from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from src.application.arc_contracts import DevelopmentEvidence
from src.domain.research import SourceDocument, SourcePassage


class DevelopmentEvidenceProvider(Protocol):
    async def development_evidence(
        self,
        universe: UUID,
        continuity: UUID,
        facts: list[dict[str, Any]],
        spoiler_position: int | None,
        token_budget: int = 3200,
    ) -> tuple[list[DevelopmentEvidence], list[str]]: ...


@dataclass(frozen=True)
class ArcSource:
    """One permitted archived source inside an arc's presentation range."""

    id: UUID
    label: str
    position: int
    position_basis: str
    authority: str | None
    source_group: str
    cloud_eligible: bool
    url: str = ""


@dataclass(frozen=True)
class ArcPassageSet:
    """Archived sentences in source presentation order, fenced before any inference."""

    sentences: list[DevelopmentEvidence]
    sources: list[ArcSource]
    issues: list[str]

    @property
    def cloud_eligible(self) -> bool:
        return bool(self.sources) and all(s.cloud_eligible for s in self.sources)


class ArcPassageProvider(Protocol):
    async def arc_passages(
        self,
        universe: UUID,
        continuity: UUID,
        *,
        first_position: int,
        last_position: int,
        position_basis: str,
        spoiler_position: int | None,
        allowed_sources: list[UUID] | None = None,
    ) -> ArcPassageSet: ...


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
    async def neighbors(self, passage_ids: list[UUID]) -> list[EvidenceHit]: ...
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
