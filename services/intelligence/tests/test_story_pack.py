from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select

from src.application.encyclopedia_contracts import EncyclopediaEntry
from src.application.story_pack import (
    StoryPack,
    catalog,
    continuity_id,
    entries,
    identifier,
    universe_id,
)
from src.infrastructure.persistence.models import NodeModel, UniverseModel
from src.infrastructure.persistence.story_pack_store import SqlStoryPackStore

SOURCE = [{"source": "guide", "quote": "Owned fictional excerpt."}]


def sample(**changes):
    value = {
        "slug": "marsh-draft",
        "title": "The Marsh (draft)",
        "description": "An owned fictional world used only by tests.",
        "medium": "manga",
        "sources": [{"key": "guide", "title": "Owned guide", "url": "https://example.test/guide"}],
        "entities": [
            {
                "key": "mira",
                "type": "CHARACTER",
                "name": "Mira",
                "introduction": "A traveller from the harbor village.",
                "chapter": 1,
                "sources": SOURCE,
                "sections": [
                    {
                        "name": "backstory",
                        "statements": [
                            {
                                "text": "Mira grew up by the harbor.",
                                "chapter": 1,
                                "sources": SOURCE,
                            },
                            {
                                "text": "Mira later kept the lantern.",
                                "chapter": 3,
                                "sources": SOURCE,
                            },
                        ],
                    }
                ],
            },
            {
                "key": "marsh",
                "type": "LOCATION",
                "name": "The Marsh",
                "introduction": "A flooded stretch of land beyond the village.",
                "chapter": 1,
                "sources": SOURCE,
            },
            {
                "key": "lantern",
                "type": "OBJECT",
                "name": "Tobin's Lantern",
                "introduction": "A lantern left on a post at the marsh edge.",
                "chapter": 3,
                "sources": SOURCE,
            },
        ],
        "arcs": [
            {
                "key": "search",
                "title": "The Search",
                "introduction": "Mira looks for her missing brother.",
                "events": [
                    {
                        "key": "departure",
                        "title": "Mira leaves home",
                        "summary": "Mira leaves the harbor village at dawn to search.",
                        "chapter": 1,
                        "characters": ["mira"],
                        "places": ["marsh"],
                        "sources": SOURCE,
                    },
                    {
                        "key": "lantern-found",
                        "title": "The lantern on the post",
                        "summary": "Mira finds her brother's lantern hanging on a post.",
                        "chapter": 3,
                        "characters": ["mira"],
                        "objects": ["lantern"],
                        "lore": ["floods"],
                        "sources": SOURCE,
                    },
                ],
                "links": [
                    {
                        "cause": "departure",
                        "effect": "lantern-found",
                        "kind": "ENABLED",
                        "reason": "Leaving home brought her to the marsh edge.",
                        "sources": SOURCE,
                    }
                ],
            }
        ],
        "lore": [
            {
                "key": "floods",
                "title": "The spring floods",
                "concept": "marsh",
                "introduction": "What is known about the water.",
                "discoveries": [
                    {
                        "key": "keeper-account",
                        "title": "The keeper's account",
                        "explanation": "The keeper says the marsh floods every spring.",
                        "classification": "established",
                        "chapter": 3,
                        "sources": SOURCE,
                    }
                ],
            }
        ],
    }
    value.update(changes)
    return value


def test_pack_rejects_every_broken_reference_together():
    broken = sample()
    broken["arcs"][0]["events"][0]["characters"] = ["marsh"]
    broken["arcs"][0]["links"][0].update(cause="lantern-found", effect="departure")
    broken["lore"][0]["discoveries"][0]["sources"] = [{"source": "missing"}]
    with pytest.raises(ValidationError) as raised:
        StoryPack.model_validate(broken)
    message = str(raised.value)
    assert "marsh is not a known CHARACTER" in message
    assert "runs backwards" in message and "unknown source missing" in message
    with pytest.raises(ValidationError):
        StoryPack.model_validate(sample(slug="one-piece"))  # drafts never take canonical slugs


