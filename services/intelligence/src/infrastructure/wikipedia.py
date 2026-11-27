"""Reads Wikipedia article pages, which its robots rules allow, keeping their structure.

Text keeps the headings and list terms above it, so a character's entry in a long list
can be picked out. Episode tables keep each episode's title with its summary.
"""

import re
from urllib.parse import quote, urljoin, urlsplit

from bs4 import BeautifulSoup, Tag

from src.application.guide import LANGUAGES, Article, Block
from src.application.research import SourceRejected
from src.infrastructure.mediawiki import NAMESPACES
from src.infrastructure.sources import PublicDocumentFetcher, PublicSourcePolicy

HOSTS = [f"{code}.wikipedia.org" for code in LANGUAGES]
MAX_BYTES = 4_000_000
NOISE = (
    "style, script, figure, sup.reference, .mw-editsection, .navbox, .toc, .thumb, "
    ".reflist, ol.references, .mw-references-wrap, .ambox, .hatnote, rt, rp"
)
EPISODE_ROW = "module-episode-list-row"
# Headings of lists that point elsewhere and tell nothing about the story.
ENDMATTER = (
    "references",
    "external links",
    "see also",
    "notes",
    "further reading",
    "脚注",
    "注釈",
    "出典",
    "外部リンク",
    "関連項目",
    "参考",
    "參考",
    "外部链接",
    "外部連結",
    "参见",
    "參見",
    "注释",
    "註釋",
)
LISTS = ("dl", "ul", "ol", "table")


def _clean(value: str) -> str:
    return " ".join(value.split())


def _own_text(element: Tag) -> str:
    """An element's text without the lists nested inside it, which are read separately."""
    parts = []
    for piece in element.find_all(string=True):
        node = piece.parent
        while node is not None and node is not element and node.name not in LISTS:
            node = node.parent
        if node is element:
            parts.append(str(piece))
    return _clean("".join(parts))


def _episode(row: Tag) -> tuple[str, str] | None:
    """An episode's label and summary from the two table rows that hold them."""
    title = row.select_one("td.summary")
    following = row.find_next_sibling("tr")
    summary = following.select_one("td.description") if isinstance(following, Tag) else None
    if title is None or summary is None:
        return None
    number = row.find("th")
    label = f"Episode {_clean(number.get_text())}" if isinstance(number, Tag) else "Episode"
    return f"{label}: {_clean(title.get_text())}"[:200], _clean(summary.get_text(" "))


def parse_blocks(body: Tag) -> list[Block]:
    for noise in body.select(NOISE):
        noise.decompose()
    headings: dict[int, str] = {}
    terms: dict[int, str] = {}
    blocks: list[Block] = []

    def add(path: list[str], text: str) -> None:
        ended = any(word in h.casefold() for h in headings.values() for word in ENDMATTER)
        if len(text) > 1 and not ended:
            blocks.append(Block(tuple(p[:200] for p in path), text[:4000]))

    for element in body.find_all(["h2", "h3", "h4", "dt", "p", "li", "dd", "tr"]):
        above = [headings[level] for level in sorted(headings)]
        if element.name in ("h2", "h3", "h4"):
            level = int(element.name[1])
            headings = {k: v for k, v in headings.items() if k < level}
            headings[level] = _clean(element.get_text())
        elif element.name == "tr":
            if EPISODE_ROW in (element.get("class") or []):
                if episode := _episode(element):
                    add([*above, episode[0]], episode[1])
        elif element.find_parent("table"):
            continue
        elif element.name == "dt":
            if element.parent is not None:
                terms[id(element.parent)] = _own_text(element)
        elif element.name == "p" and element.find_parent(["li", "dd"]):
            continue
        else:
            lists = [id(parent) for parent in element.find_parents("dl")]
            named = [terms[key] for key in reversed(lists) if terms.get(key)]
            add([*above, *named], _own_text(element))
    return blocks


def parse_article(html: str, url: str, language: str) -> Article:
    soup = BeautifulSoup(html, "html.parser")
    # Notices share the class, so the article is the largest block.
    body = max(soup.select(".mw-parser-output"), key=lambda b: len(b.get_text()), default=None)
    if body is None:
        raise SourceRejected("source_has_no_usable_text")
    heading = soup.select_one("#firstHeading")
    licence = soup.select_one(
        'a[rel~="license"], link[rel~="license"], footer a[href*="creativecommons.org"], '
        'a[href*="creativecommons.org/licenses"]'
    )
    if licence is None:
        raise SourceRejected("source_licence_unknown")
    languages: dict[str, str] = {}
    for link in soup.select("a.interlanguage-link-target[hreflang]"):
        code, address = str(link.get("hreflang")), str(link.get("href"))
        if code in LANGUAGES and urlsplit(address).hostname == f"{code}.wikipedia.org":
            languages[code] = address
    links: dict[str, str] = {}
    # Links are written relative on some language editions and in full on others.
    for link in body.select("a[href][title]"):
        target = urlsplit(urljoin(url, str(link.get("href"))))
        title = str(link.get("title"))
        if (
            target.hostname == urlsplit(url).hostname
            and target.path.startswith("/wiki/")
            and not NAMESPACES.match(title)
            and "new" not in (link.get("class") or [])
        ):
            links.setdefault(title, _clean(link.get_text())[:100])
    canonical = soup.select_one('link[rel="canonical"]')
    revision = re.search(r'"wgRevisionId":\s*(\d+)', html)
    address = str(canonical.get("href")) if canonical else url
    if urlsplit(address).hostname != urlsplit(url).hostname:
        address = url
    return Article(
        title=_clean(heading.get_text()) if heading else address.rsplit("/", 1)[-1],
        url=address,
        language=language,
        licence=str(licence.get("href")),
        revision=revision.group(1) if revision else "unknown",
        links=list(links.items()),
        languages=languages,
        blocks=parse_blocks(body),
    )


class Wikipedia:
    def __init__(self, fetcher: PublicDocumentFetcher | None = None) -> None:
        self.fetcher = fetcher or PublicDocumentFetcher(
            PublicSourcePolicy(HOSTS), MAX_BYTES, MAX_BYTES
        )

    def address(self, language: str, title: str) -> str:
        if language not in LANGUAGES:
            raise SourceRejected("source_not_approved")
        name = quote(title.strip().replace(" ", "_"), safe=":_(),'!")
        return f"https://{language}.wikipedia.org/wiki/{name}"

    async def read(self, url: str) -> Article:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname not in HOSTS:
            raise SourceRejected("source_not_approved")
        if not parts.path.startswith("/wiki/"):
            raise SourceRejected("source_not_approved")
        html, final = await self.fetcher.get_html(url)
        host = urlsplit(final).hostname or ""
        return parse_article(html, final, host.split(".")[0])
