"""Explicit cited research boundaries, separate from discovered canonical facts."""

from uuid import UUID, uuid5

from pydantic import Field, model_validator

from src.application.research_contracts import StructuredModel


class ArcResearchScope(StructuredModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=100)
    continuity_id: UUID
    position_basis: str = "manga-chapter"
    first_position: int = Field(ge=1)
    last_position: int = Field(ge=1)
    references: list[str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def ordered(self) -> "ArcResearchScope":
        if self.last_position < self.first_position or self.position_basis != "manga-chapter":
            raise ValueError("Arc scope requires an ordered manga chapter boundary")
        if any(not url.startswith("https://") for url in self.references):
            raise ValueError("Arc boundary references require HTTPS attribution")
        return self

    @property
    def id(self) -> str:
        return str(uuid5(self.continuity_id, "story-scope:" + self.slug))
