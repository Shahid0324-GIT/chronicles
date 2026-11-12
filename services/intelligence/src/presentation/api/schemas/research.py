from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

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


class AliasResponse(BaseModel):
    id: UUID
    node_id: UUID
    name: str
    normalized_name: str
    claim_id: UUID


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
