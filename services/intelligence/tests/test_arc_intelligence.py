"""Owned fixtures, not live research or One Piece findings."""

import json
from contextlib import asynccontextmanager
from dataclasses import replace
from uuid import UUID

import pytest

from src.application.arc_contracts import ArcPlan, ArcSectionDraft, ArcUnderstanding
from src.application.arc_intelligence import ArcIntelligence, article_markdown
from src.application.encyclopedia_contracts import GroundingAssessment
from src.application.story_scope import ArcResearchScope
from src.domain.entities import GraphNode, GraphRelationship
from src.domain.event_support import event_support_issue
from src.domain.value_objects import NodeType, RelationshipType

from .test_knowledge_presentation import fixture_knowledge, memory_atlas


def arc_fixture():
    universe, continuity, knowledge = fixture_knowledge()
    # Owned source coordinates adapted explicitly; production never converts media.
    for fact in knowledge.facts:
        fact["sources"][0]["provenance"]["position_basis"] = "manga-chapter"
    arc = ArcResearchScope(
        slug="owned-arc",
        title="Owned arc",
        continuity_id=continuity,
        first_position=1,
        last_position=7,
        references=["https://example.org/index"],
    )
    knowledge = replace(knowledge, story_scopes=[arc])
    atlas, _ = memory_atlas(knowledge)
    stored = {}

    class Repo:
        async def get(self, identifier):
            return stored.get(identifier)

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
            stored[identifier] = dict(
                payload=payload,
                knowledge_revision=revision,
                evidence_fingerprint=evidence,
                grounding_status=status,
            )

    @asynccontextmanager
    async def tx():
        yield Repo()

    return ArcIntelligence(atlas, tx), universe, continuity, UUID(arc.id), knowledge, stored


def test_editorial_characterization_is_not_an_event_and_active_roles_cannot_reverse():
    assert event_support_issue({"description": "This moment cements her character as brave."})
    bad = {
        "description": "Mira refuses to eat the food offered by Taro.",
        "event": {
            "trigger": "refuses to eat the food offered by Taro",
            "participant_roles": {"Taro": "actor", "Mira": "recipient"},
        },
    }
    assert event_support_issue(bad) == "active_clause_roles_reversed"
    bad["event"]["participant_roles"] = {"Mira": "actor", "Taro": "recipient"}
    assert event_support_issue(bad) is None


def inference(calls):
    async def infer(prompt, schema, task):
        calls.append(task)
        if schema is ArcPlan:
            return ArcPlan(
                sections=[
                    dict(
                        key="entry",
                        title="Arrival at the observatory",
                        objective="Investigate entry and its missing circumstances",
                        questions=["Why enter?"],
                    )
                ]
            )
        if schema is ArcUnderstanding:
            facts = json.loads(prompt.split("\n", 1)[1])["facts"]
            return ArcUnderstanding(
                bindings=[
                    dict(
                        section_key="entry",
                        facet="action",
                        fact_ids=[f["id"] for f in facts if f.get("type") == "EVENT"],
                    )
                ]
            )
        if schema is ArcSectionDraft:
            facts = json.loads(prompt.split("\n", 1)[1])["facts"]
            return ArcSectionDraft(
                heading="Mira's arrival",
                paragraphs=[dict(text="Mira entered the observatory.", fact_ids=[facts[0]["id"]])],
            )
        if schema is GroundingAssessment:
            return GroundingAssessment(
                entailed=True,
                english=True,
                names_consistent=True,
                agency_and_tense_preserved=True,
                unsupported_relationships=False,
                reason="Owned exact accepted action",
            )
        raise AssertionError(schema)

    return infer


