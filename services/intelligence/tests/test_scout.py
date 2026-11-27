import json
from urllib.parse import parse_qs, urlsplit

import pytest

from src.application.scout import PageChoices, PlannedPage, discover, read_page
from src.application.story_library import LibrarySite
from src.infrastructure.mediawiki import MediaWikiPages, MediaWikiSite, parse_page
from src.infrastructure.sources import PublicDocumentFetcher, PublicSourcePolicy, SourceRejected

API = "https://wiki.example.org/w/api.php"
FAIR = "Mira climbed onto a cart and told the fair what she had found in the orchard. " * 4
PAGE_HTML = f"""<div class="mw-parser-output">
<p>An overview of the chapter.</p>
<table class="infobox"><tr><td>Hidden facts
<a href="/wiki/Ch_2" title="Ch 2">next</a></td></tr></table>
<div class="mw-heading"><h2>Plot</h2><span class="mw-editsection">[edit]</span></div>
<p>{FAIR}<sup class="reference">[1]</sup></p>
<h3>The sluice</h3>
<p>The <a href="/wiki/Wheel" title="Wheel">wheel</a>house turned at last.</p>
<h2>Trivia</h2>
<ul><li>A fact about printing.<p>Nested.</p></li></ul>
<a href="/wiki/File:Art.png" title="File:Art.png">art</a>
<a href="/index.php?title=Gone" class="new" title="Gone">missing</a>
</div>"""


class Replies(PublicDocumentFetcher):
    """Canned API replies behind the real URL, robots and delay checks."""

    def __init__(self, robots=b"User-agent: *\nCrawl-delay: 7\nDisallow: /private") -> None:
        super().__init__(PublicSourcePolicy(["wiki.example.org"]), 100_000, 100_000)
        self.robots, self.calls = robots, []

    async def _request(self, url):
        self.calls.append(url)
        if url.endswith("/robots.txt"):
            return 200, {}, self.robots
        query = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        if query.get("meta") == "siteinfo":
            body = {
                "query": {
                    "general": {
                        "sitename": "Orchard Wiki",
                        "articlepath": "/wiki/$1",
                        "server": "//wiki.example.org",
                    },
                    "rightsinfo": {"text": "CC BY-SA", "url": "https://example.org/by-sa"},
                }
            }
        elif query.get("list") == "search":
            body = {"query": {"search": [{"title": "Orchard arc"}]}}
        else:
            body = {"parse": {"title": query["page"], "revid": 42, "text": PAGE_HTML}}
        return 200, {"content-type": "application/json"}, json.dumps(body).encode()


def site(fetcher, **settings):
    return MediaWikiSite(LibrarySite(api=API, **settings), fetcher)


def test_page_text_is_kept_by_section_without_boxes_or_markers():
    sections, links = parse_page(PAGE_HTML)
    told = {s.heading: s.text for s in sections}
    assert list(told) == ["", "Plot", "Plot / The sluice", "Trivia"]
    assert "[1]" not in told["Plot"] and "Hidden facts" not in str(told)
    # Linked words stay joined, and nested blocks are read once.
    assert told["Plot / The sluice"] == "The wheelhouse turned at last."
    assert str(told).count("Nested.") == 1
    assert [(link.title, link.section) for link in links] == [
        ("Ch 2", ""),
        ("Wheel", "Plot / The sluice"),
    ]


async def test_a_page_becomes_a_credited_source_with_only_its_story():
    fetcher = Replies()
    reader = site(fetcher, cloud_allowed=True)
    source, note = await read_page(PlannedPage(site=API, title="Chapter one", position=3), reader)
    assert source and not note
    assert source.position == 3 and source.cloud_allowed
    assert source.url == "https://wiki.example.org/wiki/Chapter_one"
    assert "wheelhouse" in source.text and "printing" not in source.text
    assert "CC BY-SA" in source.licence and "revision 42" in source.licence
    # The site's requested pace is adopted and its rules are read once.
    assert fetcher.delays == {"wiki.example.org": 7.0}
    assert sum(url.endswith("robots.txt") for url in fetcher.calls) == 1


