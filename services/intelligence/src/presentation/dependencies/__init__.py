from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.knowledge_visibility import PublicationVisibility
from src.application.ports import GraphRepository, UniverseRepository
from src.application.use_cases import GetNodeDetails, GetUniverse, GetUniverseGraph, ListUniverses
from src.infrastructure.persistence.knowledge_repository import SqlKnowledgeRepository
from src.infrastructure.persistence.repositories import SqlGraphRepository, SqlUniverseRepository


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    # This dependency owns the transaction. Repositories never commit.
    async with request.app.state.session_factory() as session, session.begin():
        yield session


Session = Annotated[AsyncSession, Depends(get_session)]


def get_universe_repository(session: Session) -> UniverseRepository:
    return SqlUniverseRepository(session)


def get_graph_repository(session: Session) -> GraphRepository:
    return SqlGraphRepository(session)


Universes = Annotated[UniverseRepository, Depends(get_universe_repository)]
Graph = Annotated[GraphRepository, Depends(get_graph_repository)]


def list_universes(universes: Universes) -> ListUniverses:
    return ListUniverses(universes)


def get_universe(universes: Universes) -> GetUniverse:
    return GetUniverse(universes)


def get_graph(universes: Universes, graph: Graph) -> GetUniverseGraph:
    return GetUniverseGraph(universes, graph)


def get_node(graph: Graph) -> GetNodeDetails:
    return GetNodeDetails(graph)


def publication_visibility(session: Session) -> PublicationVisibility:
    return PublicationVisibility(SqlKnowledgeRepository(session))
