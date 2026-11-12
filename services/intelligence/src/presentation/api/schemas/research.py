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
    canonical: Literal[False]
    evidence: list[EvidenceResponse]


class EventResponse(BaseModel):
    id: int
    stage: str
    detail: dict[str, Any]
    created_at: datetime
