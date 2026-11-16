"""Owned fixtures verify reconstruction semantics; these are not One Piece findings."""

from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

from sqlalchemy import select

from src.application.encyclopedia_contracts import GroundingAssessment
from src.application.knowledge_presentation import RecapComposer
from src.application.ports.retrieval import EvidenceHit
from src.application.research import ResearchRequest
from src.application.source_contracts import SourceRegistration
from src.application.story_reconstruction import reference_outline
from src.domain.entities import GraphNode, GraphRelationship
from src.domain.research import digest, passages_for
from src.domain.value_objects import NodeType, RelationshipType
from src.infrastructure.persistence.models import ContinuityModel
from src.infrastructure.persistence.narrative_repository import SqlNarrativeRepository
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.persistence.source_registry import SqlSourceRegistry

from .test_knowledge_presentation import fixture_knowledge, memory_atlas
from .test_relationship_bundles import evidence


def progression():
    universe, continuity, knowledge = fixture_knowledge()
    actor, first = knowledge.nodes
    second = GraphNode(
        universe_id=universe,
        continuity_id=continuity,
        type=NodeType.EVENT,
        title="opened the gate",
        summary="Not evidence",
    )
    participation = GraphRelationship(
        universe_id=universe,
        continuity_id=continuity,
        source_node_id=actor.id,
        target_node_id=second.id,
        relationship_type=RelationshipType.PARTICIPATED_IN,
        description="Mira opened the gate.",
    )
    fact = deepcopy(knowledge.facts[1])
    fact.update(id=str(uuid4()), target_id=str(second.id))
    fact["payload"].update(name="opened the gate", description="Mira opened the gate.")
    fact["sources"][0]["provenance"]["presentation_position"] = 3
    fact["sources"][0]["quote"] = "Mira opened the gate."
    edge_fact = deepcopy(knowledge.facts[2])
    edge_fact.update(id=str(uuid4()), target_id=str(participation.id))
    edge_fact["payload"].update(target_name="opened the gate", description="Mira opened the gate.")
    edge_fact["sources"] = fact["sources"]
    knowledge.nodes.append(second)
    knowledge.edges.append(participation)
    knowledge.facts.extend([fact, edge_fact])
    return universe, continuity, knowledge, first, second


def add_link(knowledge, first, second, kind):
    edge = GraphRelationship(
        universe_id=first.universe_id,
        continuity_id=first.continuity_id,
        source_node_id=first.id,
        target_node_id=second.id,
        relationship_type=kind,
        description="Entry preceded opening."
        if kind == RelationshipType.PRECEDES
        else "Entry caused the gate to open.",
    )
    fact = deepcopy(knowledge.facts[-1])
    fact.update(id=str(uuid4()), target_id=str(edge.id))
    fact["payload"].update(type=kind.value, description=edge.description)
    knowledge.edges.append(edge)
    knowledge.facts.append(fact)


async def test_shared_actor_and_source_order_never_invent_chronology_or_causation():
    universe, continuity, knowledge, first, second = progression()
    atlas, _ = memory_atlas(knowledge)
    catalog = await atlas.catalog(universe, continuity)
    story = catalog["reconstruction"]
    assert story["coverage"]["verifiedSegments"] == 2
    assert story["coverage"]["causallyExplainedTransitions"] == 0
    transition = story["transitions"][0]
    assert transition["sharedParticipantIds"]
    assert transition["narrativeOrder"] == transition["chronology"] == "not_established"
    assert not transition["causality"] and not transition["assertedSequence"]
    assert story["characterThreads"][0]["segmentIds"]
    assert any(g["kind"] == "missing_transition" for g in story["gaps"])
    bounded = (await atlas.catalog(universe, continuity, spoiler_position=1))["reconstruction"]
    assert bounded["coverage"]["verifiedSegments"] == 1 and not bounded["transitions"]
    add_link(knowledge, first, second, RelationshipType.PRECEDES)
    sequence = (await atlas.catalog(universe, continuity))["reconstruction"]["transitions"][0]
    assert sequence["assertedSequence"] and not sequence["causality"]
    add_link(knowledge, first, second, RelationshipType.CAUSED)
    causal = (await atlas.catalog(universe, continuity))["reconstruction"]
    assert causal["coverage"]["causallyExplainedTransitions"] == 1
    assert causal["transitions"][0]["causality"][0]["factIds"]


