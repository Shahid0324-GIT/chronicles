"""Investigations and evidence packages are archived work, never canonical graph rows."""

from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from src.application.research_contracts import StructuredModel
from src.domain.value_objects import NodeType


class InvestigationSubject(StructuredModel):
    name: str = Field(min_length=1, max_length=200)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    canonical_id: UUID | None = None
    type: NodeType = NodeType.CHARACTER


class BundlePassage(StructuredModel):
    passage_id: UUID
    source_id: UUID
    source_revision: str
    passage_hash: str
    start: int
    end: int
    text: str
    section: str
    url: str
    authority: str
    source_family: str
    language: str
    cloud_allowed: bool


class EvidenceBundle(StructuredModel):
    id: UUID
    fingerprint: str
    continuity_id: UUID
    spoiler_position: int | None
    subjects: list[InvestigationSubject]
    passages: list[BundlePassage]
    anchor_passage_id: UUID
    score: float
    estimated_tokens: int
    permission_fingerprint: str


class AtomicAssertion(StructuredModel):
    subject: str = Field(min_length=1, max_length=200)
    subject_type: NodeType = NodeType.CHARACTER
    predicate: str = Field(min_length=2, max_length=120)
    object: str = Field(min_length=1, max_length=200)
    object_type: NodeType = NodeType.CHARACTER
    kind: Literal["interaction", "attribute", "causality", "identity"] = "interaction"
    occurrence_status: Literal[
        "actual", "intended", "hypothetical", "reported", "denied", "uncertain"
    ] = "actual"
    classification: Literal[
        "ESTABLISHED_CANON", "SUPPORTED_INTERPRETATION", "FAN_THEORY", "UNRESOLVED"
    ] = "ESTABLISHED_CANON"
    sentence_ids: list[int] = Field(min_length=1, max_length=3)
    context_ids: list[int] = Field(default_factory=list, max_length=3)
    temporal_context: str | None = Field(default=None, max_length=120)
    uncertainty: str = Field(default="", max_length=300)


class ConnectedAssertions(StructuredModel):
    assertions: list[AtomicAssertion] = Field(default_factory=list, max_length=8)
    missing_information: list[str] = Field(default_factory=list, max_length=8)


class AtomicVerdict(StructuredModel):
    index: int = Field(ge=0, le=7)
    subject_supported: bool
    predicate_supported: bool
    object_supported: bool
    direction_valid: bool
    subject_type_valid: bool
    object_type_valid: bool
    actual_occurrence: bool
    in_universe: bool
    material_conflict: bool
    continuity_matches: bool
    reason: str = Field(min_length=3, max_length=240)


class AtomicVerdicts(StructuredModel):
    assessments: list[AtomicVerdict] = Field(min_length=1, max_length=4)


class RelationshipInvestigation(StructuredModel):
    id: UUID
    objective: str
    continuity_id: UUID
    spoiler_position: int | None
    subjects: list[InvestigationSubject]
    bundles: list[EvidenceBundle] = Field(default_factory=list)
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    relevant_events: list[str] = Field(default_factory=list)
    relevant_lore: list[str] = Field(default_factory=list)
    supporting_claims: list[str] = Field(default_factory=list)
    contradictory_claims: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    assessments: dict[str, dict[str, Any]] = Field(default_factory=dict)
    extractions: dict[str, dict[str, Any]] = Field(default_factory=dict)
    resolution_progress: dict[str, dict[str, Any]] = Field(default_factory=dict)
    pending_claims: list[str] = Field(default_factory=list)
    verification_state: str = "pending"
    publication_state: str = "unpublished"
    presentation_ready: bool = False
    policy_version: str = "relationship-bundles-v2"
