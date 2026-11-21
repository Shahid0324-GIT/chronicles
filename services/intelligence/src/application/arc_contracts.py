"""Arc research state and prose contracts; neither constitutes canonical publication."""

from typing import Any, Literal
from uuid import UUID

from pydantic import Field, computed_field, model_validator

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
    developments: list["NarrativeDevelopment"] = Field(default_factory=list, max_length=80)
    omissions: list["DevelopmentOmission"] = Field(default_factory=list, max_length=80)


class DevelopmentOmission(StructuredModel):
    fact_ids: list[str] = Field(min_length=1, max_length=40)
    reason: Literal["duplicate", "incomplete", "unrelated", "insufficient_context"]
    explanation: str = Field(min_length=8, max_length=400)


class DevelopmentConnection(StructuredModel):
    from_key: str
    relation: Literal["context", "source_sequence", "consequence", "contrast", "resolution"]
    fact_ids: list[str] = Field(min_length=1, max_length=16)


class NarrativeDevelopment(StructuredModel):
    section_key: str
    key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    stage: Literal[
        "circumstance",
        "interaction",
        "action",
        "development",
        "decision",
        "conflict",
        "consequence",
    ]
    fact_ids: list[str] = Field(min_length=1, max_length=16)
    connections: list[DevelopmentConnection] = Field(default_factory=list, max_length=8)


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
    narrative_developments: list[NarrativeDevelopment] = Field(default_factory=list)
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
    section_focus: list[str] = Field(default_factory=list)
    organization_warnings: list[str] = Field(default_factory=list)
    organization_omissions: list[DevelopmentOmission] = Field(default_factory=list)
    status: Literal["partial"] = "partial"
    sections: list[ArcSectionDossier]
    accepted_facts: list[dict[str, Any]]
    reconstruction: dict[str, Any]
    revision: str


class ArcClaim(StructuredModel):
    text: str = Field(min_length=8, max_length=1000)
    fact_ids: list[str] = Field(min_length=1, max_length=12)


class ArcParagraph(StructuredModel):
    claims: list[ArcClaim] = Field(min_length=1, max_length=20)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fact_ids(self) -> list[str]:
        return list(dict.fromkeys(i for claim in self.claims for i in claim.fact_ids))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def text(self) -> str:
        return " ".join(c.text for c in self.claims)

    @model_validator(mode="before")
    @classmethod
    def compatible_grounded_text(cls, value: Any) -> Any:
        if isinstance(value, dict) and "fact_ids" in value:
            value = dict(value)
            supplied = value.pop("fact_ids")
            expected_ids = {
                i
                for claim in value.get("claims", [])
                for i in (
                    claim.fact_ids if isinstance(claim, ArcClaim) else claim.get("fact_ids", [])
                )
            }
            if set(supplied) != expected_ids:
                raise ValueError("Paragraph citations must match its individually cited claims")
        if isinstance(value, dict) and "text" in value:
            value = dict(value)
            text = value.pop("text")
            claims = value.get("claims", [])
            expected = " ".join(
                c.text if isinstance(c, ArcClaim) else c.get("text", "") for c in claims
            )
            if " ".join(str(text).split()) != " ".join(expected.split()):
                raise ValueError(
                    "Reader text must equal its individually grounded narrative claims"
                )
        return value


class ClaimReview(StructuredModel):
    index: int = Field(ge=0)
    verdict: Literal["supported", "unsupported", "uncertain"]
    reason: str = Field(min_length=3, max_length=400)


class ArcSemanticReview(StructuredModel):
    claims: list[ClaimReview]
    paragraphs_faithful: bool
    coherent: bool
    coherence_issues: list[str] = Field(default_factory=list, max_length=12)
    unsupported_connections: list[str] = Field(default_factory=list)


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
    status: Literal["partial", "withheld"] = "partial"
    sections: list[dict[str, Any]]
    coverage: list[ArcSectionCoverage]
    quality: dict[str, Any]