async def test_multiple_document_support_for_one_canonical_event_does_not_duplicate_segments():
    universe, continuity, knowledge, _, _ = progression()
    corroboration = deepcopy(knowledge.facts[1])
    corroboration["id"] = str(uuid4())
    corroboration["sources"][0].update(id=str(uuid4()), url="https://second-owned.example/story")
    knowledge.facts.append(corroboration)
    atlas, _ = memory_atlas(knowledge)
    story = (await atlas.catalog(universe, continuity))["reconstruction"]
    assert story["coverage"]["verifiedSegments"] == 2
    assert len(story["segments"][0]["sourcePositions"]) == 2


async def test_reference_outline_is_exact_scoped_unverified_and_revocable(factory):
    async with factory() as session, session.begin():
        scope = await session.scalar(select(ContinuityModel))
        text = "The first story concerns Mira's training. The second story concerns Ron's arrival."
        hit = evidence(text)
        config = SourceRegistration(
            universe_id=scope.universe_id,
            continuity_ids=[scope.id],
            name="Owned chapter reference",
            url="https://owned.example/outline",
            category="reference",
            media=["anime"],
            access_method="html",
            authority="secondary",
            retrieval_policy="permitted",
            permission_basis="Owned synthetic research text",
            attribution="Owned fixture",
        )
        entry = await SqlSourceRegistry(session).register(config)
        source = replace(
            hit.source,
            universe_id=scope.universe_id,
            continuity_id=scope.id,
            url=config.url,
            provenance={
                "registry_id": str(entry.id),
                "registry_revision": None,
                "presentation_position": 2,
                "position_basis": "broadcast-presentation",
            },
        )
        passages = passages_for(source)
        await SqlResearchRepository(session).save_source(source, passages)
        outline = reference_outline(
            [EvidenceHit(passages[0], source)], {str(entry.id): entry.model_dump(mode="json")}
        )
        assert len(outline) == 2 and all(
            i["status"] == "reference_description_not_canon" for i in outline
        )
        job = await SqlResearchRepository(session).create_job(
            ResearchRequest(
                universe_id=scope.universe_id,
                continuity_id=scope.id,
                objective="Owned outline research",
            )
        )
        await SqlResearchRepository(session).update_job(
            job, checkpoint={"reconstruction_outline": outline}
        )
    async with factory() as session:
        knowledge = await SqlNarrativeRepository(session).knowledge(scope.universe_id, scope.id)
    assert len(knowledge.reference_outline) == 2
    atlas, _ = memory_atlas(knowledge)
    assert not (await atlas.catalog(scope.universe_id, scope.id, spoiler_position=1))[
        "reconstruction"
    ]["referenceOutline"]
    visible = (await atlas.catalog(scope.universe_id, scope.id, spoiler_position=2))[
        "reconstruction"
    ]
    assert len(visible["referenceOutline"]) == 2
    assert all(not item["verifiedEventIds"] for item in visible["referenceOutline"])
    assert not visible["segments"]
    async with factory() as session, session.begin():
        await SqlSourceRegistry(session).register(
            config.model_copy(update={"retrieval_policy": "navigation-only"})
        )
    async with factory() as session:
        revoked = await SqlNarrativeRepository(session).knowledge(scope.universe_id, scope.id)
    assert not revoked.reference_outline


