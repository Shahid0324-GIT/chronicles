from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field

from src.application.encyclopedia_contracts import EncyclopediaEntry
from src.application.research_contracts import StructuredModel
from src.application.research_frontier import ResearchFrontierService
from src.application.research_policy import ResearchLead, UniverseResearchProfile
from src.application.research_use_cases import ResearchRequestError
from src.application.source_contracts import SourceDiscovery, SourceEntry, SourceRegistration
from src.application.source_intelligence import SourceDiscoveryService, SourceSelector
from src.application.use_cases import GetUniverse
from src.domain.exceptions import NotFoundError
from src.infrastructure.persistence.research_memory import SqlResearchMemory
from src.infrastructure.persistence.source_registry import SqlSourceRegistry
from src.infrastructure.research_runtime import (
    build_atlas,
    build_retrieval,
    registry_transactions,
)
from src.infrastructure.sources import PublicSourcePolicy, SearxngSearch
from src.presentation.dependencies import Session, get_universe

router = APIRouter(prefix="/api")


@router.put("/universes/{slug}/research/profile", response_model=UniverseResearchProfile)
async def update_research_profile(
    slug: str,
    command: UniverseResearchProfile,
    session: Session,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
) -> UniverseResearchProfile:
    universe = await use_case.execute(slug)
    if universe.id != command.universe_id:
        raise ResearchRequestError("Profile universe does not match path")
    await SqlResearchMemory(session).save_profile(command)
    return command


@router.get("/universes/{slug}/research/profile", response_model=UniverseResearchProfile | None)
async def research_profile(
    slug: str, session: Session, use_case: Annotated[GetUniverse, Depends(get_universe)]
) -> UniverseResearchProfile | None:
    universe = await use_case.execute(slug)
    return await SqlResearchMemory(session).profile(universe.id)


@router.get("/universes/{slug}/research/frontier", response_model=list[ResearchLead])
async def research_frontier(
    slug: str,
    continuity_id: UUID,
    session: Session,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
    spoiler_position: int | None = Query(default=None, ge=1),
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
) -> list[ResearchLead]:
    universe = await use_case.execute(slug)
    leads = await SqlResearchMemory(session).leads(
        universe.id, continuity_id, ResearchFrontierService.boundary(spoiler_position)
    )
    if allowed_source_id is not None:
        allowed = set(allowed_source_id)
        leads = [lead for lead in leads if lead.source_ids and set(lead.source_ids) <= allowed]
    return leads[:200]


@router.post("/research/sources", response_model=SourceEntry)
async def register_source(
    command: SourceRegistration, session: Session, request: Request
) -> SourceEntry:
    policy = PublicSourcePolicy(request.app.state.settings.research_allowed_hosts)
    if (
        command.retrieval_policy == "permitted"
        and command.access_method != "import"
        and not policy.is_approved(command.url)
    ):
        raise ResearchRequestError(
            "Ingestion requires an explicitly approved host; retain as navigation-only"
        )
    return await SqlSourceRegistry(session).register(command)


@router.get("/universes/{slug}/research/sources", response_model=list[SourceEntry])
async def registry_sources(
    slug: str,
    session: Session,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
    continuity_id: UUID | None = None,
    topic: str = "",
) -> list[SourceEntry]:
    universe = await use_case.execute(slug)
    entries = await SqlSourceRegistry(session).entries(universe.id)
    return (
        SourceSelector().select(entries, str(continuity_id), topic, universe=universe.id)
        if continuity_id
        else entries
    )


@router.post("/research/sources/discover", response_model=list[SourceEntry])
async def discover_sources(command: SourceDiscovery, request: Request) -> list[SourceEntry]:
    settings = request.app.state.settings
    search = (
        SearxngSearch(
            settings.searxng_base_url,
            PublicSourcePolicy(settings.research_allowed_hosts),
            navigation_only=True,
            timeout=settings.searxng_timeout_seconds,
            interval=settings.searxng_min_interval_seconds,
        )
        if settings.searxng_base_url
        else None
    )
    return await SourceDiscoveryService(
        search, registry_transactions(request.app.state.session_factory)
    ).discover(command)


class RetrievalQuery(StructuredModel):
    universe_id: UUID
    continuity_id: UUID
    query: str = Field(min_length=3, max_length=2000)
    names: list[str] = Field(default_factory=list, max_length=8)
    source_ids: list[UUID] | None = None
    authorities: list[str] = Field(default_factory=list, max_length=3)
    spoiler_position: int | None = Field(default=None, ge=1)
    index_archive: bool = False


@router.post("/research/evidence/query")
async def retrieve_evidence(command: RetrievalQuery, request: Request) -> dict[str, Any]:
    service = build_retrieval(request.app.state.settings, request.app.state.session_factory)
    indexed = (
        await service.index(command.universe_id, command.continuity_id, command.source_ids)
        if command.index_archive
        else None
    )
    hits = await service.retrieve(
        command.universe_id,
        command.continuity_id,
        command.query,
        names=command.names,
        allowed_sources=command.source_ids,
        authorities=command.authorities,
        spoiler_position=command.spoiler_position,
    )
    return {
        "indexing": indexed,
        "hits": [
            {
                "passage_id": str(h.passage.id),
                "source_id": str(h.source.id),
                "text": h.passage.text,
                "start": h.passage.start,
                "end": h.passage.end,
                "url": h.source.url,
                "content_hash": h.passage.content_hash,
                "distance": h.distance,
                "provenance": h.source.provenance,
            }
            for h in hits
        ],
    }