async def test_dossier_survives_jobs_and_unchanged_sections_reuse_without_inference():
    service, universe, continuity, arc, knowledge, _ = arc_fixture()
    calls = []
    result = await service.rebuild(universe, continuity, arc, 7, inference(calls), lambda: [])
    assert result["status"] == "partial"
    dossier = result["dossier"]
    assert dossier["plan_status"] == "provisional_not_canon"
    coverage = dossier["sections"][0]["coverage"]
    assert coverage["research"] == "partial" and "consequence" in coverage["missing_facets"]
    assert not result["article"]["quality"]["complete"]
    first_calls = len(calls)
    again = await service.rebuild(universe, continuity, arc, 7, inference(calls), lambda: [])
    assert again == result and len(calls) == first_calls
    from copy import deepcopy

    duplicate = deepcopy(knowledge.facts[1])
    duplicate["id"] = "rediscovered-claim"
    duplicate["sources"][0]["provenance"]["job_id"] = "later-research-job"
    knowledge.facts.append(duplicate)
    assert (
        await service.rebuild(universe, continuity, arc, 7, inference(calls), lambda: []) == result
    )
    assert len(calls) == first_calls
    assert len(knowledge.nodes) == 2 and len(knowledge.edges) == 1
    assert "https://example.org/owned" in article_markdown(result)


async def test_changed_evidence_invalidates_reads_and_bounded_views_do_not_reuse_full_lore():
    service, universe, continuity, arc, knowledge, _ = arc_fixture()
    await service.rebuild(universe, continuity, arc, None, inference([]), lambda: [])
    bounded = await service.read(universe, continuity, arc, 1)
    assert bounded["dossier"] is None
    knowledge.facts[1]["payload"]["description"] = "Mira entered a different observatory."
    assert (await service.read(universe, continuity, arc, None))["article"] is None


async def test_unknown_fact_cannot_become_dossier_knowledge():
    service, universe, continuity, arc, _, _ = arc_fixture()
    base = inference([])

    async def malicious(prompt, schema, task):
        if schema is ArcUnderstanding:
            return ArcUnderstanding(
                bindings=[
                    dict(section_key="entry", facet="consequence", fact_ids=["invented-fact"])
                ]
            )
        return await base(prompt, schema, task)

    with pytest.raises(ValueError, match="Unlicensed dossier"):
        await service.rebuild(universe, continuity, arc, 7, malicious, lambda: [])


async def test_failed_prose_grounding_preserves_dossier_and_withholds_paragraphs():
    service, universe, continuity, arc, _, _ = arc_fixture()
    base = inference([])

    async def reject(prompt, schema, task):
        if schema is GroundingAssessment:
            return GroundingAssessment(
                entailed=False,
                english=True,
                names_consistent=True,
                agency_and_tense_preserved=True,
                unsupported_relationships=True,
                reason="Invented causal bridge",
            )
        return await base(prompt, schema, task)

    result = await service.rebuild(universe, continuity, arc, 7, reject, lambda: [])
    assert result["dossier"]["sections"][0]["developments"]
    assert result["article"]["sections"][0]["paragraphs"] == []
    assert "Mira entered the observatory." not in article_markdown(result)
    assert result["article"]["status"] == "withheld"
    repaired = await service.rebuild(
        universe, continuity, arc, 7, base, lambda: [], retry_withheld=True
    )
    assert repaired["article"]["quality"]["validated_sections"] == 1


async def test_explicit_source_failure_does_not_extract_unrelated_archive_material():
    from types import SimpleNamespace
    from uuid import uuid4

    from src.application.research import ResearchRequest, SourceInput
    from src.orchestration.research_workflow import ResearchWorkflow

    request = ResearchRequest(
        universe_id=uuid4(),
        continuity_id=uuid4(),
        objective="Investigate an exact historical inscription",
        sources=[
            SourceInput(
                url="https://example.org/history",
                permission_basis="Owned permitted test",
                source_scope="Owned historical test scope",
            )
        ],
    )

    async def check(state):
        return request

    async def snapshot(stage, state):
        return state

    result = await ResearchWorkflow.extractor(
        SimpleNamespace(check=check, snapshot=snapshot),
        {"source_ids": [], "archive_source_ids": [str(uuid4())], "errors": ["source_http_error"]},
    )
    assert result["candidates"] == []


