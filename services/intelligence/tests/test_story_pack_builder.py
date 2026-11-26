from dataclasses import replace

from src.application.arc_story import GroupReading, StoryOrder
from src.application.story_pack import catalog, entries
from src.application.story_pack_builder import (
    CardBatch,
    CastList,
    LoreDraft,
    PageDraft,
    build_story_pack,
    render_review,
)
from tests.test_arc_story import passage_set, payload


def scripted():
    async def infer(prompt, schema, task):
        data = payload(prompt)
        if schema is GroupReading:
            blocks = [[int(n) for n in b["sentences"]] for b in data["excerpts"]]
            return schema.model_validate(
                {
                    "scenes": [
                        {"summary": f"Scene told by excerpts {b[0]} to {b[-1]}.", "sentences": b}
                        for b in blocks
                    ],
                    "carried_state": "Mira keeps searching.",
                }
            )
        if schema is StoryOrder:
            return schema.model_validate(
                {
                    "beats": [
                        {"summary": f"Event {s['id']} of the search", "scenes": [s["id"]]}
                        for s in data["scenes"]
                    ]
                }
            )
        if schema is CardBatch:
            events = []
            for row in data["beats"]:
                number, shown = row["beat"], [int(n) for n in row["excerpts"]]
                events.append(
                    {
                        "beat": number,
                        "title": f"Part {number} of the search",
                        "summary": f"Mira continues the search for her brother in part {number}.",
                        "characters": ["Mira", "Mira the traveller"],
                        "places": ["Marsh"],
                        "sentences": [shown[0], 999],
                        "causes": [
                            # Supported, uncited, and backwards causes respectively.
                            {"beat": 1, "reason": "The departure led here.", "sentences": [1]},
                            {"beat": 1, "reason": "Nothing cites this.", "sentences": [999]},
                            {"beat": 3, "reason": "A later cause.", "sentences": [1]},
                        ]
                        if number == 2
                        else [],
                    }
                )
            return schema.model_validate({"events": events})
        if schema is CastList:
            return schema.model_validate(
                {
                    "entries": [
                        {
                            "name": "Mira",
                            "kind": "CHARACTER",
                            "same_as": ["Mira the traveller"],
                            "introduction": "A traveller searching for her brother.",
                        },
                        {
                            "name": "Marsh",
                            "kind": "LOCATION",
                            "introduction": "Flooded ground beyond the village.",
                        },
                    ]
                }
            )
        if schema is PageDraft:
            assert data["subject"] == "Mira"
            return schema.model_validate(
                {
                    "introduction": "Mira leaves home to find the brother who vanished.",
                    "sections": [
                        {
                            "name": "Backstory",
                            "statements": [
                                {"text": "Her brother vanished into the marsh.", "sentences": [2]},
                                {"text": "She secretly feared the sea.", "sentences": []},
                            ],
                        }
                    ],
                }
            )
        if schema is LoreDraft:
            return schema.model_validate(
                {
                    "threads": [
                        {
                            "title": "The flooding marsh",
                            "subject": "Marsh",
                            "introduction": "What the account says about the water.",
                            "discoveries": [
                                {
                                    "title": "Spring floods",
                                    "explanation": "The keeper says it floods each spring.",
                                    "classification": "established",
                                    "sentences": [4],
                                }
                            ],
                        },
                        {
                            "title": "Unknown thread",
                            "subject": "Nobody",
                            "introduction": "This has no subject in the cast.",
                            "discoveries": [],
                        },
                    ]
                }
            )
        raise AssertionError(schema)

    return infer


async def test_builder_drafts_a_valid_pack_and_reports_what_to_check():
    passages = passage_set()
    passages = replace(
        passages,
        sources=[replace(s, url=f"https://example.test/{s.position}") for s in passages.sources],
    )
    draft = await build_story_pack(
        slug="marsh-draft",
        world_title="The Marsh (draft)",
        arc_key="search",
        arc_title="The Search",
        medium="manga",
        passages=passages,
        story_bible=None,
        infer=scripted(),
        subjects=["Mira", "Tobin"],
    )
    pack = draft.pack
    arc = pack.arcs[0]
    assert len(arc.events) == 3
    assert [e.chapter for e in arc.events] == [1, 2, 3]
    # Spellings merge into one character; invented sentence numbers never become sources.
    assert [e.name for e in pack.entities if e.type == "CHARACTER"] == ["Mira"]
    assert all(c.quote for e in arc.events for c in e.sources)
    assert [(link.cause, link.effect) for link in arc.links] == [
        (arc.events[0].key, arc.events[1].key)
    ]
    mira = next(e for e in pack.entities if e.name == "Mira")
    assert [s.text for s in mira.sections[0].statements] == ["Her brother vanished into the marsh."]
    assert [t.title for t in pack.lore] == ["The flooding marsh"]
    assert any(arc.events[1].lore) or any(arc.events[0].lore)
    notes = " | ".join(draft.notes)
    assert "dropped uncited text" in notes and "dropped an unsupported cause" in notes
    assert "'Tobin' does not appear" in notes and "Unknown thread" in notes
    review = render_review(draft)
    assert "Led here:" in review and "## Check these" in review
    # The draft is immediately servable.
    assert len(catalog(pack)["journeys"][0]["steps"]) == 3
    assert any(p["display_title"] == "Mira" for p in entries(pack, 1))
