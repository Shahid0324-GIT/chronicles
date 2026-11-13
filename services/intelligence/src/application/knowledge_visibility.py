from dataclasses import replace
from uuid import UUID

from src.application.dto import NodeDetails, UniverseGraph
from src.application.ports.knowledge import KnowledgeRepository
from src.domain.exceptions import NotFoundError


class PublicationVisibility:
    """Source-scoped reading; curated records retain their existing visibility."""

    def __init__(self, knowledge: KnowledgeRepository) -> None:
        self.knowledge = knowledge

    async def graph(self, graph: UniverseGraph, allowed_sources: list[UUID]) -> UniverseGraph:
        hidden = await self.knowledge.hidden_targets(graph.universe.id, allowed_sources)
        return replace(
            graph,
            nodes=[n for n in graph.nodes if n.id not in hidden],
            edges=[
                e
                for e in graph.edges
                if e.id not in hidden
                and e.source_node_id not in hidden
                and e.target_node_id not in hidden
            ],
        )

    async def node(self, details: NodeDetails, allowed_sources: list[UUID]) -> NodeDetails:
        hidden = await self.knowledge.hidden_targets(details.node.universe_id, allowed_sources)
        if details.node.id in hidden:
            raise NotFoundError("Node not found")
        return replace(
            details,
            edges=[
                e
                for e in details.edges
                if e.id not in hidden
                and e.source_node_id not in hidden
                and e.target_node_id not in hidden
            ],
        )
