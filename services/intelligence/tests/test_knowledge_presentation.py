"""Owned synthetic material and fake inference. These are not research findings."""

import json
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.application.encyclopedia_contracts import GroundingAssessment, PresentationDraft
from src.application.knowledge_presentation import (
    KnowledgeAtlas,
    RecapComposer,
    ScopedKnowledge,
    StoryStructureOrganizer,
)
from src.application.knowledge_types import KnowledgeMetadata
from src.application.ports.narrative import NarrativeKnowledge
from src.domain.entities import GraphNode, GraphRelationship
from src.domain.value_objects import NodeType, RelationshipType


def fixture_knowledge():
    universe, continuity, source = uuid4(), uuid4(), str(uuid4())
    character = GraphNode(
        universe_id=universe,
        continuity_id=continuity,
        type=NodeType.CHARACTER,
        title="Later hidden name",
        summary="Later spoiler",
    )
    event = GraphNode(
        universe_id=universe,
        continuity_id=continuity,
        type=NodeType.EVENT,
        title="入った",
        summary="Raw source",
    )
    edge = GraphRelationship(
        universe_id=universe,
        continuity_id=continuity,
        source_node_id=character.id,
        target_node_id=event.id,
        relationship_type=RelationshipType.PARTICIPATED_IN,
        description="Mira entered.",
    )
    citation = {
        "id": source,
        "url": "https://example.org/owned",
        "title": "Owned fixture",
        "locator": "passage 1; 0:35",
        "provenance": {"presentation_position": 1, "position_basis": "broadcast-presentation"},
        "quote": "Mira entered the observatory.",
        "quote_start": 0,
        "quote_end": 29,
        "content_hash": "owned",
        "passage_id": "one",
    }
    facts = [
        {
            "id": str(uuid4()),
            "target_id": str(character.id),
            "kind": "entity",
            "payload": {
                "name": "Mira",
                "type": "CHARACTER",
                "description": "Mira entered the observatory.",
            },
            "sources": [citation],
        },
        {
            "id": str(uuid4()),
            "target_id": str(event.id),
            "kind": "entity",
            "payload": {
                "name": "entered",
                "type": "EVENT",
                "description": "Mira entered the observatory.",
                "event": {"occurrence_status": "actual", "participant_roles": {"Mira": "actor"}},
            },
            "sources": [citation],
        },
        {
            "id": str(uuid4()),
            "target_id": str(edge.id),
            "kind": "relationship",
            "payload": {
                "source_name": "Mira",
                "target_name": "entered",
                "type": "PARTICIPATED_IN",
                "description": "Mira entered the observatory.",
            },
            "sources": [citation],
        },
    ]
    return universe, continuity, NarrativeKnowledge([character, event], [edge], facts)


def memory_atlas(knowledge):
    saved = {}

    class NarrativeRepo:
        async def knowledge(self, *_):
            return knowledge

        async def save(self, *_):
            pass

    class Presentations:
        async def get(self, identifier):
            return saved.get(identifier)

        async def save(
            self,
            identifier,
            universe,
            continuity,
            resource,
            kind,
            boundary,
            revision,
            evidence,
            language,
            policy,
            payload,
            status,
            provider,
        ):
            saved[identifier] = {
                "knowledge_revision": revision,
                "payload": payload,
                "grounding_status": status,
                "generated_at": "2026-11-13T00:00:00Z",
            }

    @asynccontextmanager
    async def narrative_tx():
        yield NarrativeRepo()

    @asynccontextmanager
    async def presentation_tx():
        yield Presentations()

    return KnowledgeAtlas(narrative_tx, presentation_tx), saved


class FakeInference:
    calls = 0

    async def __call__(self, prompt, schema, task):
        self.calls += 1
        if schema is GroundingAssessment:
            return GroundingAssessment(
                entailed=True,
                english=True,
                names_consistent=True,
                agency_and_tense_preserved=True,
                unsupported_relationships=False,
                reason="Owned fixture is entailed.",
            )
        facts = json.loads(prompt.split("\n", 1)[1])["facts"]
        return PresentationDraft(
            display_title="Mira enters the observatory",
            short_summary="Mira entered the observatory.",
            statements=[{"text": "Mira entered the observatory.", "fact_ids": [facts[0]["id"]]}],
        )