async def test_a_site_that_disallows_its_api_is_not_read():
    fetcher = Replies(b"User-agent: *\nDisallow: /w/")
    with pytest.raises(SourceRejected, match="robots_disallowed"):
        await site(fetcher).search("orchard", 5)
    assert fetcher.calls == ["https://wiki.example.org/robots.txt"]


async def test_discovery_keeps_only_listed_candidates_in_story_order():
    async def infer(prompt, schema, task):
        data = json.loads(prompt[prompt.rindex("\n") + 1 :])
        numbers = {text.split(" | ")[0]: int(n) for n, text in data["candidates"].items()}
        assert set(numbers) == {"Orchard arc", "Ch 2", "Wheel"}
        return PageChoices.model_validate(
            {
                "pages": [
                    {"number": numbers["Wheel"], "position": 2},
                    {"number": numbers["Ch 2"], "position": 1},
                    {"number": numbers["Ch 2"], "position": 5},
                    {"number": 999, "position": 1},
                ]
            }
        )

    plan = await discover("Orchard", "Frost", "", "chapter", site(Replies()), infer)
    assert [(p.title, p.position) for p in plan] == [("Ch 2", 1), ("Wheel", 2)]


async def test_a_site_can_be_read_as_pages_with_its_stated_licence():
    html = (
        '<meta property="og:site_name" content="Orchard Wiki"><h1 id="firstHeading">Fair</h1>'
        '<div class="mw-parser-output"><p>A header notice.</p></div>'
        f'<script>{{"wgRevisionId":7}}</script><div class="mw-parser-output"><h2>Story</h2>'
        f"<h3>Frost</h3><p>{FAIR}</p><h3>Frost II</h3><p>{'A later game. ' * 30}</p></div>"
        '<a rel="license" href="https://creativecommons.org/licenses/by-sa/4.0/">licence</a>'
    )

    class Pages(PublicDocumentFetcher):
        async def _request(self, url):
            if url.endswith("/robots.txt"):
                return 200, {}, b"User-agent: *\nDisallow: /api.php"
            assert url == "https://wiki.example.org/Harvest_Fair"
            return 200, {"content-type": "text/html"}, html.encode()

    config = LibrarySite(pages="https://wiki.example.org/", sections=["story"])
    reader = MediaWikiPages(
        config, Pages(PublicSourcePolicy(["wiki.example.org"]), 100_000, 100_000)
    )
    assert await reader.search("fair", 5) == []
    planned = PlannedPage(site=config.address, title="Harvest Fair", position=1)
    # An arc naming one story's heading leaves the other stories out.
    source, _ = await read_page(planned, reader, ["story / frost"])
    assert source and "told the fair" in source.text and "later game" not in source.text
    assert source.url == "https://wiki.example.org/Harvest_Fair"
    assert "licenses/by-sa/4.0" in source.licence and "revision 7" in source.licence
    missing, reason = await read_page(planned, reader, ["story / thaw"])
    assert missing is None and "too little" in reason


def test_a_site_is_reached_one_way():
    for settings in ({}, {"api": API, "pages": "https://wiki.example.org/"}):
        with pytest.raises(ValueError, match="either"):
            LibrarySite(**settings)


async def test_headings_named_after_the_starting_page_are_the_arcs_own():
    first, second = "The first game tells of the frost. " * 8, "A sequel tells of the thaw. " * 8
    html = (
        '<div class="mw-parser-output"><h2>Story</h2>'
        f"<h3>Frost</h3><p>{first}</p><h3>Thaw</h3><p>{second}</p></div>"
        '<a rel="license" href="https://creativecommons.org/licenses/by-sa/4.0/">l</a>'
    )

    class Pages(PublicDocumentFetcher):
        async def _request(self, url):
            if url.endswith("/robots.txt"):
                return 404, {}, b""
            return 200, {"content-type": "text/html"}, html.encode()

    config = LibrarySite(pages="https://wiki.example.org/")
    reader = MediaWikiPages(
        config, Pages(PublicSourcePolicy(["wiki.example.org"]), 100_000, 100_000)
    )
    planned = PlannedPage(site=config.address, title="Harbor", position=1)
    own, _ = await read_page(planned, reader, None, "Thaw")
    assert own and "thaw" in own.text and "frost" not in own.text
    everything, _ = await read_page(planned, reader, None, "Spring")
    assert everything and "frost" in everything.text and "thaw" in everything.text
