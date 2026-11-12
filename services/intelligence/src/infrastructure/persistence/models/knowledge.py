"""Additive identity and publication audit structures; original graph rows are untouched."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .research import JSON_TYPE


class KnowledgeDecisionModel(Base):
    __tablename__ = "knowledge_decisions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["claim_id", "universe_id", "continuity_id"],
            ["research_claims.id", "research_claims.universe_id", "research_claims.continuity_id"],
        ),
        Index("ix_knowledge_decisions_job", "job_id"),
    )
    claim_id: Mapped[UUID] = mapped_column(primary_key=True)
    job_id: Mapped[UUID]
    universe_id: Mapped[UUID]
    continuity_id: Mapped[UUID]
    data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EntityAliasModel(Base):
    __tablename__ = "entity_aliases"
    __table_args__ = (
        ForeignKeyConstraint(
            ["node_id", "universe_id"], ["graph_nodes.id", "graph_nodes.universe_id"]
        ),
        ForeignKeyConstraint(
            ["claim_id", "universe_id", "continuity_id"],
            ["research_claims.id", "research_claims.universe_id", "research_claims.continuity_id"],
        ),
        UniqueConstraint("node_id", "normalized_name"),
        Index("ix_entity_aliases_scope_name", "universe_id", "continuity_id", "normalized_name"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    node_id: Mapped[UUID]
    universe_id: Mapped[UUID]
    continuity_id: Mapped[UUID]
    claim_id: Mapped[UUID]
    name: Mapped[str] = mapped_column(String(200))
    normalized_name: Mapped[str] = mapped_column(String(200))
    sensitive: Mapped[bool] = mapped_column(Boolean)


class PromotionRecordModel(Base):
    __tablename__ = "promotion_records"
    __table_args__ = (
        UniqueConstraint("claim_id"),
        UniqueConstraint("id", "universe_id", "continuity_id"),
        ForeignKeyConstraint(
            ["claim_id", "universe_id", "continuity_id"],
            ["research_claims.id", "research_claims.universe_id", "research_claims.continuity_id"],
        ),
        Index("ix_promotion_records_target", "target_id", "reversed"),
        Index("ix_promotion_records_job", "job_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    claim_id: Mapped[UUID]
    job_id: Mapped[UUID]
    universe_id: Mapped[UUID]
    continuity_id: Mapped[UUID]
    target_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(String(30))
    created: Mapped[bool] = mapped_column(Boolean)
    reversed: Mapped[bool] = mapped_column(Boolean)
    data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correction_reason: Mapped[str | None] = mapped_column(Text)


class PromotionEvidenceModel(Base):
    __tablename__ = "promotion_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["promotion_id", "universe_id", "continuity_id"],
            [
                "promotion_records.id",
                "promotion_records.universe_id",
                "promotion_records.continuity_id",
            ],
        ),
        ForeignKeyConstraint(
            ["passage_id", "universe_id", "continuity_id"],
            ["source_passages.id", "source_passages.universe_id", "source_passages.continuity_id"],
        ),
        Index("ix_promotion_evidence_passage", "passage_id"),
    )
    promotion_id: Mapped[UUID] = mapped_column(primary_key=True)
    passage_id: Mapped[UUID] = mapped_column(primary_key=True)
    quote_start: Mapped[int] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID]
    continuity_id: Mapped[UUID]
    quote_end: Mapped[int]
    quote: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64))
