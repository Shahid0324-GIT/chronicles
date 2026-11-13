from uuid import UUID

from pydantic import Field

from src.application.knowledge_types import KnowledgeCategory
from src.application.research_contracts import StructuredModel


class PresentedStatement(StructuredModel):
    text: str = Field(min_length=8, max_length=500)
    fact_ids: list[str] = Field(min_length=1, max_length=8)


class PresentationDraft(StructuredModel):
    display_title: str = Field(min_length=5, max_length=100)
    short_summary: str = Field(min_length=12, max_length=350)
    statements: list[PresentedStatement] = Field(min_length=1, max_length=4)


class GroundingAssessment(StructuredModel):
    entailed: bool
    english: bool
    names_consistent: bool
    agency_and_tense_preserved: bool
    unsupported_relationships: bool
    reason: str = Field(min_length=3, max_length=300)


class EntrySection(StructuredModel):
    name: str
    statements: list[PresentedStatement]


class EncyclopediaEntry(StructuredModel):
    id: UUID
    entry_type: KnowledgeCategory
    graph_type: str
    display_title: str
    short_introduction: str
    detailed_overview: str
    aliases: list[str]
    original_names: list[str]
    sections: list[EntrySection]
    connections: list[dict[str, str]]
    source_references: list[dict[str, str]]
    continuity_id: UUID
    language: str
    spoiler_position: int | None
    knowledge_revision: str
    presentation: dict[str, object]
