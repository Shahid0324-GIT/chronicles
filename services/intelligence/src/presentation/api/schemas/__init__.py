from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.application.dto import NodeDetails, UniverseGraph
from src.domain.entities import Continuity, GraphNode, GraphRelationship, Universe
from src.domain.value_objects import NodeType, RelationshipType


class UniverseResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    description: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, item: Universe) -> "UniverseResponse":
        return cls(
            id=item.id,
            slug=str(item.slug),
            title=item.title,
            description=item.description,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )


class ContinuityResponse(BaseModel):
    id: UUID
    universe_id: UUID
    name: str
    medium: str
    description: str

    @classmethod
    def from_entity(cls, item: Continuity) -> "ContinuityResponse":
        return cls.model_validate(item, from_attributes=True)


class NodeResponse(BaseModel):
    id: UUID
    universe_id: UUID
    continuity_id: UUID | None
    type: NodeType
    title: str
    summary: str
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, item: GraphNode) -> "NodeResponse":
        return cls.model_validate(item, from_attributes=True)


class EdgeResponse(BaseModel):
    id: UUID
    universe_id: UUID
    continuity_id: UUID | None
    source: UUID
    target: UUID
    relationship_type: RelationshipType
    description: str

    @classmethod
    def from_entity(cls, item: GraphRelationship) -> "EdgeResponse":
        return cls(
            id=item.id,
            universe_id=item.universe_id,
            continuity_id=item.continuity_id,
            source=item.source_node_id,
            target=item.target_node_id,
            relationship_type=item.relationship_type,
            description=item.description,
        )


class GraphResponse(BaseModel):
    universe: UniverseResponse
    continuities: list[ContinuityResponse]
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]

    @classmethod
    def from_dto(cls, item: UniverseGraph) -> "GraphResponse":
        return cls(
            universe=UniverseResponse.from_entity(item.universe),
            continuities=[ContinuityResponse.from_entity(c) for c in item.continuities],
            nodes=[NodeResponse.from_entity(n) for n in item.nodes],
            edges=[EdgeResponse.from_entity(e) for e in item.edges],
        )


class NodeDetailsResponse(BaseModel):
    node: NodeResponse
    edges: list[EdgeResponse]

    @classmethod
    def from_dto(cls, item: NodeDetails) -> "NodeDetailsResponse":
        return cls(
            node=NodeResponse.from_entity(item.node),
            edges=[EdgeResponse.from_entity(e) for e in item.edges],
        )


class ErrorResponse(BaseModel):
    code: str
    message: str


class HealthResponse(BaseModel):
    status: str
    database: str
