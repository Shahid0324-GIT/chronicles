import json

import pytest

from src.application.story_cast import CastList, clip, name_cast, same_name

TEXTS = {
    1: "Alice stands trial before the Queen of Hearts in Wonderland.",
    2: "Sora walks through the Olympus Coliseum and meets Phil.",
    3: "The Coliseum is damaged, so Phil postpones the games.",
    4: "Cerberus breaks into the Coliseum while Sora watches.",
    5: "Later Alice vanishes from her cage near a chair.",
}
POSITION = {1: 1, 2: 2, 3: 2, 4: 2, 5: 3}


def mention(name, kind, ids):
    return {"name": name, "kind": kind, "events": [1], "ids": ids, "context": ids}


MENTIONS = {
    "alice": mention("Alice", "CHARACTER", [1]),
    "queen of hearts": mention("Queen of Hearts", "CHARACTER", [1]),
    "coliseum": mention("Coliseum", "LOCATION", [3]),
    "olympus coliseum": mention("Olympus Coliseum", "LOCATION", [2]),
    "chair": mention("chair", "OBJECT", [5]),
    "why she vanished": mention("why she vanished", "MYSTERY", [5]),
}


async def test_the_cast_merges_only_variants_and_cites_each_introduction():
    seen = []

    async def infer(prompt, schema, task):
        data = json.loads(prompt[prompt.rindex("\n") + 1 :])
        own = {s["name"]: s["excerpts"] for s in data["subjects"]}
        seen.append((prompt, data))
        return CastList.model_validate(
            {
                "entries": [
                    {
                        "name": "Alice",
                        "kind": "CHARACTER",
                        "same_as": ["Queen of Hearts"],
                        "introduction": "A girl put on trial in Wonderland.",
                        "sentences": own.get("Alice", []),
                    },
                    {
                        "name": "Queen of Hearts",
                        "kind": "CHARACTER",
                        "introduction": "The ruler who judges the trial.",
                        # Its own sentence and one from a later part of the story.
                        "sentences": [
                            *own.get("Queen of Hearts", []),
                            *(int(n) for n, t in data["excerpts"].items() if "Coliseum" in t),
                        ],
                    },
                    {
                        "name": "Coliseum",
                        "kind": "LOCATION",
                        "same_as": ["Olympus Coliseum"],
                        "introduction": "An arena where games are held.",
                        "sentences": own.get("Coliseum", []),
                    },
                    {"name": "Olympus Coliseum", "kind": "LOCATION"},
                    {"name": "chair", "kind": "OBJECT", "keep": False},
                ]
            }
        )

    cast = await name_cast("Arc", MENTIONS, TEXTS, POSITION, infer)
    assert "why she vanished" not in [s["name"] for s in seen[0][1]["subjects"]]
    # An introduction is shown only where its name first appears.
    shown = seen[0][1]["excerpts"].values()
    assert TEXTS[5] in shown and not any("Cerberus" in t for t in shown if "damaged" in t)
    # Names left without an introduction are asked for once more, and only those.
    assert len(seen) == 2 and seen[1][0].startswith("Each subject below still needs")
    assert [s["name"] for s in seen[1][1]["subjects"]] == ["Queen of Hearts", "Olympus Coliseum"]
    assert cast.alias_of["olympus coliseum"] == cast.alias_of["coliseum"]
    assert cast.alias_of["queen of hearts"] == "queen of hearts"
    assert cast.subjects["alice"]["introduction"] == "A girl put on trial in Wonderland."
    # Nothing cited, so no introduction.
    assert cast.subjects["queen of hearts"]["introduction"] == ""
    assert "chair" not in cast.alias_of
    assert cast.subjects["why she vanished"]["introduction"].startswith("An open question")
    notes = " | ".join(cast.notes)
    assert "Kept 'Queen of Hearts' apart" in notes and "Left out as minor (1): chair" in notes


@pytest.mark.parametrize(
    ("first", "second", "kind", "expected"),
    [
        ("Ines", "Ines Varga", "CHARACTER", True),
        ("Captain Hook", "Hook", "CHARACTER", True),
        ("The Coliseum", "coliseum", "LOCATION", True),
        ("Alice", "Queen of Hearts", "CHARACTER", False),
        ("Keyblade", "Keyblade of Heart", "OBJECT", False),
        ("Traverse Town", "First District", "LOCATION", False),
        ("Captain Hook", "Captain Hook's ship", "LOCATION", False),
    ],
)
def test_only_spellings_of_one_name_merge(first, second, kind, expected):
    assert same_name(first, second, kind) is expected


def test_sentence_numbers_never_stay_in_prose():
    told = clip("Fields stay warm [2]. A crack (1, 4) in row (3).", 100)
    assert told == "Fields stay warm. A crack in row (3)."
