"""Configuration and boundary regression fixtures; not discovered One Piece story content."""

from copy import deepcopy

import pytest
from sqlalchemy import func, select

from src.application.event_extraction import EventFrame, immediate_pronoun_context
from src.application.knowledge_presentation import ScopedKnowledge
from src.application.story_scope import ArcResearchScope
from src.infrastructure.persistence.configure_one_piece import (
    MANGA_ID,
    ROMANCE_DAWN,
    UNIVERSE_ID,
    configure,
)
from src.infrastructure.persistence.models import ContinuityModel, NodeModel, RelationshipModel
from src.infrastructure.persistence.research_memory import SqlResearchMemory

from .test_knowledge_presentation import fixture_knowledge, memory_atlas


async def test_configuration_is_idempotent_preserves_graph_and_has_no_story_fixtures(factory):
    async with factory() as session, session.begin():
        before = [
            await session.scalar(select(func.count()).select_from(model))
            for model in [NodeModel, RelationshipModel]
        ]
        await configure(session)
        await configure(session)
        assert before == [
            await session.scalar(select(func.count()).select_from(model))
            for model in [NodeModel, RelationshipModel]
        ]
        continuity = await session.get(ContinuityModel, MANGA_ID)
        assert continuity.medium == "MANGA" and continuity.universe_id == UNIVERSE_ID
        profile = await SqlResearchMemory(session).profile(UNIVERSE_ID)
        assert profile.story_scopes == [ROMANCE_DAWN]
        assert profile.story_scopes[0].last_position == 7


async def test_arc_boundary_does_not_equal_volume_boundary_or_create_events():
    universe, continuity, knowledge = fixture_knowledge()
    arc = ROMANCE_DAWN.model_copy(update={"continuity_id": continuity})
    object.__setattr__(knowledge, "story_scopes", [arc])
    for fact in knowledge.facts:
        fact["sources"][0]["provenance"] = {
            "position_basis": "manga-chapter",
            "presentation_position": 7,
        }
    atlas, _ = memory_atlas(knowledge)
    catalog = await atlas.catalog(universe, continuity, spoiler_position=7)
    assert catalog["journeys"][0]["id"] == arc.id
    assert catalog["journeys"][0]["title"] == "Romance Dawn"
    for fact in knowledge.facts:
        fact["sources"][0]["provenance"]["presentation_position"] = 8
    assert not (await atlas.catalog(universe, continuity, spoiler_position=7))["journeys"]
    assert not (await atlas.catalog(universe, continuity))["journeys"]


def test_unknown_and_mixed_coordinate_systems_fail_closed():
    _, continuity, knowledge = fixture_knowledge()
    second = deepcopy(knowledge.facts[0])
    second["sources"][0]["provenance"]["position_basis"] = "manga-chapter"
    knowledge.facts.append(second)
    assert not ScopedKnowledge.select(knowledge, None, 1, continuity).facts
    with pytest.raises(ValueError):
        ArcResearchScope(**{**ROMANCE_DAWN.model_dump(), "first_position": 8, "last_position": 7})


def test_adjacent_pronoun_context_retained_but_competing_people_not_guessed():
    frame = EventFrame(
        trigger="is tied",
        occurrence_status="actual",
        participants=[{"name": "Mira", "role": "actor"}],
        sentence_ids=[1],
    )
    before = {"id": 0, "passage_id": "one", "text": "Mira appears in the courtyard."}
    anchor = {"id": 1, "passage_id": "one", "text": "She is tied to a post."}
    assert immediate_pronoun_context(
        frame, [before, anchor], [anchor], anchor, ["Mira", "Ron"]
    ) == [before, anchor]
    before["text"] = "Mira meets Ron in the courtyard."
    assert immediate_pronoun_context(
        frame, [before, anchor], [anchor], anchor, ["Mira", "Ron"]
    ) == [anchor]
