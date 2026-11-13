from typing import Generic, Literal, TypeVar
from uuid import UUID

from pydantic import Field, model_validator

from src.application.research_contracts import (
    Assessment,
    CandidateEntity,
    CandidateRelationship,
    Citation,
    StructuredModel,
)
from src.domain.value_objects import NodeType, RelationshipType


class IdentityComparison(StructuredModel):
    decision: Literal["SAME_ENTITY", "DIFFERENT_ENTITY", "AMBIGUOUS", "NEW_ENTITY"]
    target_id: UUID | None = None
    target_index: int | None = Field(default=None, ge=0, le=7)
    entity_type_valid: bool
    reason: str = Field(min_length=3, max_length=600)
    evidence: list[Citation] = Field(min_length=1, max_length=3)
    hidden_identity: bool = False

    @model_validator(mode="after")
    def target_required(self) -> "IdentityComparison":
        if (
            self.decision in {"SAME_ENTITY", "DIFFERENT_ENTITY"}
            and self.target_id is None
            and self.target_index is None
        ):
            raise ValueError("A compared target UUID is required")
        return self


class IndexedIdentityComparison(StructuredModel):
    decision: Literal["SAME_ENTITY", "DIFFERENT_ENTITY", "AMBIGUOUS", "NEW_ENTITY"]
    target_index: int | None = Field(default=None, ge=0, le=7)
    entity_type_valid: bool
    reason: str = Field(min_length=3, max_length=600)
    evidence_indices: list[int] = Field(min_length=1, max_length=3)
    hidden_identity: bool = False

    # Cross-field target requirements are enforced once by IdentityResolver. They
    # cannot be expressed in this provider's JSON schema; retrying them is wasteful.


class EventIdentityComparison(IndexedIdentityComparison):
    same_occurrence: bool
    same_granularity: bool
    repeated_occurrence_excluded: bool


class RelationshipAnalysis(StructuredModel):
    relationships: list[CandidateRelationship] = Field(default_factory=list, max_length=8)


class IndexedRelationship(StructuredModel):
    source_index: int = Field(ge=0, le=23)
    target_index: int = Field(ge=0, le=23)
    type: RelationshipType
    description: str = Field(min_length=5, max_length=600)
    sentence_ids: list[int] = Field(min_length=1, max_length=3)


class IndexedRelationships(StructuredModel):
    relationships: list[IndexedRelationship] = Field(default_factory=list, max_length=6)


class RollbackRequest(StructuredModel):
    reason: str = Field(min_length=10, max_length=500)


class ResearchRetryRequest(RollbackRequest):
    from_stage: Literal[
        "identity_resolver",
        "relationship_analyst",
        "verifier",
        "promotion_policy",
        "narrative_builder",
    ] = "identity_resolver"


class CharacterEntity(CandidateEntity):
    type: Literal[NodeType.CHARACTER]


class EventEntity(CandidateEntity):
    type: Literal[NodeType.EVENT]


class LocationEntity(CandidateEntity):
    type: Literal[NodeType.LOCATION]


class FactionEntity(CandidateEntity):
    type: Literal[NodeType.FACTION]


class ObjectEntity(CandidateEntity):
    type: Literal[NodeType.OBJECT]


class LoreEntity(CandidateEntity):
    type: Literal[NodeType.LORE]


class ArcEntity(CandidateEntity):
    type: Literal[NodeType.STORY_ARC]


class MysteryEntity(CandidateEntity):
    type: Literal[NodeType.MYSTERY]


E = TypeVar("E", bound=CandidateEntity)


class EntityBatch(StructuredModel, Generic[E]):
    entities: list[E] = Field(default_factory=list, max_length=3)


FOCUSED_SCHEMAS: dict[NodeType, type[StructuredModel]] = {
    NodeType.CHARACTER: EntityBatch[CharacterEntity],
    NodeType.EVENT: EntityBatch[EventEntity],
    NodeType.LOCATION: EntityBatch[LocationEntity],
    NodeType.FACTION: EntityBatch[FactionEntity],
    NodeType.OBJECT: EntityBatch[ObjectEntity],
    NodeType.LORE: EntityBatch[LoreEntity],
    NodeType.STORY_ARC: EntityBatch[ArcEntity],
    NodeType.MYSTERY: EntityBatch[MysteryEntity],
}


class KnowledgeAssessment(Assessment):
    in_universe: bool
    entity_type_valid: bool


class KnowledgeVerification(StructuredModel):
    assessments: list[KnowledgeAssessment] = Field(min_length=1, max_length=1)


class NarrativeAssessment(Assessment):
    content_kind: Literal["fictional-story", "real-world-publication", "uncertain"]
    entity_type_valid: bool


class NarrativeVerification(StructuredModel):
    assessments: list[NarrativeAssessment] = Field(min_length=1, max_length=1)
