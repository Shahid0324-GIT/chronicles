"""Owned synthetic event evidence and publication fixtures, never live research."""

from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.application.event_extraction import EventFrames, evidence_units, extract_events
from src.application.narrative import NarrativeBuilder
from src.domain.research import SourcePassage, digest
from src.infrastructure.persistence.models.research import SourceDocumentModel
from src.infrastructure.research_runtime import narrative_transactions

from .test_knowledge import prepared

TEXT = "Mira Vale entered the observatory. The arrival happened at the observatory."


def passage(text=TEXT):
    return SourcePassage(uuid4(), uuid4(), 0, 0, len(text), text, digest(text))


async def test_event_frame_materializes_evidenced_endpoints_and_typed_edges():
    p = passage()

    async def infer(prompt, schema):
        return EventFrames.model_validate(
            {
                "events": [
                    {
                        "trigger": "entered",
                        "occurrence_status": "actual",
                        "participants": [{"name": "Mira Vale", "role": "actor"}],
                        "location": "observatory",
                        "sentence_ids": [0],
                    }
                ]
            }
        )

    result = await extract_events([p], "Research the explicitly described arrival", infer)
    assert {e.type.value for e in result.entities} == {"EVENT", "CHARACTER", "LOCATION"}
    assert {e.type.value for e in result.relationships} == {"PARTICIPATED_IN", "OCCURRED_AT"}
    assert all(e.evidence[0].quote == "Mira Vale entered the observatory." for e in result.entities)
    event = next(e for e in result.entities if e.type.value == "EVENT")
    assert event.event["identity_anchor"]
    repeated = await extract_events([p], "Research again", infer)
    assert repeated.entities[0].event["identity_anchor"] == event.event["identity_anchor"]


async def test_missing_trigger_or_sentence_does_not_manufacture_event_evidence():
    async def infer(prompt, schema):
        return EventFrames.model_validate(
            {
                "events": [
                    {
                        "trigger": "invented action",
                        "occurrence_status": "actual",
                        "sentence_ids": [0],
                    }
                ]
            }
        )

    assert not (await extract_events([passage()], "Research supplied material", infer)).entities


def test_long_sentence_units_preserve_exact_passage_offsets():
    p = passage("Long owned synthetic text " * 45)
    units = evidence_units([p])
    assert units and all(len(u["text"]) <= 400 for u in units)
    assert all(p.text[u["start"] : u["start"] + len(u["text"])] == u["text"] for u in units)


async def test_intended_outcome_is_not_an_event_and_beneficiary_is_not_a_participant():
    p = passage("Mira runs to save Corin from a future danger.")

    async def intended(prompt, schema):
        return EventFrames.model_validate(
            {
                "events": [
                    {
                        "trigger": "save Corin",
                        "occurrence_status": "intended",
                        "sentence_ids": [0],
                    }
                ]
            }
        )

    intended_result = await extract_events([p], "Research actual occurrences", intended)
    assert intended_result.entities[0].event["occurrence_status"] == "intended"
    assert not intended_result.relationships

    async def actual(prompt, schema):
        return EventFrames.model_validate(
            {
                "events": [
                    {
                        "trigger": "runs",
                        "occurrence_status": "actual",
                        "sentence_ids": [0],
                        "participants": [
                            {"name": "Mira", "role": "actor"},
                            {"name": "Corin", "role": "mentioned"},
                        ],
                    }
                ]
            }
        )

    result = await extract_events([p], "Research actual occurrences", actual)
    assert {r.source_name for r in result.relationships} == {"Mira"}


async def test_publication_rejects_intended_event_even_with_supported_assessment(factory):
    from uuid import UUID

    from src.infrastructure.persistence.models.research import ResearchClaimModel

    job, service, _, claims, resolutions = await prepared(factory)
    event = next(c for c in claims if c["payload"].get("type") == "EVENT")
    async with factory() as session, session.begin():
        row = await session.get(ResearchClaimModel, UUID(event["id"]))
        row.payload = {**row.payload, "event": {"occurrence_status": "intended"}}
    result = await service.publish(job, resolutions, {}, False)
    assert len(result["promoted"]) == 1
    assert len(result["unresolved"]) == 2


async def accepted_fixture(factory):
    job, service, tx, claims, resolutions = await prepared(factory)
    await service.publish(job, resolutions, {}, False)
    async with tx() as u:
        saved = await u.archive.get_job(job)
    async with factory() as session, session.begin():
        for s in await session.scalars(select(SourceDocumentModel)):
            s.provenance = {"presentation_position": 1, "position_basis": "broadcast-presentation"}
    return job, service, saved


async def test_narrative_from_accepted_graph_is_stable_scoped_and_reversible(factory):
    job, service, saved = await accepted_fixture(factory)
    from uuid import UUID

    universe, continuity = UUID(saved["universe_id"]), UUID(saved["continuity_id"])
    builder = NarrativeBuilder(narrative_transactions(factory))
    first = await builder.build(universe, continuity, spoiler_position=1)
    assert len(first["journeys"]) == 1
    step = first["journeys"][0]["steps"][0]
    assert step["participantIds"] and step["presentation"]["relationshipIds"]
    assert first == await builder.build(universe, continuity, spoiler_position=1)
    assert not (await builder.build(universe, continuity, allowed_sources=[]))["journeys"]
    await service.rollback_job(job, "Owned synthetic correction of all publications")
    assert not (await builder.build(universe, continuity))["journeys"]


