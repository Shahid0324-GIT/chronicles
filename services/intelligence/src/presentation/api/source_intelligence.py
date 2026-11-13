from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field

from src.application.narrative import NarrativeBuilder
from src.application.research_contracts import StructuredModel
from src.application.research_use_cases import ResearchRequestError
from src.application.source_contracts import SourceDiscovery, SourceEntry, SourceRegistration
from src.application.source_intelligence import SourceDiscoveryService, SourceSelector
from src.application.use_cases import GetUniverse
from src.infrastructure.persistence.source_registry import SqlSourceRegistry
from src.infrastructure.research_runtime import (
    build_retrieval,
    narrative_transactions,
    registry_transactions,
)
from src.infrastructure.sources import PublicSourcePolicy, SearxngSearch
from src.presentation.dependencies import Session, get_universe

router = APIRouter(prefix="/api")


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
) -> dict[str, Any]:
    universe = await use_case.execute(slug)
    return await NarrativeBuilder(narrative_transactions(request.app.state.session_factory)).build(
        universe.id,
        continuity_id,
        allowed_sources=allowed_source_id,
        spoiler_position=spoiler_position,
    )
