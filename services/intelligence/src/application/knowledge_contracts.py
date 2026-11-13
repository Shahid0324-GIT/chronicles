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
from src.domain.value_objects import NodeType


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


class RelationshipAnalysis(StructuredModel):
    relationships: list[CandidateRelationship] = Field(default_factory=list, max_length=8)


class RollbackRequest(StructuredModel):
    reason: str = Field(min_length=10, max_length=500)


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
