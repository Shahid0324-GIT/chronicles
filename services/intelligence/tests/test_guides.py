"""Search and guide pages, with an invented story, a fake encyclopedia and fake models."""

import json
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from src.application.guide import Article, Block, Guide
from src.application.guide_builder import build_guide
from src.application.guide_jobs import GuideRequest, guide_key
from src.application.guide_research import Passage, main_page, translate
from src.application.guide_writer import cast_entries
from src.application.research import SourceRejected
from src.application.research_contracts import InferenceFailure, Task
from src.application.search_intent import understand
from src.infrastructure.config.settings import Settings
from src.infrastructure.guide_service import Guides
from src.infrastructure.wikipedia import Wikipedia, parse_article
from src.main import create_app

LICENCE = "https://creativecommons.org/licenses/by-sa/4.0/"
HTML = """<html><head><link rel="canonical" href="https://en.wikipedia.org/wiki/Lantern_Marsh">
<script>{"wgRevisionId":42}</script></head><body>
<h1 id="firstHeading">Lantern Marsh</h1>
<a class="interlanguage-link-target" hreflang="zh"
 href="https://zh.wikipedia.org/wiki/Lantern">zh</a>
<div class="mw-parser-output">
<p>Lantern Marsh is an invented story.<sup class="reference">[1]</sup></p>
<div class="mw-heading"><h2>Characters</h2></div>
<dl><dt>Wren Alder</dt><dd>A ferry keeper who keeps the last lamp.
<ul><li>She cannot swim.</li></ul></dd></dl>
<p><a href="/wiki/Wren_Alder" title="Wren Alder">Wren</a>
<a href="https://en.wikipedia.org/wiki/Lamp_(Lantern_Marsh)" title="Lamp (Lantern Marsh)">lamp</a>
<a href="/wiki/File:x.png" title="File:x.png">file</a>
<a href="https://elsewhere.example/wiki/Y" title="Y">elsewhere</a></p>
<table><tr class="module-episode-list-row"><th>1</th><td class="summary">"The Fog"</td></tr>
<tr><td class="description">Wren rows into the fog.</td></tr></table>
<table><tr><td><p>A box of figures.</p></td></tr></table>
<div class="mw-heading"><h2>References</h2></div><ul><li>Some book.</li></ul>
</div><footer><a href="https://creativecommons.org/licenses/by-sa/4.0/">licence</a></footer>
</body></html>"""


def test_parser_keeps_headings_terms_and_episodes_and_drops_the_rest() -> None:
    article = parse_article(HTML, "https://en.wikipedia.org/wiki/Lantern_Marsh", "en")
    read = {block.path: block.text for block in article.blocks}
    assert read[()] == "Lantern Marsh is an invented story."
    assert read[("Characters", "Wren Alder")] in (
        "A ferry keeper who keeps the last lamp.",
        "She cannot swim.",
    )
    assert [b.text for b in article.blocks if b.path == ("Characters", "Wren Alder")] == [
        "A ferry keeper who keeps the last lamp.",
        "She cannot swim.",
    ]
    assert read[("Characters", 'Episode 1: "The Fog"')] == "Wren rows into the fog."
    assert not any("figures" in text or "Some book" in text for text in read.values())
    assert [title for title, _text in article.links] == ["Wren Alder", "Lamp (Lantern Marsh)"]
    assert article.languages == {"zh": "https://zh.wikipedia.org/wiki/Lantern"}
    assert article.revision == "42"


@pytest.mark.asyncio
async def test_reader_refuses_other_sites() -> None:
    for url in ("https://elsewhere.example/wiki/Y", "https://en.wikipedia.org/w/api.php"):
        with pytest.raises(SourceRejected):
            await Wikipedia().read(url)


def article(title: str, language: str = "en", **values: Any) -> Article:
    return Article(
        title=title,
        url=f"https://{language}.wikipedia.org/wiki/{title.replace(' ', '_')}",
        language=language,
        licence=LICENCE,
        revision="1",
        **values,
    )


