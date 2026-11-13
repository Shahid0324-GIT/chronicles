from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from src.application.research_contracts import CandidateEntity, CandidateRelationship


class JobResponse(BaseModel):
    id: UUID
    universe_id: UUID
    continuity_id: UUID
    objective: str
    status: str
    stage: str
    iteration: int
    cancel_requested: bool
    error: str | None
    provider_usage: list[dict[str, Any]]


class EvidenceResponse(BaseModel):
    passage_id: UUID
    source_id: UUID
    quote: str
    passage_start: int
    quote_start: int
    quote_end: int
    url: str
    title: str
    publisher: str
    content_hash: str
    retrieved_at: datetime
    source_scope: str
    permission_basis: str
    public_web: bool
    truncated: bool
    independence_key: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class FindingResponse(BaseModel):
    id: UUID
    kind: Literal["entity", "relationship"]
    payload: CandidateEntity | CandidateRelationship
    decision: Literal["supported", "disputed", "insufficient", "review"]
    reason: str
    canonical: bool
    canonical_id: UUID | None = None
    promotion_id: UUID | None = None
    evidence: list[EvidenceResponse]


class EventResponse(BaseModel):
    id: int
    stage: str
    detail: dict[str, Any]
    created_at: datetime


class ResearchDiscoveryResponse(BaseModel):
    id: UUID
    canonical_id: UUID
    kind: Literal["entity", "relationship"]
    type: str
    label: str


class ResearchSummaryResponse(BaseModel):
    id: UUID
    status: Literal["queued", "running", "completed", "partial", "failed", "cancelled"]
    stage: str
    error: str | None
    model_calls: int = Field(ge=0)
    incomplete_call_reservations: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    retry_count: int = Field(ge=0)
    validation_failures: int = Field(ge=0)
    providers: list[str]
    sources: int = Field(ge=0)
    source_retrievals: int = Field(ge=0)
    embedding_reused: int = Field(ge=0)
    embedding_generated: int = Field(ge=0)
    candidate_entities: int = Field(ge=0)
    accepted_relationships: int = Field(ge=0)
    unresolved_findings: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    stage_elapsed_ms: dict[str, int]
    discoveries: list[ResearchDiscoveryResponse]


class AliasResponse(BaseModel):
    id: UUID
    node_id: UUID
    name: str
    normalized_name: str
    claim_id: UUID
    supporting_claim_ids: list[UUID]
    source_ids: list[UUID]


class PromotionResponse(BaseModel):
    id: UUID
    claim_id: UUID
    job_id: UUID
    universe_id: UUID
    continuity_id: UUID
    target_id: UUID
    kind: Literal["entity", "relationship"]
    created: bool
    reversed: bool
    data: dict[str, Any]
    created_at: datetime
    reversed_at: datetime | None
    correction_reason: str | None


class KnowledgeResponse(BaseModel):
    decisions: dict[str, dict[str, Any]]
    promotions: list[PromotionResponse]
    summary: dict[str, int]
