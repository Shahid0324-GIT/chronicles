from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import VECTOR  # type: ignore[import-untyped]
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .research import JSON_TYPE


class SourceRegistryModel(Base):
    __tablename__ = "source_registry"
    __table_args__ = (
        UniqueConstraint("universe_id", "url"),
        Index("ix_source_registry_universe", "universe_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID] = mapped_column(ForeignKey("universes.id"))
    url: Mapped[str] = mapped_column(String(2000))
    domain: Mapped[str] = mapped_column(String(300))
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
    health: Mapped[str] = mapped_column(String(40))
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(100))


class InferenceCacheModel(Base):
    __tablename__ = "research_inference_cache"
    __table_args__ = (Index("ix_inference_cache_created", "created_at"),)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PassageEmbeddingModel(Base):
    __tablename__ = "passage_embeddings"
    __table_args__ = (
        UniqueConstraint("passage_id", "model_key"),
        ForeignKeyConstraint(
            ["passage_id", "universe_id", "continuity_id"],
            ["source_passages.id", "source_passages.universe_id", "source_passages.continuity_id"],
        ),
        Index("ix_embedding_scope_model", "universe_id", "continuity_id", "model_key"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    passage_id: Mapped[UUID]
    universe_id: Mapped[UUID]
    continuity_id: Mapped[UUID]
    model_key: Mapped[str] = mapped_column(String(200))
    dimensions: Mapped[int]
    content_hash: Mapped[str] = mapped_column(String(64))
    # The type has no fixed dimension; each model digest/dimension is filtered separately.
    vector: Mapped[list[float]] = mapped_column(VECTOR().with_variant(JSON(), "sqlite"))


class NarrativeProjectionModel(Base):
    __tablename__ = "narrative_projections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["continuity_id", "universe_id"], ["continuities.id", "continuities.universe_id"]
        ),
        UniqueConstraint("universe_id", "continuity_id", "boundary_key"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID]
    continuity_id: Mapped[UUID]
    boundary_key: Mapped[str] = mapped_column(String(64))
    revision: Mapped[str] = mapped_column(String(64))
    catalog: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class KnowledgePresentationModel(Base):
    __tablename__ = "knowledge_presentations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["continuity_id", "universe_id"], ["continuities.id", "continuities.universe_id"]
        ),
        Index(
            "ix_knowledge_presentation_scope",
            "universe_id",
            "continuity_id",
            "kind",
            "boundary_key",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID]
    continuity_id: Mapped[UUID]
    resource_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(String(40))
    boundary_key: Mapped[str] = mapped_column(String(64))
    knowledge_revision: Mapped[str] = mapped_column(String(64))
    evidence_fingerprint: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(20))
    policy_version: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
    grounding_status: Mapped[str] = mapped_column(String(40))
    provider_metadata: Mapped[list[dict[str, Any]]] = mapped_column(JSON_TYPE)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
