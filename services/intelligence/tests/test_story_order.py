import json

from src.application.arc_story import GroupReading
from src.application.story_library import LibrarySource, LibraryWorld, library_passages
from src.application.story_order import Placements, order_sources
from src.application.story_pack_builder import _Evidence

HARBOR = [
    "Mira left the harbor to look for her brother in the marsh.",
    "After the tower fell, Mira came back to the harbor and rang the bell.",
    "The whole village answered it and lit the lamps along the quay.",
]
TOWER = [
    "Mira reached the old tower and climbed it while the water rose.",
    "The tower fell into the water as Mira jumped clear of the stairs.",
]


def page(title, position, paragraphs):
    return LibrarySource(
        url=f"https://wiki.example.org/{title}",
        title=title,
        position=position,
        text="\n".join(paragraphs),
    )


def placing(*moved):
    async def infer(prompt, schema, task):
        data = json.loads(prompt[prompt.rindex("\n") + 1 :])
        assert [p["title"] for p in data["outline"]] == ["Harbor", "Tower"]
        assert [p["number"] for p in data["paragraphs"]] == [1, 2, 3, 4, 5]
        return Placements.model_validate({"moved": list(moved)})

    return infer


async def order(*moved):
    sources = [page("Tower", 2, TOWER), page("Harbor", 1, HARBOR)]
    return await order_sources("The Search", sources, placing(*moved))


async def test_a_return_visit_moves_to_the_page_it_happens_after():
    result = await order(
        {"paragraph": 2, "during": 2, "clue": "after the tower  FELL"},
        {"paragraph": 3, "during": 2},
    )
    told = [(p.title, p.position, p.text) for p in result.sources]
    assert told == [
        ("Harbor", 1, HARBOR[0]),
        ("Tower", 2, "\n".join(TOWER)),
        # It now belongs to the later part, so it stays hidden until then.
        ("Harbor", 2, "\n".join(HARBOR[1:])),
    ]
    assert "because it says 'after the tower FELL'" in result.notes[0]
    world = LibraryWorld(
        slug="marsh", title="Marsh", medium="game", arcs=[{"key": "a", "title": "A"}]
    )
    passages = library_passages(world, result.sources, ordered=True)
    assert [s.position for s in passages.sources] == [1, 2, 2]
    assert "lit the lamps" in passages.sentences[-1].text
    # Pieces of one page are still one source.
    assert len({key for key, _ in _Evidence(passages).sources.values()}) == 2


async def test_moves_without_support_leave_page_order():
    result = await order(
        {"paragraph": 2, "during": 2, "clue": "words nobody wrote"},
        # Nothing before it moved, so it cannot be a continuation.
        {"paragraph": 3, "during": 2},
        {"paragraph": 5, "during": 9, "clue": "The tower fell into"},
        # A page's opening is its first visit.
        {"paragraph": 1, "during": 2, "clue": "Mira left the harbor"},
        {"paragraph": 99, "during": 2, "clue": "After the tower fell"},
    )
    assert [p.title for p in result.sources] == ["Harbor", "Tower"]
    assert result.notes == ["5 proposed moves were not supported by the text and were ignored"]


async def test_an_earlier_event_stays_hidden_until_the_page_that_told_it():
    result = await order({"paragraph": 5, "during": 1, "clue": "The tower fell into"})
    # It follows the harbor visit it happened during, ahead of the tower's own opening.
    assert [(p.title, p.position) for p in result.sources] == [("Harbor", 1), ("Tower", 2)]
    assert result.sources[1].text == f"{TOWER[1]}\n{TOWER[0]}"


def test_long_side_lists_do_not_reject_a_reading():
    reading = GroupReading.model_validate(
        {
            "scenes": [{"summary": "Mira searches the whole marsh.", "sentences": [1]}],
            "participants": [f"Person {n}" for n in range(40)],
            "carried_state": "Mira keeps searching.",
            "open_questions": [{"unexpected": "field"}],
        }
    )
    assert len(reading.participants) == 24 and reading.open_questions == []
