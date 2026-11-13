"""Validated model structures, not canonical graph records."""

from dataclasses import dataclass
from typing import Literal, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.value_objects import NodeType, RelationshipType

T = TypeVar("T", bound=BaseModel)
Task = Literal[
    "planning", "extraction", "verification", "identity_resolution", "relationship_analysis"
]


class StructuredModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResearchPlan(StructuredModel):
    questions: list[str] = Field(min_length=1, max_length=5)
    queries: list[str] = Field(default_factory=list, max_length=5)


class Citation(StructuredModel):
    passage_id: UUID
    quote: str = Field(min_length=12, max_length=400)


class CandidateEntity(StructuredModel):
    event: dict[str, object] | None = None
    name: str = Field(min_length=1, max_length=200)
    type: NodeType
    description: str = Field(min_length=5, max_length=600)
    evidence: list[Citation] = Field(min_length=1, max_length=3)


class CandidateRelationship(StructuredModel):
    source_id: UUID | None = None
    target_id: UUID | None = None
    source_name: str = Field(min_length=1, max_length=200)
    target_name: str = Field(min_length=1, max_length=200)
    type: RelationshipType
    description: str = Field(min_length=5, max_length=600)
    evidence: list[Citation] = Field(min_length=1, max_length=3)


class Extraction(StructuredModel):
    entities: list[CandidateEntity] = Field(default_factory=list, max_length=12)
    relationships: list[CandidateRelationship] = Field(default_factory=list, max_length=8)


class Assessment(StructuredModel):
    claim_id: UUID
    decision: Literal["supported", "disputed", "insufficient", "review"]
    reason: str = Field(min_length=3, max_length=600)

    material_conflict: bool = False
    continuity_matches: bool = True
    contradiction_evidence: list[Citation] = Field(default_factory=list, max_length=3)


class Verification(StructuredModel):
    assessments: list[Assessment] = Field(max_length=16)


@dataclass(frozen=True)
class InferenceUsage:
    provider: str
    model: str
    credential: str
    task: str
    status: str
    elapsed_ms: int
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class InferenceResult:
    value: BaseModel
    usage: InferenceUsage


class InferenceFailure(Exception):
    """Only sanitized codes cross the infrastructure boundary."""

    def __init__(self, code: str, retry_after: float = 0) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after


class InferenceProvider(Protocol):
    name: str
    model: str
    credential: str

    async def available(self) -> bool: ...

    async def generate(
        self, system: str, prompt: str, schema: type[T], task: Task
    ) -> InferenceResult: ...


class Inference(Protocol):
    usage: list[InferenceUsage]

    async def generate(
        self,
        system: str,
        prompt: str,
        schema: type[T],
        task: Task,
        *,
        public_source_content: bool = False,
    ) -> InferenceResult: ...
