from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from src.application.knowledge_visibility import PublicationVisibility
from src.application.use_cases import GetNodeDetails, GetUniverse, GetUniverseGraph, ListUniverses
from src.presentation.api.schemas import (
    GraphResponse,
    HealthResponse,
    NodeDetailsResponse,
    UniverseResponse,
)
from src.presentation.dependencies import (
    Session,
    get_graph,
    get_node,
    get_universe,
    list_universes,
    publication_visibility,
)

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
async def health(session: Session) -> HealthResponse:
    await session.execute(text("SELECT 1"))
    return HealthResponse(status="ok", database="ready")


@router.get("/universes", response_model=list[UniverseResponse])
async def universes(
    use_case: Annotated[ListUniverses, Depends(list_universes)],
) -> list[UniverseResponse]:
    return [UniverseResponse.from_entity(u) for u in await use_case.execute()]


@router.get("/universes/{slug}", response_model=UniverseResponse)
async def universe(
    slug: str, use_case: Annotated[GetUniverse, Depends(get_universe)]
) -> UniverseResponse:
    return UniverseResponse.from_entity(await use_case.execute(slug))


@router.get("/universes/{slug}/graph", response_model=GraphResponse)
async def graph(
    slug: str,
    use_case: Annotated[GetUniverseGraph, Depends(get_graph)],
    visibility: Annotated[PublicationVisibility, Depends(publication_visibility)],
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
    curated_only: bool = False,
) -> GraphResponse:
    result = await use_case.execute(slug)
    if curated_only or allowed_source_id is not None:
        result = await visibility.graph(result, [] if curated_only else allowed_source_id or [])
    return GraphResponse.from_dto(result)


@router.get("/nodes/{node_id}", response_model=NodeDetailsResponse)
async def node(
    node_id: UUID,
    use_case: Annotated[GetNodeDetails, Depends(get_node)],
    visibility: Annotated[PublicationVisibility, Depends(publication_visibility)],
    allowed_source_id: Annotated[list[UUID] | None, Query()] = None,
    curated_only: bool = False,
) -> NodeDetailsResponse:
    result = await use_case.execute(node_id)
    if curated_only or allowed_source_id is not None:
        result = await visibility.node(result, [] if curated_only else allowed_source_id or [])
    return NodeDetailsResponse.from_dto(result)
