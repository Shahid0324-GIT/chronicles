from uuid import UUID

from src.application.dto import NodeDetails, UniverseGraph
from src.application.ports import GraphRepository, UniverseRepository
from src.domain.entities import Universe
from src.domain.exceptions import NotFoundError


class ListUniverses:
    def __init__(self, universes: UniverseRepository) -> None:
        self.universes = universes

    async def execute(self) -> list[Universe]:
        return await self.universes.list_all()


class GetUniverse:
    def __init__(self, universes: UniverseRepository) -> None:
        self.universes = universes

    async def execute(self, slug: str) -> Universe:
        universe = await self.universes.get_by_slug(slug)
        if universe is None:
            raise NotFoundError("Universe not found")
        return universe


class GetUniverseGraph:
    def __init__(self, universes: UniverseRepository, graph: GraphRepository) -> None:
        self.universes = universes
        self.graph = graph

    async def execute(self, slug: str) -> UniverseGraph:
        universe = await GetUniverse(self.universes).execute(slug)
        # One request session, sequential operations: AsyncSession is not concurrency-safe.
        return UniverseGraph(
            universe,
            await self.graph.get_continuities(universe.id),
            await self.graph.get_nodes(universe.id),
            await self.graph.get_edges(universe.id),
        )


class GetNodeDetails:
    def __init__(self, graph: GraphRepository) -> None:
        self.graph = graph

    async def execute(self, node_id: UUID) -> NodeDetails:
        node = await self.graph.get_node(node_id)
        if node is None:
            raise NotFoundError("Node not found")
        return NodeDetails(node, await self.graph.get_incident_edges(node_id))
