from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class ResearchJobModel(Base):
    __tablename__ = "research_jobs"
    __table_args__ = (
        UniqueConstraint("id", "universe_id", "continuity_id"),
        ForeignKeyConstraint(
            ["continuity_id", "universe_id"], ["continuities.id", "continuities.universe_id"]
        ),
        Index("ix_research_jobs_queue", "status", "created_at"),
        Index("ix_research_jobs_request", "request_hash"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID] = mapped_column(ForeignKey("universes.id"))
    continuity_id: Mapped[UUID]
    objective: Mapped[str] = mapped_column(Text)
    request: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
    request_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    checkpoint: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
    cancel_requested: Mapped[bool] = mapped_column(Boolean)
    error: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SourceDocumentModel(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("id", "universe_id", "continuity_id"),
        UniqueConstraint("universe_id", "continuity_id", "url_hash", "content_hash"),
        ForeignKeyConstraint(
            ["continuity_id", "universe_id"], ["continuities.id", "continuities.universe_id"]
        ),
        Index("ix_source_documents_lookup", "universe_id", "continuity_id", "url_hash"),
        Index("ix_source_documents_checked", "universe_id", "continuity_id", "last_checked_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID] = mapped_column(ForeignKey("universes.id"))
    continuity_id: Mapped[UUID]
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(300))
    publisher: Mapped[str] = mapped_column(String(300))
    text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    permission_basis: Mapped[str] = mapped_column(Text)
    source_scope: Mapped[str] = mapped_column(Text)
    public_web: Mapped[bool] = mapped_column(Boolean)
    truncated: Mapped[bool] = mapped_column(Boolean)
    independence_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)


class SourcePassageModel(Base):
    __tablename__ = "source_passages"
    __table_args__ = (
        UniqueConstraint("id", "universe_id", "continuity_id"),
        UniqueConstraint("source_id", "ordinal"),
        ForeignKeyConstraint(
            ["source_id", "universe_id", "continuity_id"],
            [
                "source_documents.id",
                "source_documents.universe_id",
                "source_documents.continuity_id",
            ],
        ),
        Index("ix_source_passages_source", "source_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID]
    continuity_id: Mapped[UUID]
    source_id: Mapped[UUID]
    ordinal: Mapped[int] = mapped_column(Integer)
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))


class ResearchClaimModel(Base):
    __tablename__ = "research_claims"
    __table_args__ = (
        UniqueConstraint("id", "universe_id", "continuity_id"),
        UniqueConstraint("job_id", "content_hash"),
        ForeignKeyConstraint(
            ["job_id", "universe_id", "continuity_id"],
            ["research_jobs.id", "research_jobs.universe_id", "research_jobs.continuity_id"],
        ),
        Index("ix_research_claims_job", "job_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID]
    continuity_id: Mapped[UUID]
    job_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(String(30))
    content_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
    decision: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text)


class ClaimEvidenceModel(Base):
    __tablename__ = "claim_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["claim_id", "universe_id", "continuity_id"],
            ["research_claims.id", "research_claims.universe_id", "research_claims.continuity_id"],
        ),
        ForeignKeyConstraint(
            ["passage_id", "universe_id", "continuity_id"],
            ["source_passages.id", "source_passages.universe_id", "source_passages.continuity_id"],
        ),
        Index("ix_claim_evidence_passage", "passage_id"),
    )
    claim_id: Mapped[UUID] = mapped_column(primary_key=True)
    passage_id: Mapped[UUID] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID]
    continuity_id: Mapped[UUID]
    quote: Mapped[str] = mapped_column(Text)
    quote_start: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_end: Mapped[int] = mapped_column(Integer)


class ResearchEventModel(Base):
    __tablename__ = "research_events"
    __table_args__ = (Index("ix_research_events_job", "job_id", "id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("research_jobs.id"))
    stage: Mapped[str] = mapped_column(String(60))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProviderUsageModel(Base):
    __tablename__ = "provider_usage"
    __table_args__ = (Index("ix_provider_usage_job", "job_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("research_jobs.id"))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE)
