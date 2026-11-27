from pathlib import Path

import pytest

from src.application.story_library import library_passages
from src.application.story_pack import StoryPack, catalog
from src.application.story_pack_merge import merge_packs
from src.infrastructure.story_library_files import StoryLibraryFiles
from tests.test_story_pack import sample

SAMPLES = Path(__file__).resolve().parents[3] / "samples"


def test_the_owned_sample_world_reads_in_order_and_cites_exact_text():
    files = StoryLibraryFiles(SAMPLES)
    world = files.world("lantern-marsh")
    pages = files.sources(world, "the-search")
    passages = library_passages(world, list(reversed(pages)))
    assert [s.position for s in passages.sources] == [1, 2]
    assert len(passages.sentences) == 6 and passages.cloud_eligible
    first = passages.sentences[0]
    assert pages[0].text[first.start : first.end] == first.text
    # A copy of a page adds nothing, and one private page keeps the whole arc local.
    private = pages[0].model_copy(update={"cloud_allowed": False, "title": "Z private copy"})
    assert len(library_passages(world, [*pages, private]).sentences) == 6
    assert not library_passages(world, [private]).cloud_eligible
    with pytest.raises(ValueError, match="known arcs"):
        files.sources(world, "missing")
    with pytest.raises(ValueError, match="path separators"):
        files.world("../elsewhere")


def test_a_second_arc_joins_the_world_and_shares_its_cast():
    first = StoryPack.model_validate(sample())
    value = sample()
    # The same traveller under another spelling, with clashing keys everywhere else.
    value["entities"][0].update(key="traveller", name="Mira Vale", aliases=["Mira"])
    value["arcs"][0]["events"][0]["characters"] = ["traveller"]
    value["arcs"][0]["events"][1]["characters"] = ["traveller"]
    value["sources"].append(
        {"key": "second", "title": "Second guide", "url": "https://example.test/second"}
    )
    value["arcs"][0]["events"][1]["sources"] = [{"source": "second", "quote": "Owned."}]
    merged = merge_packs([first, StoryPack.model_validate(value)])
    assert [a.key for a in merged.arcs] == ["search", "search-2"]
    characters = [e for e in merged.entities if e.type == "CHARACTER"]
    assert [(e.key, e.aliases) for e in characters] == [("mira", ["Mira Vale"])]
    assert len(merged.sources) == 2 and len(merged.entities) == 3
    events = [e for arc in merged.arcs for e in arc.events]
    assert len({e.key for e in events}) == 4
    assert all(e.characters == ["mira"] for e in events)
    assert len(catalog(merged)["journeys"]) == 2
    other = StoryPack.model_validate(sample(slug="other-draft"))
    with pytest.raises(ValueError, match="same draft world"):
        merge_packs([first, other])
