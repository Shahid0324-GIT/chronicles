"""Owned fixtures, not live research or One Piece findings."""

import json
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from src.application.arc_contracts import (
    ArcAccountCoverage,
    ArcAccountDraft,
    ArcContinuousDraft,
    ArcEntailmentBatch,
    ArcOutline,
    ArcParagraph,
    ArcSectionDraft,
    DevelopmentEvidence,
)
from src.application.arc_grounding import CALIBRATION
from src.application.arc_intelligence import ArcIntelligence, article_markdown
from src.application.arc_understanding import review_passages
from src.application.story_scope import ArcResearchScope
from src.domain.entities import GraphNode, GraphRelationship
from src.domain.event_support import event_support_issue
from src.domain.value_objects import NodeType, RelationshipType

from .test_knowledge_presentation import fixture_knowledge, memory_atlas


def arc_fixture():
    universe, continuity, knowledge = fixture_knowledge()
    # Owned source coordinates adapted explicitly; production never converts media.
    for fact in knowledge.facts:
        source = fact["sources"][0]
        source["provenance"]["position_basis"] = "manga-chapter"
        source["passage_id"] = str(uuid4())
        source["quote_end"] = len(source["quote"])
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

    class OwnedEvidence:
        async def development_evidence(self, _universe, _continuity, facts, _boundary):
            return [
                DevelopmentEvidence(
                    id=f["id"],
                    source_id=s["id"],
                    source_hash=s["content_hash"],
                    passage_id=s["passage_id"],
                    passage_hash=s["content_hash"],
                    passage_start=0,
                    start=s["quote_start"],
                    end=s["quote_end"],
                    text=s["quote"],
                    source_group="owned",
                )
                for f in facts
                for s in f["sources"]
            ], []

    return (
        ArcIntelligence(atlas, tx, OwnedEvidence()),
        universe,
        continuity,
        UUID(arc.id),
        knowledge,
        stored,
    )


def holistic_inference(calls, *, gap=False, bad_article=False, invalid_outline=False):
    async def infer(prompt, schema, task):
        calls.append(schema)
        data = json.loads(prompt.split("\n", 1)[1])
        if schema is ArcAccountDraft:
            assert "sections" not in data and data["accepted"]
            return schema.model_validate(
                {
                    "paragraphs": [
                        {"claims": [{"text": "Mira entered the observatory.", "fact_ids": ["1"]}]}
                    ],
                    "gaps": [
                        {
                            "question": "What happened after Mira entered?",
                            "kind": "missing_evidence",
                            "essential": True,
                        }
                    ]
                    if gap
                    else [],
                }
            )
        if schema is ArcEntailmentBatch:
            if "cases" in data:
                return schema.model_validate(
                    {
                        "decisions": [
                            {
                                "index": i,
                                "finding": "entailed" if case["expected"] else "not_established",
                                "reason": "Owned calibration verdict",
                            }
                            for i, case in enumerate(CALIBRATION)
                        ],
                    }
                )
            safe = all("Taro" not in claim["text"] for claim in data["claims"])
            return schema.model_validate(
                {
                    "decisions": [
                        {
                            "index": claim["index"],
                            "finding": "entailed" if safe else "contradicted",
                            "reason": "Owned source check",
                        }
                        for claim in data["claims"]
                    ],
                }
            )
        if schema is ArcAccountCoverage:
            return schema(
                coherent=True,
                complete=not gap,
                search_questions=[
                    "What happened after Mira entered?",
                    "What unsupported question should be queued?",
                ]
                if gap
                else [],
            )
        if schema is ArcOutline:
            assert data == {"1": "Mira entered the observatory."}
            return schema.model_validate(
                {
                    "sections": [
                        {
                            "heading": "Arrival at the observatory",
                            "paragraphs": [2 if invalid_outline else 1],
                        }
                    ]
                }
            )
        if schema is ArcContinuousDraft:
            assert set(data) == {"account", "outline"}
            return schema.model_validate(
                {
                    "sections": [
                        {
                            "heading": "Arrival at the observatory",
                            "paragraphs": [
                                {
                                    "claims": [
                                        {
                                            "text": "Taro reached the observatory."
                                            if bad_article
                                            else "Mira went inside the observatory.",
                                            "fact_ids": ["1"],
                                        }
                                    ]
                                }
                            ],
                        }
                    ]
                }
            )
        if schema is ArcSectionDraft:
            return schema.model_validate(data["section"])
        raise AssertionError(schema)

    return infer


async def test_holistic_document_is_persisted_before_outline_and_article_and_reused():
    service, universe, continuity, arc, _, _ = arc_fixture()
    calls = []
    base = holistic_inference(calls)

    async def observe(prompt, schema, task):
        if schema is ArcOutline:
            before = await service.read(universe, continuity, arc, 7)
            assert before["dossier"]["understanding"]["status"] == "qualified"
            assert before["dossier"]["sections"] == [] and before["article"] is None
        return await base(prompt, schema, task)

    result = await service.rebuild_understanding(universe, continuity, arc, 7, observe, lambda: [])
    assert calls == [
        ArcAccountDraft,
        ArcEntailmentBatch,
        ArcAccountCoverage,
        ArcEntailmentBatch,
        ArcOutline,
        ArcContinuousDraft,
        ArcEntailmentBatch,
        ArcAccountCoverage,
    ]
    assert result["article"]["quality"]["complete"]
    assert "Mira went inside the observatory." in article_markdown(result)
    published = result["article"]["sections"][0]["paragraphs"][0]
    assert published["fact_ids"] == result["dossier"]["understanding"]["paragraphs"][0]["fact_ids"]
    again = await service.rebuild_understanding(universe, continuity, arc, 7, observe, lambda: [])
    assert again == result and len(calls) == 8


