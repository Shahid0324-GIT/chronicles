from uuid import UUID, uuid4

import pytest

from src.application.use_cases import GetNodeDetails, GetUniverse, GetUniverseGraph, ListUniverses
from src.domain.exceptions import NotFoundError
from src.infrastructure.persistence.seed import sample_graph


class FakeUniverses:
    def __init__(self):
        self.universe = sample_graph()[0]

    async def list_all(self):
        return [self.universe]

    async def get_by_slug(self, slug):
        return self.universe if slug == str(self.universe.slug) else None


class FakeGraph:
    def __init__(self):
        self.universe, self.continuity, self.nodes, self.edges = sample_graph()

    async def get_continuities(self, universe_id):
        return [self.continuity]

    async def get_nodes(self, universe_id):
        return self.nodes

    async def get_edges(self, universe_id):
        return self.edges

    async def get_node(self, node_id: UUID):
        return next((n for n in self.nodes if n.id == node_id), None)

    async def get_incident_edges(self, node_id):
        return [e for e in self.edges if node_id in (e.source_node_id, e.target_node_id)]


async def test_use_cases_with_constructor_injected_fakes():
    universes, graph = FakeUniverses(), FakeGraph()
    assert await ListUniverses(universes).execute() == [universes.universe]
    assert await GetUniverse(universes).execute("re-zero") == universes.universe
    result = await GetUniverseGraph(universes, graph).execute("re-zero")
    assert len(result.nodes) == 15 and len(result.edges) == 25
    details = await GetNodeDetails(graph).execute(graph.nodes[0].id)
    assert details.node == graph.nodes[0]
    assert all(details.node.id in (e.source_node_id, e.target_node_id) for e in details.edges)


async def test_missing_entities():
    with pytest.raises(NotFoundError):
        await GetUniverse(FakeUniverses()).execute("missing")
    with pytest.raises(NotFoundError):
        await GetUniverseGraph(FakeUniverses(), FakeGraph()).execute("missing")
    with pytest.raises(NotFoundError):
        await GetNodeDetails(FakeGraph()).execute(uuid4())