def test_story_map_shows_causes_cast_and_respects_the_chapter_boundary():
    pack = StoryPack.model_validate(sample())
    full = catalog(pack)
    first, second = full["journeys"][0]["steps"]
    causal = [r for r in full["relations"] if r["type"] == "ENABLED"]
    assert causal[0]["id"] in second["presentation"]["relationshipIds"]
    assert second["loreThreadIds"] == [full["loreThreads"][0]["id"]]
    assert {first["eventNodeId"], second["eventNodeId"]} <= {e["id"] for e in full["entryIndex"]}
    for value in (first["id"], first["eventNodeId"], full["sources"][0]["id"]):
        assert str(UUID(value)) == value

    bounded = catalog(pack, 1)
    assert [s["title"] for s in bounded["journeys"][0]["steps"]] == ["Mira leaves home"]
    assert bounded["loreThreads"] == [] and bounded["discoveries"] == []
    assert "lantern" not in str(bounded).casefold()


def test_entry_pages_match_the_contract_and_hide_later_sections():
    pack = StoryPack.model_validate(sample())
    pages = {p["display_title"]: p for p in entries(pack)}
    for page in pages.values():
        EncyclopediaEntry.model_validate(page)
    mira = pages["Mira"]
    assert [s["name"] for s in mira["sections"]] == ["backstory", "in the story"]
    assert mira["source_references"][0]["quote"] == "Owned fictional excerpt."
    assert mira["connections"]
    early = {p["display_title"]: p for p in entries(pack, 1)}
    assert "Tobin's Lantern" not in early
    assert "lantern" not in str(early["Mira"]).casefold()


async def test_publishing_replaces_only_the_draft_world(factory):
    pack = StoryPack.model_validate(sample())
    async with factory() as session:
        canonical = await session.scalar(select(func.count()).select_from(NodeModel))
    for _ in range(2):
        async with factory() as session, session.begin():
            counts = await SqlStoryPackStore(session).publish(pack)
    assert counts == {"nodes": 5, "relationships": 5}
    async with factory() as session:
        total = await session.scalar(select(func.count()).select_from(NodeModel))
        saved = await SqlStoryPackStore(session).load(
            universe_id(pack.slug), continuity_id(pack.slug)
        )
    assert total == canonical + 5 and saved == pack


async def test_publishing_refuses_a_slug_owned_by_another_world(factory):
    pack = StoryPack.model_validate(sample())
    async with factory() as session, session.begin():
        existing = await session.scalar(select(UniverseModel))
        existing.slug = pack.slug
    with pytest.raises(ValueError, match="not this draft"):
        async with factory() as session, session.begin():
            await SqlStoryPackStore(session).publish(pack)


async def test_story_map_and_entry_endpoints_serve_the_draft(app, factory):
    pack = StoryPack.model_validate(sample())
    async with factory() as session, session.begin():
        await SqlStoryPackStore(session).publish(pack)
    app.state.session_factory = factory
    continuity = str(continuity_id(pack.slug))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        base = f"/api/universes/{pack.slug}"
        story = await client.get(f"{base}/narrative", params={"continuity_id": continuity})
        assert story.status_code == 200
        assert len(story.json()["journeys"][0]["steps"]) == 2
        mira = identifier(pack.slug, "node", "mira")
        entry = await client.get(f"{base}/entries/{mira}", params={"continuity_id": continuity})
        assert entry.status_code == 200 and entry.json()["display_title"] == "Mira"
        unknown = await client.get(
            f"{base}/entries/{uuid4()}", params={"continuity_id": continuity}
        )
        assert unknown.status_code == 404
        graph = await client.get(f"{base}/graph")
        assert graph.status_code == 200
        assert {n["title"] for n in graph.json()["nodes"]} >= {"Mira", "Mira leaves home"}