async def test_read_is_inference_free_and_repeated_rebuild_reuses_artifacts():
    universe, continuity, knowledge = fixture_knowledge()
    atlas, saved = memory_atlas(knowledge)
    entries = await atlas.entries(universe, continuity)
    assert all(e["presentation"]["status"] == "unavailable" for e in entries)
    assert all("Later" not in json.dumps(e) for e in entries)
    inference = FakeInference()
    await atlas.rebuild(universe, continuity, inference)
    calls = inference.calls
    before = deepcopy(saved)
    counts = await atlas.rebuild(universe, continuity, inference)
    assert inference.calls == calls and counts["reused"] == len(saved)
    assert saved == before
    catalog = await atlas.catalog(universe, continuity)
    assert catalog["journeys"][0]["steps"][0]["title"] == "Mira enters the observatory"
    assert "入った" not in json.dumps(catalog, ensure_ascii=False)


async def test_character_history_has_only_accepted_participation_and_affected_cache_changes():
    universe, continuity, knowledge = fixture_knowledge()
    atlas, saved = memory_atlas(knowledge)
    scope = await atlas.scope(universe, continuity)
    character = next(r for r in atlas.resources(scope) if r.get("graph_type") == "CHARACTER")
    assert len(character["facts"]) == 3
    inference = FakeInference()
    await atlas.rebuild(universe, continuity, inference)
    before = {r["id"]: r["revision"] for r in atlas.resources(scope)}
    knowledge.facts[0]["payload"]["description"] = "Mira is an observer."
    after = {
        r["id"]: r["revision"] for r in atlas.resources(await atlas.scope(universe, continuity))
    }
    assert before[character["id"]] != after[character["id"]]
    assert all(before[key] == value for key, value in after.items() if key != character["id"])
    entry = next(e for e in await atlas.entries(universe, continuity) if e["id"] == character["id"])
    assert entry["presentation"]["status"] == "unavailable"
    assert len(saved) == 4


def test_spoilers_unknown_positions_nonactual_theories_and_source_allowlist():
    _, _, knowledge = fixture_knowledge()
    assert len(ScopedKnowledge.select(knowledge, None, 1).edges()) == 1
    assert not ScopedKnowledge.select(knowledge, [], None).facts
    for fact in knowledge.facts:
        fact["sources"] = [deepcopy(fact["sources"][0])]
    knowledge.facts[0]["sources"][0]["provenance"]["presentation_position"] = 4
    assert not ScopedKnowledge.select(knowledge, None, 1).edges()
    knowledge.facts[1]["payload"]["event"]["occurrence_status"] = "reported"
    knowledge.facts[2]["payload"]["knowledge"] = {"classification": "FAN_THEORY"}
    assert len(ScopedKnowledge.select(knowledge, None, None).facts) == 1
    knowledge.facts[0]["sources"][0]["provenance"] = {}
    assert not ScopedKnowledge.select(knowledge, None, 1).facts


def test_grouping_requires_same_action_evidence_and_keeps_routes_and_attempts_distinct():
    _, _, knowledge = fixture_knowledge()
    event = knowledge.nodes[1]
    other = replace(event, id=uuid4())
    knowledge.nodes.append(other)
    extra = deepcopy(knowledge.facts[1])
    extra["target_id"] = str(other.id)
    knowledge.facts.append(extra)
    organizer = StoryStructureOrganizer()
    assert len(organizer.groups(ScopedKnowledge.select(knowledge, None, None))) == 1
    extra["payload"]["knowledge"] = {"route_id": "alternative"}
    assert len(organizer.groups(ScopedKnowledge.select(knowledge, None, None))) == 2
    extra["payload"]["knowledge"] = {"attempt_id": "second"}
    assert len(organizer.groups(ScopedKnowledge.select(knowledge, None, None))) == 2
    extra["payload"].pop("knowledge")
    extra["sources"][0]["quote_start"] = 40
    assert len(organizer.groups(ScopedKnowledge.select(knowledge, None, None))) == 2


@pytest.mark.parametrize(
    "title,ids,status",
    [
        ("入った story moment", ["one"], "withheld_language"),
        ("entered", ["one"], "withheld_title"),
        ("Mira Enters the Observatory", ["invented"], "withheld_references"),
    ],
)
async def test_invalid_localization_and_citations_are_withheld_without_semantic_call(
    title, ids, status
):
    calls = 0

    async def infer(*_):
        nonlocal calls
        calls += 1
        return PresentationDraft(
            display_title=title,
            short_summary="Mira entered the observatory.",
            statements=[{"text": "Mira entered the observatory.", "fact_ids": ids}],
        )

    _, _, knowledge = fixture_knowledge()
    resource = {"kind": "milestone", "facts": [{**knowledge.facts[1], "id": "one"}]}
    assert (await RecapComposer().compose(resource, infer))[1] == status
    assert calls == 1


