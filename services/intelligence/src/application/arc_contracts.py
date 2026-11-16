"""Arc research state and prose contracts; neither constitutes canonical publication."""

from typing import Any, Literal
from uuid import UUID

from pydantic import Field, model_validator

from src.application.research_contracts import StructuredModel

Facet = Literal[
    "circumstances",
    "development",
    "action",
    "decision",
    "conflict",
    "consequence",
    "character_journey",
    "lore",
    "story_impact",
    "retrospective",
    "adaptation",
]


class KnowledgePositions(StructuredModel):
    """Unknown coordinates stay unknown. Historical occurrence is never a reveal fence."""

    basis: str
    occurrence: str | None = None
    narrative: int | None = Field(default=None, ge=1)
    reveal: int | None = Field(default=None, ge=1)
    evidence_boundaries: list[int] = Field(default_factory=list)


class ArcSectionPlan(StructuredModel):
    key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)
    title: str = Field(min_length=3, max_length=150)
    objective: str = Field(min_length=10, max_length=1500)
    first_position: int | None = Field(default=None, ge=1)
    last_position: int | None = Field(default=None, ge=1)
    questions: list[str] = Field(default_factory=list, max_length=12)
    outline_evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def ordered(self) -> "ArcSectionPlan":
        if self.first_position and self.last_position and self.first_position > self.last_position:
            raise ValueError("Section boundaries are ordered source coordinates")
        return self


class ArcPlan(StructuredModel):
    status: Literal["provisional_not_canon"] = "provisional_not_canon"
    sections: list[ArcSectionPlan] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique(self) -> "ArcPlan":
        if len({s.key for s in self.sections}) != len(self.sections):
            raise ValueError("Section keys must be unique")
        return self


class DevelopmentBinding(StructuredModel):
    """An editorial assignment of accepted assertions, not new story assertions."""

    section_key: str
    facet: Facet
    fact_ids: list[str] = Field(min_length=1, max_length=16)


class ArcUnderstanding(StructuredModel):
    bindings: list[DevelopmentBinding] = Field(default_factory=list, max_length=200)


class ArcSectionCoverage(StructuredModel):
    research: Literal["not_researched", "partial", "sufficient", "blocked", "contradictory"]
    presentation: Literal["not_ready", "ready", "validated", "withheld"]
    supported_facets: list[Facet]
    missing_facets: list[Facet]
    gaps: list[str]


class ArcSectionDossier(StructuredModel):
    id: UUID
    plan: ArcSectionPlan
    developments: list[DevelopmentBinding]
    coverage: ArcSectionCoverage
    revision: str


class ArcDossier(StructuredModel):
    version: Literal["arc-dossier-v1"] = "arc-dossier-v1"
    arc_id: UUID
    universe_id: UUID
    continuity_id: UUID
    title: str
    perspective: Literal["bounded", "full_lore"]
    spoiler_position: int | None
    source_range: tuple[int, int]
    plan_status: Literal["provisional_not_canon"] = "provisional_not_canon"
    status: Literal["partial"] = "partial"
    sections: list[ArcSectionDossier]
    accepted_facts: list[dict[str, Any]]
    reconstruction: dict[str, Any]
    revision: str


class ArcParagraph(StructuredModel):
    text: str = Field(min_length=20, max_length=5000)
    fact_ids: list[str] = Field(min_length=1, max_length=40)


class ArcSectionDraft(StructuredModel):
    heading: str = Field(min_length=3, max_length=150)
    paragraphs: list[ArcParagraph] = Field(min_length=1, max_length=12)


class ArcArticle(StructuredModel):
    version: Literal["arc-article-v1"] = "arc-article-v1"
    arc_id: UUID
    continuity_id: UUID
    title: str
    perspective: Literal["bounded", "full_lore"]
    spoiler_position: int | None
    dossier_revision: str
    status: Literal["partial"] = "partial"
    sections: list[dict[str, Any]]
    coverage: list[ArcSectionCoverage]
    quality: dict[str, Any]
