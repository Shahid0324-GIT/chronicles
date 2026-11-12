from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TypeAlias
from uuid import UUID, uuid4

from src.domain.exceptions import DomainError
from src.domain.value_objects import NodeType, RelationshipType, Slug

JSONValue: TypeAlias = "str | int | float | bool | None | list[JSONValue] | dict[str, JSONValue]"


def now() -> datetime:
    return datetime.now(UTC)


def require_text(value: str, label: str) -> None:
    if not value.strip():
        raise DomainError(f"{label} must not be blank")


@dataclass(frozen=True, kw_only=True)
class Universe:
    slug: Slug
    title: str
    description: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=now)
    updated_at: datetime = field(default_factory=now)

    def __post_init__(self) -> None:
        require_text(self.title, "Title")


@dataclass(frozen=True, kw_only=True)
class Continuity:
    universe_id: UUID
    name: str
    medium: str
    description: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        require_text(self.name, "Continuity name")
        require_text(self.medium, "Medium")


@dataclass(frozen=True, kw_only=True)
class GraphNode:
    universe_id: UUID
    type: NodeType
    title: str
    summary: str
    continuity_id: UUID | None = None
    metadata: dict[str, JSONValue] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=now)
    updated_at: datetime = field(default_factory=now)

    def __post_init__(self) -> None:
        require_text(self.title, "Title")
        if not isinstance(self.type, NodeType):
            raise DomainError("Unknown node type")


@dataclass(frozen=True, kw_only=True)
class GraphRelationship:
    universe_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    relationship_type: RelationshipType
    description: str
    continuity_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not isinstance(self.relationship_type, RelationshipType):
            raise DomainError("Unknown relationship type")
        require_text(self.description, "Relationship description")

    def validate_endpoints(self, source: GraphNode, target: GraphNode) -> None:
        if (source.id, target.id) != (self.source_node_id, self.target_node_id):
            raise DomainError("Relationship endpoints do not match the supplied nodes")
        if source.universe_id != self.universe_id or target.universe_id != self.universe_id:
            raise DomainError("Relationship endpoints must belong to the same universe")
        # None means explicitly shared across continuities. It never implies adaptation equivalence.
        scoped = {c for c in (source.continuity_id, target.continuity_id) if c is not None}
        if len(scoped) > 1 or (scoped and self.continuity_id not in scoped):
            raise DomainError("Relationship and endpoints have incompatible continuities")
