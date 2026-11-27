"""MediaWiki sites, read through the API or as pages, within robots and delay rules."""

import re
from typing import Any
from urllib.parse import quote, urlencode, urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from src.application.research import SourceRejected
from src.application.scout import WikiLink, WikiPage, WikiSection
from src.application.story_library import LibrarySite
from src.infrastructure.sources import PublicDocumentFetcher

HIDDEN = (
    "table, style, script, figure, sup.reference, .mw-editsection, .navbox, .toc, "
    ".thumb, .infobox, .reflist, ol.references"
)
NAMESPACES = re.compile(
    r"^(file|category|special|template|user|help|talk|mediawiki|module)( talk)?:", re.I
)
HEADINGS = ("h2", "h3", "h4")


def _clean(value: str) -> str:
    return " ".join(value.split())


class _Trail:
    """The heading path at the current place, such as "Plot / The fair"."""

    def __init__(self) -> None:
        self.levels: dict[int, str] = {}

    def enter(self, heading: Tag) -> None:
        level = int(heading.name[1])
        self.levels = {k: v for k, v in self.levels.items() if k < level}
        self.levels[level] = _clean(heading.get_text())

    def path(self) -> str:
        return " / ".join(self.levels[k] for k in sorted(self.levels))


def parse_page(html: str) -> tuple[list[WikiSection], list[WikiLink]]:
    """Readable text by section, and the article links with the section they sit in."""
    soup = BeautifulSoup(html, "html.parser")
    for edit in soup.select(".mw-editsection"):
        edit.decompose()
    trail = _Trail()
    links: dict[str, WikiLink] = {}
    # Links come first: chapter lists often sit in tables, which carry no prose.
    for element in soup.find_all([*HEADINGS, "a"]):
        if element.name in HEADINGS:
            trail.enter(element)
            continue
        title = str(element.get("title") or "")
        classes = str(element.get("class") or "")
        if (
            title
            and str(element.get("href") or "").startswith("/")
            and "new" not in classes
            and not NAMESPACES.match(title)
        ):
            links.setdefault(title, WikiLink(trail.path(), title, _clean(element.get_text())[:80]))
    for hidden in soup.select(HIDDEN):
        hidden.decompose()
    trail = _Trail()
    texts: dict[str, list[str]] = {}
    for element in soup.find_all([*HEADINGS, "p", "li", "dd"]):
        if element.name in HEADINGS:
            trail.enter(element)
        elif not element.find_parent(["p", "li", "dd"]):
            if text := _clean(element.get_text()):
                texts.setdefault(trail.path(), []).append(text)
    return (
        [WikiSection(heading, "\n".join(parts)) for heading, parts in texts.items()],
        list(links.values()),
    )


class MediaWikiPages:
    """A wiki read as ordinary article pages, for sites that keep agents off their API."""

    def __init__(self, config: LibrarySite, fetcher: PublicDocumentFetcher) -> None:
        self.config, self.fetcher = config, fetcher
        self._credit: tuple[str, str] | None = None
        self._pages: dict[str, WikiPage] = {}

    async def credit(self) -> tuple[str, str]:
        if self._credit is None:
            raise SourceRejected("source_licence_unknown")
        return self._credit

    async def search(self, query: str, limit: int) -> list[str]:
        return []

    async def page(self, title: str) -> WikiPage:
        if title in self._pages:
            return self._pages[title]
        url = self.config.pages + quote(title.replace(" ", "_"), safe="/:()'")
        html, final = await self.fetcher.get_html(url)
        soup = BeautifulSoup(html, "html.parser")
        # Indicators and notices use the same class, so the article is the largest one.
        blocks = soup.select(".mw-parser-output")
        body = max(blocks, key=lambda b: len(b.get_text()), default=None)
        if body is None:
            raise SourceRejected("source_has_no_usable_text")
        heading = soup.select_one("#firstHeading")
        name = _clean(heading.get_text()) if heading else title
        if self._credit is None:
            named = soup.select_one('meta[property="og:site_name"]')
            site = str(named.get("content")) if named else str(urlsplit(final).hostname)
            licence = soup.select_one(
                'a[rel~="license"], link[rel~="license"], footer a[href*="creativecommons.org"], '
                '#footer a[href*="creativecommons.org"], a[href*="creativecommons.org/licenses"]'
            )
            self._credit = (site, str(licence.get("href")) if licence else "Licence not stated")
        canonical = soup.select_one('link[rel="canonical"]')
        address = str(canonical.get("href")) if canonical else final
        if urlsplit(address).hostname != urlsplit(final).hostname:
            address = final
        revision = re.search(r'"wgRevisionId":\s*(\d+)', html)
        sections, links = parse_page(str(body))
        page = WikiPage(
            title=name,
            url=address,
            revision=revision.group(1) if revision else "unknown",
            sections=sections,
            links=links,
        )
        self._pages[title] = page
        return page


class MediaWikiSite:
    def __init__(self, config: LibrarySite, fetcher: PublicDocumentFetcher) -> None:
        self.config, self.fetcher = config, fetcher
        self._info: dict[str, Any] = {}
        self._pages: dict[str, WikiPage] = {}

    async def _call(self, **parameters: str | int) -> dict[str, Any]:
        query = urlencode({**parameters, "format": "json", "formatversion": 2})
        data = await self.fetcher.get_json(f"{self.config.api}?{query}")
        if "error" in data:
            raise SourceRejected("source_api_rejected")
        return data

    async def _site(self) -> dict[str, Any]:
        if not self._info:
            data = await self._call(action="query", meta="siteinfo", siprop="general|rightsinfo")
            self._info = data["query"]
        return self._info

    async def credit(self) -> tuple[str, str]:
        info = await self._site()
        rights = info.get("rightsinfo") or {}
        licence = _clean(f"{rights.get('text', '')} {rights.get('url', '')}")
        return str(info["general"].get("sitename") or "Wiki"), licence or "Licence not stated"

    async def search(self, query: str, limit: int) -> list[str]:
        data = await self._call(action="query", list="search", srsearch=query[:300], srlimit=limit)
        return [str(hit["title"]) for hit in data["query"]["search"]]

    async def page(self, title: str) -> WikiPage:
        if title in self._pages:
            return self._pages[title]
        general = (await self._site())["general"]
        data = await self._call(
            action="parse", page=title, prop="text|revid", redirects=1, disabletoc=1
        )
        parsed = data["parse"]
        sections, links = parse_page(str(parsed["text"]))
        name = str(parsed["title"])
        path = str(general["articlepath"]).replace("$1", quote(name.replace(" ", "_"), safe="/:()"))
        server = str(general["server"])
        if server.startswith("//"):
            server = "https:" + server
        page = WikiPage(
            title=name,
            url=urljoin(server, path),
            revision=str(parsed.get("revid", "")),
            sections=sections,
            links=links,
        )
        self._pages[title] = page
        return page