def test_unified_metadata_supports_documents_and_rejects_unknown_classification():
    assert KnowledgeMetadata(category="book", section="contents").category == "book"
    assert (
        KnowledgeMetadata(category="artifact", classification="FAN_THEORY").classification
        == "FAN_THEORY"
    )
    with pytest.raises(ValidationError):
        KnowledgeMetadata(category="book", classification="supported")


async def test_model_approval_cannot_override_unknown_names_or_unsupported_causes():
    universe, continuity, knowledge = fixture_knowledge()
    atlas, _ = memory_atlas(knowledge)
    resource = next(
        r
        for r in atlas.resources(await atlas.scope(universe, continuity))
        if r["kind"] == "milestone"
    )

    class WrongName(FakeInference):
        async def __call__(self, prompt, schema, task):
            result = await super().__call__(prompt, schema, task)
            if isinstance(result, PresentationDraft):
                result.display_title = "Inventedperson enters the observatory"
            return result

    assert (await RecapComposer().compose(resource, WrongName()))[1] == "withheld_names"

    class WrongCause(FakeInference):
        async def __call__(self, prompt, schema, task):
            result = await super().__call__(prompt, schema, task)
            if isinstance(result, PresentationDraft):
                result.short_summary = "Mira entered because she wanted to find a secret."
            return result

    assert (await RecapComposer().compose(resource, WrongCause()))[1] == "withheld_causality"


async def test_identical_evidence_reuses_presentation_across_spoiler_boundaries():
    universe, continuity, knowledge = fixture_knowledge()
    atlas, _ = memory_atlas(knowledge)
    inference = FakeInference()
    await atlas.rebuild(universe, continuity, inference)
    calls = inference.calls
    await atlas.rebuild(universe, continuity, inference, spoiler_position=1)
    assert inference.calls == calls


async def test_theories_need_identified_source_speculation_and_stay_noncanonical():
    universe, continuity, knowledge = fixture_knowledge()
    source = knowledge.facts[0]["sources"][0]
    record = {
        "id": str(uuid4()),
        "classification": "FAN_THEORY",
        "operational_status": "supported",
        "original_statement": "An owned sourced theory.",
        "sources": [{**source, "quote": "A reader suggests an owned theory."}],
    }
    knowledge.interpretations.append(record)
    atlas, _ = memory_atlas(knowledge)
    result = await atlas.interpretations(universe, continuity, spoiler_position=1)
    assert len(result) == 1 and result[0]["canonical"] is False
    record["sources"][0]["quote"] = "All observers agree that the door is open."
    assert not await atlas.interpretations(universe, continuity)


