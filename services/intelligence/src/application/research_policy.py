"""Versioned, bounded effort policy. Page count is a resource ceiling, never sufficiency."""

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from src.application.research_contracts import StructuredModel


class ResearchPolicy(StructuredModel):
    version: Literal["focused-v1", "adaptive-v2"] = "adaptive-v2"
    depth: Literal["quick", "focused", "deep"] = "focused"
    max_passes: int = Field(default=3, ge=1, le=20)
    max_follow_up_depth: int = Field(default=2, ge=0, le=10)
    max_queries: int = Field(default=8, ge=0, le=100)
    max_documents: int = Field(default=12, ge=1, le=200)
    max_bytes: int = Field(default=20_000_000, ge=1024, le=50_000_000)
    max_requests: int = Field(default=60, ge=1, le=2000)
    max_document_chars: int = Field(default=500_000, ge=500, le=2_000_000)
    presentation_requires_coverage: bool = True
    max_model_calls: int = Field(default=48, ge=1, le=200)
    max_tokens: int = Field(default=150_000, ge=1000, le=1_000_000)
    max_seconds: int = Field(default=900, ge=10, le=3600)
    dossier_tokens: int = Field(default=3500, ge=500, le=16000)
    max_leads: int = Field(default=40, ge=1, le=200)
    min_relevant_facts: int = Field(default=3, ge=1, le=100)
    min_source_groups: int = Field(default=1, ge=1, le=10)
    required_facets: list[str] = Field(
        default_factory=lambda: ["identity", "events", "connections"], min_length=1, max_length=12
    )

    @model_validator(mode="before")
    @classmethod
    def depth_defaults(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        presets = {
            "quick": dict(
                max_passes=1,
                max_follow_up_depth=1,
                max_queries=3,
                max_documents=4,
                max_requests=20,
                max_bytes=8_000_000,
                max_model_calls=16,
                max_tokens=40_000,
                max_seconds=300,
                dossier_tokens=2500,
            ),
            "deep": dict(
                max_passes=6,
                max_follow_up_depth=4,
                max_queries=20,
                max_documents=30,
                max_requests=180,
                max_bytes=50_000_000,
                max_model_calls=96,
                max_tokens=300_000,
                max_seconds=1800,
                dossier_tokens=7000,
            ),
        }
        return {**presets.get(value.get("depth", "focused"), {}), **value}


class UniverseResearchProfile(StructuredModel):
    universe_id: UUID
    original_medium: Literal[
        "unknown", "manga", "light-novel", "web-novel", "game", "book", "anime"
    ]
    continuity_media: dict[UUID, str] = Field(default_factory=dict, max_length=30)
    primary_categories: list[str] = Field(default_factory=list, max_length=20)
    publishers: list[str] = Field(default_factory=list, max_length=20)
    authorized_sites: list[str] = Field(default_factory=list, max_length=30)
    reference_sites: list[str] = Field(default_factory=list, max_length=30)
    apis: list[str] = Field(default_factory=list, max_length=20)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    story_structure: str = Field(default="Unknown; investigate structure", max_length=500)
    source_priorities: dict[str, int] = Field(default_factory=dict, max_length=30)
    retrieval_methods: list[str] = Field(default_factory=lambda: ["html", "official-api"])
    boundary_notes: str = Field(
        default="Do not merge adaptations or infer first reveal", max_length=1000
    )


LeadStatus = Literal[
    "DISCOVERED", "QUEUED", "RESEARCHING", "RESOLVED", "PARTIALLY_RESOLVED", "BLOCKED", "EXHAUSTED"
]


class ResearchLead(StructuredModel):
    id: UUID
    universe_id: UUID
    continuity_id: UUID
    boundary_key: str
    objective_key: str
    question: str = Field(min_length=5, max_length=1500)
    related_questions: list[str] = Field(default_factory=list)
    topic: str = Field(max_length=300)
    related_entity_ids: list[UUID] = Field(default_factory=list)
    discovery_origin: str = Field(max_length=300)
    priority: int = Field(default=50, ge=0, le=100)
    expected_value: float = Field(default=0.5, ge=0, le=1)
    source_ids: list[UUID] = Field(default_factory=list)
    available_sources: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    estimated_cost: int = Field(default=1, ge=0)
    status: LeadStatus = "DISCOVERED"
    depth: int = Field(default=0, ge=0)
    attempt_count: int = Field(default=0, ge=0)
    last_attempted_at: str | None = None
    last_job_id: UUID | None = None
    last_stop_reason: str | None = None


class CoverageAssessment(StructuredModel):
    outcome: Literal[
        "SUFFICIENT_FOR_PRESENTATION",
        "PARTIAL_COVERAGE",
        "BLOCKED_BY_SOURCE_ACCESS",
        "BUDGET_EXHAUSTED",
        "INSUFFICIENT_EVIDENCE",
    ]
    relevant_facts: int
    source_groups: int
    facets: list[str]
    missing_facets: list[str]
    pending_leads: int
    contradictions: int
    reason: str


class LeadAnswer(StructuredModel):
    lead_index: int = Field(ge=0)
    fact_indices: list[int] = Field(min_length=1, max_length=12)
    fully_answered: bool


class CoverageReview(StructuredModel):
    answers: list[LeadAnswer] = Field(default_factory=list, max_length=40)
    follow_up_questions: list[str] = Field(default_factory=list, max_length=5)