MAIN = article(
    "Lantern Marsh",
    blocks=[
        Block((), "Lantern Marsh is an invented story about a ferry keeper."),
        Block(("Plot",), "Wren Alder rows into the fog to find the missing lamp."),
    ],
    links=[("List of Lantern Marsh characters", "characters")],
    languages={"zh": "https://zh.wikipedia.org/wiki/灯泽"},
)
CAST_PAGE = article(
    "List of Lantern Marsh characters",
    blocks=[
        Block(("Main", "Wren Alder"), "A ferry keeper who keeps the last lamp burning at night."),
        Block(("Main", "Tobin Reed"), "A reed cutter who owes the ferry keeper an old favour."),
    ],
)
CHINESE = article(
    "灯泽",
    "zh",
    blocks=[Block(("故事",), "雷恩在雾中划船寻找失踪的灯。第2章她找到了它。")],
)


class Shelf:
    def __init__(self) -> None:
        self.pages = {a.url: a for a in (MAIN, CAST_PAGE, CHINESE)}

    def address(self, language: str, title: str) -> str:
        return f"https://{language}.wikipedia.org/wiki/{title.replace(' ', '_')}"

    async def read(self, url: str) -> Article:
        if url not in self.pages:
            raise SourceRejected("source_http_404")
        return self.pages[url]


def data_of(prompt: str) -> Any:
    return json.loads(prompt[prompt.rindex("\n") + 1 :])


