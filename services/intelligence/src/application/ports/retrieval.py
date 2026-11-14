from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from src.domain.research import SourceDocument, SourcePassage


@dataclass(frozen=True)
class EmbeddingIdentity:
    model: str
    digest: str
    dimensions: int

    @property
    def key(self) -> str:
        return f"{self.model}@{self.digest}:{self.dimensions}:passage-v2"


class EmbeddingProvider(Protocol):
    async def identity(self) -> EmbeddingIdentity: ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class EvidenceHit:
    passage: SourcePassage
    source: SourceDocument
    distance: float | None = None


class EvidenceIndex(Protocol):
    async def source_metadata(
        self, universe: UUID, continuity: UUID, source_ids: list[UUID] | None = None
    ) -> dict[UUID, dict[str, Any]]: ...
    async def cached_vector(
        self, universe: UUID, continuity: UUID, model: EmbeddingIdentity, content_hash: str
    ) -> list[float] | None: ...
    async def passages(
        self,
        universe: UUID,
        continuity: UUID,
        source_ids: list[UUID] | None = None,
        query: str | None = None,
    ) -> list[EvidenceHit]: ...
    async def indexed(self, passage: UUID, model: EmbeddingIdentity, content_hash: str) -> bool: ...
    async def store(
        self, hit: EvidenceHit, model: EmbeddingIdentity, vector: list[float]
    ) -> None: ...
    async def nearest(
        self,
        universe: UUID,
        continuity: UUID,
        model: EmbeddingIdentity,
        vector: list[float],
        limit: int,
        allowed_sources: list[UUID] | None,
        authorities: list[str],
    ) -> list[EvidenceHit]: ...


class EvidenceIndexTransaction(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[EvidenceIndex]: ...
