from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from src.domain.entities import GraphNode, GraphRelationship


@dataclass(frozen=True)
class NarrativeKnowledge:
    nodes: list[GraphNode]
    edges: list[GraphRelationship]
    facts: list[dict[str, Any]]
    interpretations: list[dict[str, Any]] = field(default_factory=list)


class NarrativeRepository(Protocol):
    async def knowledge(self, universe: UUID, continuity: UUID) -> NarrativeKnowledge: ...
    async def save(
        self,
        universe: UUID,
        continuity: UUID,
        boundary_key: str,
        revision: str,
        catalog: dict[str, Any],
    ) -> None: ...


class NarrativeTransaction(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[NarrativeRepository]: ...
