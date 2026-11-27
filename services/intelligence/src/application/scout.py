"""Scout: find the pages that tell one arc on approved sites and keep their story sections.

A model only chooses among titles the site itself returned; code checks the choice, and
every saved page carries its link and licence.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import Field

from src.application.knowledge_presentation import Infer
from src.application.research_contracts import StructuredModel
from src.application.story_library import LibrarySite, LibrarySource

CANDIDATES = 160
OVERVIEWS = 3


@dataclass(frozen=True)
class WikiLink:
    section: str
    title: str
    label: str


@dataclass(frozen=True)
class WikiSection:
    heading: str
    text: str


@dataclass(frozen=True)
class WikiPage:
    title: str
    url: str
    revision: str
    sections: list[WikiSection] = field(default_factory=list)
    links: list[WikiLink] = field(default_factory=list)


class WikiSite(Protocol):
    config: LibrarySite

    async def credit(self) -> tuple[str, str]:
        """The site's name and the licence it states for its text."""
        ...

    async def search(self, query: str, limit: int) -> list[str]:
        """Matching titles; empty when the site does not offer search to agents."""
        ...

    async def page(self, title: str) -> WikiPage: ...


class PlannedPage(StructuredModel):
    site: str = Field(max_length=300)
    title: str = Field(min_length=1, max_length=250)
    position: int = Field(ge=1, le=100000)


class PagePlan(StructuredModel):
    """``pages.json``: what will be read, editable by the user before or after fetching."""

    pages: list[PlannedPage] = Field(max_length=80)
    # The page the search started from; sections named after it are this arc's.
    focus: str = Field(default="", max_length=250)


class PageChoice(StructuredModel):
    number: int
    position: int


class PageChoices(StructuredModel):
    pages: list[PageChoice] = Field(max_length=60)


async def discover(
    world_title: str,
    arc_title: str,
    about: str,
    position_word: str,
    site: WikiSite,
    infer: Infer,
    progress: Callable[[str], None] = lambda _message: None,
    start: list[str] | None = None,
) -> list[PlannedPage]:
    """Read the likeliest overview pages and let a model pick from what they link to."""
    hits: list[str] = list(start or [])
    for query in (f"{world_title} {arc_title}", f"{arc_title} {about}".strip(), world_title):
        for title in await site.search(query, 8):
            if title not in hits:
                hits.append(title)
    if not hits:
        raise ValueError("No pages to start from; name an overview page of this story with --start")
    found: dict[str, str] = {title: "search result" for title in hits}
    for title in hits[:OVERVIEWS]:
        progress(f"  reading overview: {title}")
        page = await site.page(title)
        for link in page.links:
            where = f"{page.title} > {link.section or 'introduction'}"
            if link.label and link.label != link.title:
                where += f" ({link.label})"
            # A link says more about a page than a bare search hit does.
            if found.get(link.title, "search result") == "search result":
                found[link.title] = where
    # Search hits first, then links under story-like headings, then the rest.
    story = ("chapter", "episode", "plot", "story", "arc", "volume", "quest")
    ranked = sorted(
        found,
        key=lambda t: (
            t not in hits,
            not any(word in found[t].split("(")[0].casefold() for word in story),
        ),
    )[:CANDIDATES]
    choices = PageChoices.model_validate(
        await infer(
            "Choose the wiki pages whose text tells this story arc, from the numbered "
            "candidates only. Prefer one page per chapter, episode or quest, covering the "
            "whole requested range, over overview, list, character or game pages. Give each "
            f"chosen number the {position_word} number at which it happens, so they sort "
            "into story order.\n"
            'Return only JSON: {"pages":[{"number":1,"position":1}]}\n'
            + json.dumps(
                {
                    "story": world_title,
                    "arc": arc_title,
                    "requested": about or arc_title,
                    "candidates": {
                        str(n): f"{title} | {found[title][:160]}"
                        for n, title in enumerate(ranked, 1)
                    },
                },
                ensure_ascii=False,
            ),
            PageChoices,
            # A cloud-preferred task, so allowed sites are not planned on the small local model.
            "presentation",
        )
    )
    planned: dict[str, PlannedPage] = {}
    for choice in choices.pages:
        if 0 < choice.number <= len(ranked) and 0 < choice.position <= 100000:
            title = ranked[choice.number - 1]
            planned.setdefault(
                title,
                PlannedPage(site=site.config.address, title=title, position=choice.position),
            )
    return sorted(planned.values(), key=lambda p: (p.position, p.title))


def _under(page: WikiPage, focus: str) -> str:
    """Text under headings named after the arc's own page, such as one game among many."""
    name = focus.casefold()
    return "\n".join(
        s.text for s in page.sections if name and name in s.heading.casefold().split(" / ")
    )


def story_text(page: WikiPage, wanted: list[str]) -> str:
    """Story sections. A name with "/" is an exact heading path and what lies under it;
    a single word matches any heading that contains it."""
    names = [w.casefold() for w in wanted]

    def matches(heading: str) -> bool:
        return any(
            heading == name or heading.startswith(name + " / ") if "/" in name else name in heading
            for name in names
        )

    return "\n".join(s.text for s in page.sections if s.heading and matches(s.heading.casefold()))


async def read_page(
    planned: PlannedPage, site: WikiSite, sections: list[str] | None = None, focus: str = ""
) -> tuple[LibrarySource | None, str]:
    """One page as a library source, or the reason it could not be used."""
    page = await site.page(planned.title)
    text = "" if sections else _under(page, focus)
    if len(text) < 200:
        text = story_text(page, sections or site.config.sections)
    note = ""
    # An arc that names its own headings must not fall back to other material.
    if len(text) < 200 and not sections:
        text = "\n".join(s.text for s in page.sections if not s.heading)
        note = f"{page.title}: no story section found, kept only the introduction"
    if len(text) < 200:
        return None, f"{page.title}: too little story text to use"
    name, licence = await site.credit()
    return (
        LibrarySource(
            url=page.url,
            title=f"{page.title} ({name})"[:300],
            position=planned.position,
            text=text[:500_000],
            licence=f"{licence}. Text by {name} contributors, revision {page.revision}"[:300],
            cloud_allowed=site.config.cloud_allowed,
        ),
        note,
    )