async def model(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
    name = schema.__name__
    if name == "Picks":
        offered = data_of(prompt)
        wanted = [n for n, text in offered.items() if "Wren" in text or "characters" in text]
        return schema.model_validate({"numbers": [*map(int, wanted), 999]})
    if name == "Translations":
        items = [
            {"number": int(n), "english": "Wren rowed through the fog and found it. Chapter 2."}
            for n in data_of(prompt)
        ]
        return schema.model_validate({"items": items})
    if name == "Sorting":
        numbers = [int(n) for n in data_of(prompt)]
        key = "premise" if '"premise"' in prompt else "overview"
        return schema.model_validate({"sections": [{"key": key, "numbers": numbers}]})
    if name == "SectionDraft":
        first = int(next(iter(data_of(prompt)["sources"])))
        text = "Wren keeps the lamp. Wren can fly."
        return schema.model_validate(
            {
                "paragraphs": [
                    {"text": text, "sources": [first, 500]},
                    {"text": "Nobody knows why.", "sources": [500]},
                ]
            }
        )
    if name == "Doubts":
        assert task == "verification"
        return schema.model_validate({"sentences": [2]})
    if name == "CastDraft":
        numbers = list(data_of(prompt))
        return schema.model_validate(
            {
                "members": [
                    {
                        "number": int(numbers[0]),
                        "name": "Wren Alder",
                        "role": "main",
                        "description": "The ferry keeper.",
                    },
                    {
                        "number": int(numbers[0]),
                        "name": "Invented Person",
                        "role": "main",
                        "description": "Not on the entry.",
                    },
                ]
            }
        )
    raise AssertionError(name)


async def build(kind: Any, subject: str = "") -> Guide:
    return await build_guide(
        kind, "Lantern Marsh", subject, "Lantern Marsh", "", Shelf(), model, model, lambda _m: None
    )


@pytest.mark.asyncio
async def test_summary_has_cited_sections_cast_and_translated_originals() -> None:
    guide = await build("summary")
    premise, story = guide.sections
    assert [p.text for p in premise.paragraphs] == ["Wren keeps the lamp."]
    assert story.paragraphs == []
    assert [m.name for m in guide.cast] == ["Wren Alder"]
    numbers = {s.number for s in guide.sources}
    assert all(set(p.cites) <= numbers for p in premise.paragraphs)
    assert set(guide.cast[0].cites) <= numbers
    assert any(note.startswith("Removed as unsupported: Wren can fly") for note in guide.notes)
    assert any(note.startswith("Left out, no source given") for note in guide.notes)


@pytest.mark.asyncio
async def test_character_guide_reads_only_their_entry() -> None:
    guide = await build("character", "Wren Alder")
    assert guide.title == "Wren Alder · Lantern Marsh"
    assert {s.heading for s in guide.sources} == {"Main / Wren Alder"}
    assert [s.heading for s in guide.sections][0] == "Overview"


@pytest.mark.asyncio
async def test_translation_keeps_the_original_and_drops_cut_replies() -> None:
    passages = [Passage(CHINESE, CHINESE.blocks[0]), Passage(MAIN, MAIN.blocks[0])]
    sources, notes = await translate(passages, [], model, lambda _m: None)
    assert sources[0].original == CHINESE.blocks[0].text
    assert sources[0].text.startswith("Wren rowed")
    assert (sources[1].original, sources[1].number) == ("", 2)
    assert notes == []

    async def cut(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        return schema.model_validate({"items": [{"number": 1, "english": "Wren"}]})

    sources, notes = await translate(passages, [], cut, lambda _m: None)
    assert [s.language for s in sources] == ["en"]
    assert "not fully translated" in notes[0]


@pytest.mark.asyncio
async def test_a_page_that_does_not_name_the_story_is_refused() -> None:
    with pytest.raises(ValueError, match="paste its link"):
        await main_page(Shelf(), "Glass Orchard", "Lantern Marsh", "")


def test_cast_comes_from_one_list_of_characters() -> None:
    passages = [Passage(a, b) for a in (MAIN, CAST_PAGE) for b in a.blocks]
    assert [p.block.path[-1] for p in cast_entries(passages)] == ["Wren Alder", "Tobin Reed"]


@pytest.mark.asyncio
async def test_a_search_naming_no_character_is_unclear() -> None:
    async def vague(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        return schema.model_validate({"kind": "character", "story": "Lantern Marsh"})

    assert (await understand("lantern marsh person", vague)).kind == "unclear"


class Maker:
    def __init__(self) -> None:
        self.calls = 0

    async def make(self, request: GuideRequest, report: Any) -> Guide:
        self.calls += 1
        report("reading")
        if self.calls == 1:
            raise InferenceFailure("all_providers_unavailable")
        return await build("summary")


@pytest.mark.asyncio
async def test_guides_are_approved_built_resumed_and_served(tmp_path: Path) -> None:
    app = create_app(Settings(story_library_path=str(tmp_path)))
    maker = Maker()
    app.state.guides = Guides(tmp_path, maker)
    wanted = {"kind": "summary", "story": "Lantern Marsh", "approved": True}
    local = {"X-Chronicles-Local": "1"}
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        assert (await client.post("/api/guides", json=wanted)).status_code == 403
        refused = await client.post(
            "/api/guides", json={**wanted, "approved": False}, headers=local
        )
        assert refused.status_code == 409
        assert maker.calls == 0
        job = (await client.post("/api/guides", json=wanted, headers=local)).json()
        assert job["key"] == guide_key(GuideRequest.model_validate(wanted))
        await app.state.guides.jobs.tasks[job["key"]]
        stopped = (await client.get(f"/api/guides/{job['key']}")).json()
        assert stopped["job"]["error"] == "all_providers_unavailable"
        assert stopped["guide"] is None
        await client.post(f"/api/guides/{job['key']}/resume", headers=local)
        await app.state.guides.jobs.tasks[job["key"]]
        done = (await client.get(f"/api/guides/{job['key']}")).json()
        assert done["job"]["state"] == "ready"
        assert done["guide"]["title"] == "Lantern Marsh: summary and cast"
        # Asking again opens the saved page without building it twice.
        again = (await client.post("/api/guides", json=wanted, headers=local)).json()
        assert (again["state"], maker.calls) == ("ready", 2)
        listed = (await client.get("/api/guides")).json()["jobs"]
        assert [j["key"] for j in listed] == [job["key"]]
        assert (await client.get("/api/guides/unknown")).status_code == 404
