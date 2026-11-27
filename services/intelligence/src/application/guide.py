"""A guide: a cited summary, arc or character page written from an encyclopedia.

Every paragraph names the sources it came from. A translated source keeps the original
beside the English, so a reader can check it.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import Field

from src.application.research_contracts import StructuredModel

Kind = Literal["summary", "arc", "character"]
LANGUAGES = {"en": "English", "ja": "Japanese", "zh": "Chinese"}


@dataclass(frozen=True)
class Block:
    """One paragraph, list item or episode entry, under its headings and terms."""

    path: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class Article:
    title: str
    url: str
    language: str
    licence: str
    revision: str
    blocks: list[Block] = field(default_factory=list)
    # (page title, text shown) of links to other articles in the same language.
    links: list[tuple[str, str]] = field(default_factory=list)
    # Language code to the same subject's page in that language.
    languages: dict[str, str] = field(default_factory=dict)


class Encyclopedia(Protocol):
    def address(self, language: str, title: str) -> str: ...

    async def read(self, url: str) -> Article: ...


class GuideSource(StructuredModel):
    number: int = Field(ge=1)
    title: str = Field(max_length=300)
    url: str = Field(pattern=r"^https://", max_length=1000)
    language: str = Field(max_length=8)
    heading: str = Field(default="", max_length=300)
    text: str = Field(min_length=1, max_length=8000)
    # The untranslated paragraph, empty when the source is already English.
    original: str = Field(default="", max_length=8000)
    licence: str = Field(default="", max_length=300)
    revision: str = Field(default="", max_length=60)


class GuideParagraph(StructuredModel):
    text: str = Field(min_length=1, max_length=3000)
    cites: list[int] = Field(min_length=1, max_length=20)


class GuideSection(StructuredModel):
    heading: str = Field(min_length=1, max_length=100)
    # Empty when the sources say nothing on this.
    paragraphs: list[GuideParagraph] = Field(default_factory=list, max_length=60)


class CastMember(StructuredModel):
    name: str = Field(min_length=1, max_length=100)
    role: Literal["main", "supporting"]
    text: str = Field(min_length=1, max_length=600)
    cites: list[int] = Field(min_length=1, max_length=4)


class Guide(StructuredModel):
    schema_version: Literal[1] = 1
    kind: Kind
    story: str = Field(min_length=1, max_length=180)
    subject: str = Field(default="", max_length=120)
    title: str = Field(min_length=1, max_length=320)
    sections: list[GuideSection] = Field(max_length=12)
    cast: list[CastMember] = Field(default_factory=list, max_length=40)
    sources: list[GuideSource] = Field(max_length=600)
    notes: list[str] = Field(default_factory=list, max_length=200)