async def test_import_sharing_requires_explicit_current_grant_and_revocation_takes_effect(factory):
    from src.application.source_contracts import SourceRegistration
    from src.infrastructure.persistence.evidence_index import SqlEvidenceIndex
    from src.infrastructure.persistence.models.research import SourceDocumentModel
    from src.infrastructure.persistence.source_registry import SqlSourceRegistry

    from .test_source_intelligence import prepare_index

    scope, ids, _, _ = await prepare_index(factory)
    async with factory() as session, session.begin():
        command = SourceRegistration(
            universe_id=scope.universe_id,
            name="Owned imported account",
            url="https://first.example/import",
            category="reference",
            media=["anime"],
            continuity_ids=[scope.id],
            access_method="import",
            authority="secondary",
            retrieval_policy="permitted",
            permission_basis="Owned explicit cloud test grant",
            attribution="Owned text",
            cloud_content_allowed=True,
            imported_content_cloud_allowed=True,
        )
        row = await SqlSourceRegistry(session).register(command)
        source = await session.get(SourceDocumentModel, ids[0])
        source.public_web = False
        source.provenance = {**source.provenance, "registry_id": str(row.id)}
        metadata = await SqlEvidenceIndex(session).source_metadata(
            scope.universe_id, scope.id, [ids[0]]
        )
        assert metadata[ids[0]]["import_cloud_allowed"]
        assert not metadata[ids[0]]["public_web"]
        await SqlSourceRegistry(session).register(
            command.model_copy(
                update={"cloud_content_allowed": False, "imported_content_cloud_allowed": False}
            )
        )
        metadata = await SqlEvidenceIndex(session).source_metadata(
            scope.universe_id, scope.id, [ids[0]]
        )
        assert not metadata[ids[0]]["import_cloud_allowed"]


@pytest.mark.parametrize(
    "text",
    [
        "Taro entered the observatory.",
        "Mira entered the observatory before Mira opened its gate.",
    ],
)
async def test_model_cannot_approve_uncited_subject_or_temporal_bridge(text):
    service, universe, continuity, arc, _, _ = arc_fixture()
    base = inference([])

    async def invalid_prose(prompt, schema, task):
        if schema is GroundingAssessment:
            raise AssertionError("Deterministic rejection must precede model approval")
        draft = await base(prompt, schema, task)
        if schema is ArcSectionDraft:
            draft.paragraphs[0].text = text
        return draft

    result = await service.rebuild(universe, continuity, arc, 7, invalid_prose, lambda: [])
    assert result["article"]["quality"]["validated_sections"] == 0
    assert result["article"]["sections"][0]["status"] == "withheld"


async def test_later_revelation_enriches_earlier_full_lore_context_but_not_bounded_view():
    from copy import deepcopy

    service, universe, continuity, arc, knowledge, _ = arc_fixture()
    before = await service.rebuild(universe, continuity, arc, 7, inference([]), lambda: [])
    await service.rebuild(universe, continuity, arc, None, inference([]), lambda: [])
    historical = GraphNode(
        universe_id=universe,
        continuity_id=continuity,
        type=NodeType.EVENT,
        title="built the observatory",
        summary="Not evidence",
    )
    revelation = GraphRelationship(
        universe_id=universe,
        continuity_id=continuity,
        source_node_id=knowledge.nodes[1].id,
        target_node_id=historical.id,
        relationship_type=RelationshipType.REVEALED,
        description="The arrival revealed the old construction.",
    )
    fact = deepcopy(knowledge.facts[1])
    fact.update(id="later-history", target_id=str(historical.id))
    fact["payload"]["description"] = "Taro built the observatory before Mira's arrival."
    fact["sources"][0]["provenance"]["presentation_position"] = 50
    fact["sources"][0]["quote"] = fact["payload"]["description"]
    link_fact = deepcopy(fact)
    link_fact.update(id="later-explanation", target_id=str(revelation.id), kind="relationship")
    link_fact["payload"].update(type="REVEALED", description=revelation.description)
    knowledge.nodes.append(historical)
    knowledge.edges.append(revelation)
    knowledge.facts.extend([fact, link_fact])
    assert (await service.read(universe, continuity, arc, 7)) == before
    assert (await service.read(universe, continuity, arc, None))["article"] is None
    _, _, full_facts = await service.context(universe, continuity, arc, None)
    _, _, early_facts = await service.context(universe, continuity, arc, 7)
    assert {str(historical.id), str(revelation.id)} <= {f["target_id"] for f in full_facts}
    assert not {str(historical.id), str(revelation.id)} & {f["target_id"] for f in early_facts}
    after = await service.rebuild(universe, continuity, arc, None, inference([]), lambda: [])
    assert after["article"]["dossier_revision"] != before["article"]["dossier_revision"]
