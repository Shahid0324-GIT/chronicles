from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import Field, model_validator

from src.application.research_contracts import StructuredModel


class SourceRegistration(StructuredModel):
    universe_id: UUID
    name: str = Field(min_length=2, max_length=300)
    url: str = Field(max_length=2000)
    category: Literal[
        "official",
        "episode-guide",
        "game-lore",
        "dedicated-wiki",
        "reference",
        "discussion",
        "novel-excerpt",
        "chapter-index",
        "side-story",
        "character-profile",
        "item-description",
        "book",
        "quest",
        "creator-qa",
    ]
    media: list[str] = Field(min_length=1, max_length=8)
    continuity_ids: list[UUID] = Field(min_length=1, max_length=10)
    access_method: Literal["html", "mediawiki", "official-api", "import", "navigation"]
    authority: Literal["primary", "secondary", "unverified"]
    discovery_priority: int = Field(default=50, ge=0, le=100)
    topics: list[str] = Field(default_factory=list, max_length=30)
    retrieval_policy: Literal["permitted", "navigation-only"] = "navigation-only"
    permission_basis: str = Field(min_length=10, max_length=500)
    attribution: str = Field(min_length=3, max_length=500)
    selectors: dict[str, str] = Field(default_factory=dict)
    revision: str | None = None
    discovery_origin: str | None = Field(default=None, max_length=1500)
    cloud_content_allowed: bool = False
    derived_from: str | None = None
    presentation_position: int | None = Field(default=None, ge=1, le=100000)
    position_basis: str | None = None

    @model_validator(mode="after")
    def validate_locator(self) -> "SourceRegistration":
        p = urlsplit(self.url)
        if (
            p.scheme not in {"http", "https"}
            or not p.hostname
            or p.username
            or p.password
            or p.port not in {None, 80, 443}
        ):
            raise ValueError("Registry requires a public HTTP(S) reference without credentials")
        if set(self.selectors) - {"start_at", "end_before"}:
            raise ValueError("Only explicit section markers are supported")
        if any(not value or len(value) > 200 for value in self.selectors.values()):
            raise ValueError("Section markers must contain one to 200 characters")
        if self.access_method == "navigation" and self.retrieval_policy != "navigation-only":
            raise ValueError("Navigational references cannot authorize ingestion")
        return self


class SourceEntry(SourceRegistration):
    id: UUID
    domain: str
    health: str
    last_success: datetime | None
    last_error: str | None


class SourceDiscovery(StructuredModel):
    universe_id: UUID
    continuity_id: UUID
    universe_name: str = Field(min_length=2, max_length=200)
    topics: list[str] = Field(default_factory=list, max_length=5)