async def test_unknown_presentation_order_stays_partial_instead_of_inventing_steps(factory):
    job, service, tx, _, resolutions = await prepared(factory)
    await service.publish(job, resolutions, {}, False)
    async with tx() as u:
        saved = await u.archive.get_job(job)
    from uuid import UUID

    result = await NarrativeBuilder(narrative_transactions(factory)).build(
        UUID(saved["universe_id"]), UUID(saved["continuity_id"])
    )
    assert not result["journeys"] and result["unorderedMilestones"] and result["partial"]
    assert result["orderingGaps"]


async def test_spoiler_boundary_excludes_unpositioned_documents(factory):
    job, service, tx, _, resolutions = await prepared(factory)
    await service.publish(job, resolutions, {}, False)
    async with tx() as u:
        saved = await u.archive.get_job(job)
    from uuid import UUID

    result = await NarrativeBuilder(narrative_transactions(factory)).build(
        UUID(saved["universe_id"]), UUID(saved["continuity_id"]), spoiler_position=1
    )
    assert not result["journeys"] and not result["unorderedMilestones"] and not result["sources"]


async def test_narrative_api_keeps_existing_catalog_shape(factory, app):
    _, _, saved = await accepted_fixture(factory)
    app.state.session_factory = factory
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/universes/re-zero/narrative", params={"continuity_id": saved["continuity_id"]}
        )
        assert response.status_code == 200
        catalog = response.json()
        assert catalog["schemaVersion"] == 1
        assert all(k in catalog for k in ["journeys", "loreThreads", "discoveries", "sources"])


async def test_ambiguous_episode_keeps_representative_and_explicit_gap(factory):
    from contextlib import asynccontextmanager
    from dataclasses import replace
    from uuid import UUID

    from src.application.ports.narrative import NarrativeKnowledge
    from src.domain.value_objects import NodeType

    _, _, saved = await accepted_fixture(factory)
    universe, continuity = UUID(saved["universe_id"]), UUID(saved["continuity_id"])
    async with narrative_transactions(factory)() as repo:
        knowledge = await repo.knowledge(universe, continuity)
    event = next(
        n
        for n in knowledge.nodes
        if n.type == NodeType.EVENT and any(f["target_id"] == str(n.id) for f in knowledge.facts)
    )
    fact = next(f for f in knowledge.facts if f["target_id"] == str(event.id))
    others = [replace(event, id=uuid4()) for _ in range(2)]
    extra = [
        {
            **fact,
            "target_id": str(n.id),
            "sources": [
                {**s, "provenance": {**s["provenance"], "presentation_position": position}}
                for s in fact["sources"]
            ],
        }
        for n, position in zip(others, [1, 2], strict=True)
    ]

    class Memory:
        calls = 0

        async def knowledge(self, *_):
            type(self).calls += 1
            facts = knowledge.facts + extra
            return NarrativeKnowledge(
                knowledge.nodes + others,
                knowledge.edges,
                list(reversed(facts)) if self.calls % 2 else facts,
            )

        async def save(self, *_):
            pass

    @asynccontextmanager
    async def tx():
        yield Memory()

    builder = NarrativeBuilder(tx)
    catalog = await builder.build(universe, continuity)
    assert len(catalog["journeys"][0]["steps"]) == 2
    assert len(catalog["unorderedMilestones"]) == 1 and catalog["partial"]
    assert catalog["orderingGaps"][0]["kind"] == "ambiguous-within-episode-order"
    assert catalog["journeys"][0]["steps"][0]["episodeLabel"] == "By episode 1"
    assert catalog == await builder.build(universe, continuity)
    assert all(s["locator"].count("passage ") == 1 for s in catalog["sources"])


async def test_lore_projection_uses_allowed_assertion_instead_of_later_summary(factory):
    from contextlib import asynccontextmanager
    from dataclasses import replace
    from uuid import UUID

    from src.application.ports.narrative import NarrativeKnowledge

    _, _, saved = await accepted_fixture(factory)
    universe, continuity = UUID(saved["universe_id"]), UUID(saved["continuity_id"])
    async with narrative_transactions(factory)() as repo:
        knowledge = await repo.knowledge(universe, continuity)
    fact = next(f for f in knowledge.facts if f["kind"] == "entity")
    node = next(n for n in knowledge.nodes if str(n.id) == fact["target_id"])
    from src.domain.value_objects import NodeType

    lore = replace(node, type=NodeType.LORE, title="Later secret title", summary="Later spoiler")

    class Memory:
        async def knowledge(self, *_):
            return NarrativeKnowledge([lore], [], [fact])

        async def save(self, *_):
            pass

    @asynccontextmanager
    async def tx():
        yield Memory()

    catalog = await NarrativeBuilder(tx).build(universe, continuity, spoiler_position=1)
    thread = catalog["loreThreads"][0]
    assert thread["title"] == fact["payload"]["name"]
    assert thread["introduction"] == fact["payload"]["description"]
    assert "Later spoiler" not in str(catalog) and "Later secret title" not in str(catalog)