async def test_api_entries_connections_languages_and_rebuild_are_scoped(factory, app):
    from httpx import ASGITransport, AsyncClient

    from .test_event_narrative import accepted_fixture

    _, _, job = await accepted_fixture(factory)
    app.state.session_factory = factory
    params = {"continuity_id": job["continuity_id"]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/universes/re-zero/encyclopedia", params=params)
        assert response.status_code == 200
        entries = response.json()
        assert entries and all(e["presentation"]["status"] == "unavailable" for e in entries)
        path = "/api/universes/re-zero/entries/" + entries[0]["id"]
        assert (await client.get(path, params=params)).json()["id"] == entries[0]["id"]
        assert (await client.get(path, params={**params, "language": "ja"})).status_code == 422
        assert (
            await client.get(path, params={**params, "allowed_source_id": str(uuid4())})
        ).status_code == 404
        queued = await client.post("/api/universes/re-zero/presentations/rebuild", json=params)
        assert queued.status_code == 202
        assert queued.json()["status"] == "queued"


async def test_output_schema_rejects_invented_fact_references_and_wrong_named_subjects():
    universe, continuity, knowledge = fixture_knowledge()
    atlas, _ = memory_atlas(knowledge)
    resource = next(
        r
        for r in atlas.resources(await atlas.scope(universe, continuity))
        if r["kind"] == "milestone"
    )
    schema = RecapComposer.draft_schema(resource, ["1"])
    value = {
        "display_title": "Mira enters the observatory",
        "short_summary": "Mira entered the observatory.",
        "statements": [{"text": "Mira entered the observatory.", "fact_ids": ["2"]}],
    }
    with pytest.raises(ValidationError):
        schema.model_validate(value)
    value["statements"][0]["fact_ids"] = ["1"]
    schema.model_validate(value)
    resource["facts"][0]["payload"]["event"]["participant_roles"] = {"an unnamed visitor": "actor"}
    schema = RecapComposer.draft_schema(resource, ["1"])
    with pytest.raises(ValidationError):
        schema.model_validate(value)


async def test_retrieval_job_provenance_and_duplicate_claim_ids_do_not_invalidate_content():
    universe, continuity, knowledge = fixture_knowledge()
    atlas, _ = memory_atlas(knowledge)
    before = atlas.resources(await atlas.scope(universe, continuity))
    duplicate = deepcopy(knowledge.facts[0])
    duplicate["id"] = str(uuid4())
    duplicate["sources"][0]["provenance"]["job_id"] = str(uuid4())
    knowledge.facts.append(duplicate)
    after = atlas.resources(await atlas.scope(universe, continuity))
    assert {r["id"]: r["revision"] for r in before} == {r["id"]: r["revision"] for r in after}


def test_arc_glosses_remap_fact_references_to_current_input_order():
    resource = {
        "validated_glosses": [
            {
                "display_title": "Second moment",
                "statements": [{"text": "Second statement.", "fact_ids": ["canonical-b"]}],
            },
            {
                "display_title": "First moment",
                "statements": [{"text": "First statement.", "fact_ids": ["canonical-a"]}],
            },
        ]
    }
    result = RecapComposer.indexed_glosses(resource, {"1": "canonical-a", "2": "canonical-b"})
    assert result[0]["display_title"] == "First moment"
    assert result[0]["statements"][0]["fact_ids"] == ["1"]
    assert result[1]["statements"][0]["fact_ids"] == ["2"]


async def test_unbridged_proper_names_use_neutral_fallback_without_inference():
    _, _, knowledge = fixture_knowledge()
    fact = {**knowledge.facts[0], "payload": {**knowledge.facts[0]["payload"], "name": "未知名"}}

    async def forbidden(*_):
        raise AssertionError("Do not invent a romanization")

    result = await RecapComposer().compose(
        {
            "id": fact["target_id"],
            "kind": "entry",
            "graph_type": "CHARACTER",
            "names": [],
            "facts": [fact],
        },
        forbidden,
    )
    assert result == ({}, "withheld_name_localization")


async def test_shared_nodes_keep_the_explicit_requested_continuity_for_organization():
    universe, continuity, knowledge = fixture_knowledge()
    knowledge.nodes[:] = [replace(node, continuity_id=None) for node in knowledge.nodes]
    atlas, _ = memory_atlas(knowledge)
    resources = atlas.resources(await atlas.scope(universe, continuity))
    assert any(resource["kind"] == "arc" for resource in resources)
    assert len(await atlas.entries(universe, continuity)) == 2


async def test_one_malformed_resource_does_not_hide_valid_entries_or_provider_failures():
    from src.application.research_contracts import InferenceFailure

    universe, continuity, knowledge = fixture_knowledge()
    atlas, _ = memory_atlas(knowledge)

    class InvalidFirst(FakeInference):
        first = True

        async def __call__(self, prompt, schema, task):
            if self.first:
                self.first = False
                raise InferenceFailure("structured_output_exhausted")
            return await super().__call__(prompt, schema, task)

    counts = await atlas.rebuild(universe, continuity, InvalidFirst())
    assert counts["partial"] and counts["generated"] >= 1
    other, _ = memory_atlas(knowledge)

    async def offline(*_):
        raise InferenceFailure("provider_unavailable")

    with pytest.raises(InferenceFailure, match="provider_unavailable"):
        await other.rebuild(universe, continuity, offline)


def test_established_short_name_survives_scoped_schema_and_shared_contract():
    schema = RecapComposer.draft_schema(
        {
            "id": "person",
            "kind": "entry",
            "graph_type": "CHARACTER",
            "names": [{"id": "person", "english": "Mira"}],
            "facts": [],
        },
        ["1"],
    )
    value = schema.model_validate(
        {
            "display_title": "Mira",
            "short_summary": "Mira entered the observatory.",
            "statements": [{"text": "Mira entered the observatory.", "fact_ids": ["1"]}],
        }
    )
    assert PresentationDraft.model_validate(value.model_dump(mode="json")).display_title == "Mira"


async def test_arc_assembles_current_grounded_sentences_without_new_inference():
    universe, continuity, knowledge = fixture_knowledge()
    atlas, _ = memory_atlas(knowledge)
    inference = FakeInference()
    await atlas.rebuild(universe, continuity, inference)
    before = inference.calls
    catalog = await atlas.catalog(universe, continuity)
    journey = catalog["journeys"][0]
    assert journey["overview"] == "Mira entered the observatory."
    assert journey["presentation"]["assembly"]["method"] == "deterministic-grounded-milestones"
    assert journey["presentation"]["assembly"]["source_artifact_ids"]
    await atlas.rebuild(universe, continuity, inference)
    assert inference.calls == before