async def test_archive_navigation_names_do_not_revise_unrelated_reader_entries():
    universe, continuity, knowledge = fixture_knowledge()
    knowledge.facts[0]["sources"][0]["provenance"]["links_json"] = '[{"text":"Taro"}]'
    atlas, _ = memory_atlas(knowledge)
    target = str(knowledge.nodes[0].id)
    before = next(
        r["revision"]
        for r in atlas.resources(await atlas.scope(universe, continuity))
        if r["id"] == target
    )
    extra = GraphNode(
        universe_id=universe,
        continuity_id=continuity,
        type=NodeType.CHARACTER,
        title="Taro",
        summary="Not evidence",
    )
    own = deepcopy(knowledge.facts[0])
    own.update(id=str(uuid4()), target_id=str(extra.id))
    own["payload"].update(name="Taro", description="Taro is an astronomer.")
    own["sources"] = [
        {
            **own["sources"][0],
            "quote": "Taro is an astronomer.",
            "content_hash": digest("Taro is an astronomer."),
        }
    ]
    knowledge.nodes.append(extra)
    knowledge.facts.append(own)
    assert (
        next(
            r["revision"]
            for r in atlas.resources(await atlas.scope(universe, continuity))
            if r["id"] == target
        )
        == before
    )


async def test_arc_dossier_prioritizes_segments_and_exports_only_licensed_references():
    universe, continuity, knowledge, first, second = progression()
    atlas, _ = memory_atlas(knowledge)
    resource = next(
        r for r in atlas.resources(await atlas.scope(universe, continuity)) if r["kind"] == "arc"
    )
    resource["synthesis"] = True
    for _ in range(12):
        extra = deepcopy(resource["facts"][-1])
        extra.update(id=str(uuid4()), target_id=str(uuid4()), kind="relationship")
        extra["payload"]["description"] = "Owned participants connections and outcomes. " * 12
        resource["facts"].append(extra)
    selected = RecapComposer.selected_facts(resource)
    assert {str(first.id), str(second.id)} <= {
        f["target_id"] for f in selected if f["payload"].get("type") == "EVENT"
    }
    references = {str(i + 1): f["id"] for i, f in enumerate(selected)}
    indexed = RecapComposer.indexed_reconstruction(resource, references)
    assert indexed and len(indexed["segments"]) == 2
    assert not indexed["transitions"][0]["causal_fact_refs"]
    assert not indexed["transitions"][0]["sequence_fact_refs"]
    assert all(set(s["fact_refs"]) <= references.keys() for s in indexed["segments"])


async def test_mentioned_people_do_not_become_unresolved_actual_participants():
    universe, continuity, knowledge = fixture_knowledge()
    knowledge.facts[1]["payload"]["event"]["participant_roles"]["Taro"] = "mentioned"
    atlas, _ = memory_atlas(knowledge)
    story = (await atlas.catalog(universe, continuity))["reconstruction"]
    assert "Taro" not in story["segments"][0]["unresolvedParticipantNames"]


async def test_unlicensed_temporal_bridge_is_rejected_before_model_approval():
    import json

    universe, continuity, knowledge, _, _ = progression()
    atlas, _ = memory_atlas(knowledge)
    resource = next(
        r for r in atlas.resources(await atlas.scope(universe, continuity)) if r["kind"] == "arc"
    )
    resource["synthesis"] = True
    calls = []

    async def infer(prompt, schema, task):
        calls.append(task)
        if schema is GroundingAssessment:
            raise AssertionError("A semantic model cannot approve this unlicensed temporal bridge")
        context = json.loads(prompt.split("\n", 1)[1])
        return schema.model_validate(
            {
                "display_title": "The story of Mira",
                "short_summary": "Mira entered the observatory while Mira opened the gate.",
                "statements": [
                    {
                        "text": "Mira entered the observatory.",
                        "fact_ids": [context["facts"][0]["id"]],
                    }
                ],
            }
        )

    payload, status = await RecapComposer().compose(resource, infer)
    assert status == "withheld_order" and payload["grounding_assessment"]["entailed"] is False
    assert calls == ["presentation"]
