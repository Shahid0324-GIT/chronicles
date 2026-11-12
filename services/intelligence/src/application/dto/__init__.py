from dataclasses import dataclass

from src.domain.entities import Continuity, GraphNode, GraphRelationship, Universe


@dataclass(frozen=True)
class UniverseGraph:
    universe: Universe
    continuities: list[Continuity]
    nodes: list[GraphNode]
    edges: list[GraphRelationship]


@dataclass(frozen=True)
class NodeDetails:
    node: GraphNode
    edges: list[GraphRelationship]
