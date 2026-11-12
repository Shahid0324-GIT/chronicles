from uuid import UUID

from pydantic import Field, model_validator

from src.application.research_contracts import StructuredModel


class SourceInput(StructuredModel):
    url: str | None = Field(default=None, max_length=2000)
    text: str | None = Field(default=None, min_length=30, max_length=30_000)
    title: str = Field(default="", max_length=300)
    permission_basis: str = Field(min_length=10, max_length=500)
    source_scope: str = Field(min_length=5, max_length=500)

    @model_validator(mode="after")
    def one_input(self) -> "SourceInput":
        if bool(self.url) == bool(self.text):
            raise ValueError("Provide exactly one approved public URL or imported text")
        return self


class ResearchRequest(StructuredModel):
    universe_id: UUID
    continuity_id: UUID
    objective: str = Field(min_length=10, max_length=1500)
    sources: list[SourceInput] = Field(default_factory=list, max_length=20)
    allow_search: bool = False


class FetchedDocument(StructuredModel):
    url: str
    title: str
    publisher: str
    text: str
    truncated: bool