@router.get("/universes/{slug}/narrative")
async def narrative(
    slug: str,
    request: Request,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
    continuity_id: UUID,
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
    spoiler_position: int | None = Query(default=None, ge=1),
    language: Literal["en"] = "en",
) -> dict[str, Any]:
    universe = await use_case.execute(slug)
    return await build_atlas(request.app.state.session_factory).catalog(
        universe.id,
        continuity_id,
        allowed_sources=allowed_source_id,
        spoiler_position=spoiler_position,
    )


@router.get("/universes/{slug}/encyclopedia", response_model=list[EncyclopediaEntry])
async def encyclopedia(
    slug: str,
    request: Request,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
    continuity_id: UUID,
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
    spoiler_position: int | None = Query(default=None, ge=1),
    category: str | None = None,
    language: Literal["en"] = "en",
) -> list[dict[str, Any]]:
    universe = await use_case.execute(slug)
    entries = await build_atlas(request.app.state.session_factory).entries(
        universe.id,
        continuity_id,
        allowed_sources=allowed_source_id,
        spoiler_position=spoiler_position,
    )
    return [e for e in entries if category is None or e["entry_type"] == category]


@router.get("/universes/{slug}/entries/{entry_id}", response_model=EncyclopediaEntry)
async def encyclopedia_entry(
    slug: str,
    entry_id: UUID,
    request: Request,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
    continuity_id: UUID,
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
    spoiler_position: int | None = Query(default=None, ge=1),
    language: Literal["en"] = "en",
) -> dict[str, Any]:
    entries = await encyclopedia(
        slug, request, use_case, continuity_id, allowed_source_id, spoiler_position
    )
    entry = next((e for e in entries if e["id"] == str(entry_id)), None)
    if not entry:
        raise NotFoundError("No eligible entry at this story boundary")
    return entry


@router.get("/universes/{slug}/entries/{entry_id}/connections")
async def encyclopedia_connections(
    slug: str,
    entry_id: UUID,
    request: Request,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
    continuity_id: UUID,
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
    spoiler_position: int | None = Query(default=None, ge=1),
    language: Literal["en"] = "en",
) -> list[dict[str, str]]:
    entry = await encyclopedia_entry(
        slug, entry_id, request, use_case, continuity_id, allowed_source_id, spoiler_position
    )
    return list(entry["connections"])


@router.get("/universes/{slug}/story-arcs")
async def story_arcs(
    slug: str,
    request: Request,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
    continuity_id: UUID,
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
    spoiler_position: int | None = Query(default=None, ge=1),
    language: Literal["en"] = "en",
) -> list[dict[str, Any]]:
    catalog = await narrative(
        slug, request, use_case, continuity_id, allowed_source_id, spoiler_position
    )
    return [
        {
            "id": j["id"],
            "display_title": j["title"],
            "overview": j.get("overview", j["introduction"]),
            "major_milestones": j["steps"],
            "continuity": str(continuity_id),
            "source_references": [
                s for s in catalog["sources"] if s["id"] in j["ordering"]["sourceIds"]
            ],
            "partial": catalog["partial"],
            "ordering": j["ordering"],
            "organization_kind": "partial-source-guide",
            "presentation": j.get("presentation", {"status": "unavailable"}),
        }
        for j in catalog["journeys"]
    ]


@router.get("/universes/{slug}/journeys/{journey_id}")
async def journey(
    slug: str,
    journey_id: UUID,
    request: Request,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
    continuity_id: UUID,
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
    spoiler_position: int | None = Query(default=None, ge=1),
    language: Literal["en"] = "en",
) -> dict[str, Any]:
    catalog = await narrative(
        slug, request, use_case, continuity_id, allowed_source_id, spoiler_position
    )
    found = next((j for j in catalog["journeys"] if j["id"] == str(journey_id)), None)
    if not found:
        raise NotFoundError("Journey is unavailable at this story boundary")
    return dict(found)


@router.get("/universes/{slug}/lore", response_model=list[EncyclopediaEntry])
async def lore_entries(
    slug: str,
    request: Request,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
    continuity_id: UUID,
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
    spoiler_position: int | None = Query(default=None, ge=1),
    language: Literal["en"] = "en",
) -> list[dict[str, Any]]:
    return await encyclopedia(
        slug, request, use_case, continuity_id, allowed_source_id, spoiler_position, "lore"
    )


@router.get("/universes/{slug}/mysteries", response_model=list[EncyclopediaEntry])
async def mystery_entries(
    slug: str,
    request: Request,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
    continuity_id: UUID,
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
    spoiler_position: int | None = Query(default=None, ge=1),
    language: Literal["en"] = "en",
) -> list[dict[str, Any]]:
    return await encyclopedia(
        slug, request, use_case, continuity_id, allowed_source_id, spoiler_position, "mystery"
    )


@router.get("/universes/{slug}/interpretations")
async def interpretations(
    slug: str,
    request: Request,
    use_case: Annotated[GetUniverse, Depends(get_universe)],
    continuity_id: UUID,
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
    spoiler_position: int | None = Query(default=None, ge=1),
) -> list[dict[str, Any]]:
    universe = await use_case.execute(slug)
    return await build_atlas(request.app.state.session_factory).interpretations(
        universe.id,
        continuity_id,
        allowed_sources=allowed_source_id,
        spoiler_position=spoiler_position,
    )
