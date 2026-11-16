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
    discovery_summary: str = Field(default="", max_length=1000)
    discovery_parent_url: str | None = Field(default=None, max_length=2000)
    discovery_depth: int = Field(default=0, ge=0, le=10)
    discovery_api: Literal["mediawiki-search"] | None = None
    follow_links: bool = False
    render_javascript: bool = False
    eligible_section_terms: list[str] = Field(default_factory=list, max_length=20)
    discovery_index: bool = False
    discovery_path_prefix: str | None = Field(default=None, max_length=1000)
    cloud_content_allowed: bool = False
    imported_content_cloud_allowed: bool = False
    derived_from: str | None = None
    presentation_position: int | None = Field(default=None, ge=1, le=100000)
    position_basis: str | None = None

    @model_validator(mode="after")
    def validate_locator(self) -> "SourceRegistration":
        if self.imported_content_cloud_allowed and (
            self.access_method != "import" or not self.cloud_content_allowed
        ):
            raise ValueError("Imported sharing requires explicit import and cloud permissions")
        if any(not term.strip() or len(term) > 100 for term in self.eligible_section_terms):
            raise ValueError("Eligible section terms require explicit nonempty labels")
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
        if self.discovery_api and (
            self.access_method != "mediawiki" or self.retrieval_policy != "permitted" or p.query
        ):
            raise ValueError(
                "Search APIs require an explicitly permitted query-free MediaWiki endpoint"
            )
        if self.render_javascript and (
            self.access_method != "html" or self.retrieval_policy != "permitted"
        ):
            raise ValueError("Rendered extraction requires explicit permitted HTML registration")
        if self.discovery_path_prefix is not None and (
            not self.discovery_path_prefix.startswith("/")
            or ".." in self.discovery_path_prefix
            or "?" in self.discovery_path_prefix
            or self.retrieval_policy != "permitted"
            or self.access_method != "html"
        ):
            raise ValueError("Discovery rules require an explicit permitted HTML path prefix")
        return self


class SourceEntry(SourceRegistration):
    id: UUID
    domain: str
    health: str
    last_success: datetime | None
    last_error: str | None
    retry_at: datetime | None = None


class SourceDiscovery(StructuredModel):
    universe_id: UUID
    continuity_id: UUID
    universe_name: str = Field(min_length=2, max_length=200)
    topics: list[str] = Field(default_factory=list, max_length=5)