async def test_essential_evidence_gap_stops_outline_and_preserves_only_grounded_questions():
    service, universe, continuity, arc, _, _ = arc_fixture()
    calls = []
    result = await service.rebuild_understanding(
        universe, continuity, arc, 7, holistic_inference(calls, gap=True), lambda: []
    )
    assert calls == [ArcAccountDraft, ArcEntailmentBatch, ArcAccountCoverage]
    assert result["article"]["status"] == "withheld"
    assert result["dossier"]["understanding"]["paragraphs"]
    assert service.research_questions(result["dossier"], []) == [
        "What happened after Mira entered?"
    ]
    survey = await service.rebuild_understanding(
        universe, continuity, arc, 7, holistic_inference(calls), lambda: [], survey_only=True
    )
    assert survey["survey"]["questions"] == ["What happened after Mira entered?"]
    assert survey["survey"]["understanding_status"] == "partial"
    assert calls == [ArcAccountDraft, ArcEntailmentBatch, ArcAccountCoverage]


@pytest.mark.parametrize("invalid_outline", [False, True])
async def test_unsupported_article_or_invalid_outline_cannot_publish(invalid_outline):
    service, universe, continuity, arc, _, _ = arc_fixture()
    calls = []
    result = await service.rebuild_understanding(
        universe,
        continuity,
        arc,
        7,
        holistic_inference(calls, bad_article=True, invalid_outline=invalid_outline),
        lambda: [],
    )
    assert (ArcContinuousDraft in calls) is not invalid_outline
    assert result["article"]["status"] == "withheld"
    assert result["article"]["quality"]["validated_sections"] == 0
    assert "Taro" not in article_markdown(result)


async def test_review_repairs_only_missing_verdict_and_preserves_supported_sibling():
    paragraph = ArcParagraph.model_validate(
        {
            "claims": [
                {"text": "Mira entered the observatory.", "fact_ids": ["a"]},
                {"text": "Mira carried a lantern.", "fact_ids": ["b"]},
            ]
        }
    )
    observed = []

    async def infer(prompt, schema, _task):
        rows = json.loads(prompt.split("\n", 1)[1])["claims"]
        observed.append([r["index"] for r in rows])
        return schema.model_validate(
            {
                "decisions": [
                    {
                        "index": rows[0]["index"],
                        "finding": "entailed",
                        "reason": "Owned exact context",
                    }
                ],
            }
        )

    result, withheld, unavailable = await review_passages(
        [paragraph],
        {
            "a": {"assertion": paragraph.claims[0].text},
            "b": {"assertion": paragraph.claims[1].text},
        },
        infer,
    )
    assert result == [paragraph] and withheld == 0 and not unavailable
    assert observed == [[0, 1], [1]]


async def test_later_linked_assertion_changes_full_lore_without_changing_bounded_account():
    service, universe, continuity, arc, knowledge, _ = arc_fixture()
    before = await service.rebuild_understanding(
        universe, continuity, arc, 7, holistic_inference([]), lambda: []
    )
    await service.rebuild_understanding(
        universe, continuity, arc, None, holistic_inference([]), lambda: []
    )
    revealed = GraphNode(
        universe_id=universe,
        continuity_id=continuity,
        type=NodeType.EVENT,
        title="built the observatory",
        summary="Owned test construction",
    )
    link = GraphRelationship(
        universe_id=universe,
        continuity_id=continuity,
        source_node_id=knowledge.nodes[1].id,
        target_node_id=revealed.id,
        relationship_type=RelationshipType.REVEALED,
        description="The arrival revealed the old construction.",
    )
    fact = deepcopy(knowledge.facts[1])
    fact.update(id="later-history", target_id=str(revealed.id))
    fact["sources"][0]["provenance"]["presentation_position"] = 50
    fact["sources"][0]["quote"] = fact["payload"]["description"] = "Taro built the observatory."
    fact["sources"][0]["quote_end"] = len(fact["sources"][0]["quote"])
    link_fact = deepcopy(fact)
    link_fact.update(id="later-explanation", target_id=str(link.id), kind="relationship")
    link_fact["payload"].update(type="REVEALED", description=link.description)
    knowledge.nodes.append(revealed)
    knowledge.edges.append(link)
    knowledge.facts.extend([fact, link_fact])
    assert await service.read(universe, continuity, arc, 7) == before
    assert (await service.read(universe, continuity, arc, None))["status"] == "pending"
    _, _, current = await service.context(universe, continuity, arc, None)
    assert str(revealed.id) in {f["target_id"] for f in current}


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
