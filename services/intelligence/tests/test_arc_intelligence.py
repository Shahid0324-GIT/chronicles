"""Owned fixtures, not live research or One Piece findings."""

import json
from contextlib import asynccontextmanager
from dataclasses import replace
from uuid import UUID

import pytest

from src.application.arc_contracts import (
    ArcDossier,
    ArcPlan,
    ArcSectionDraft,
    ArcSemanticReview,
    ArcUnderstanding,
)
from src.application.arc_grounding import CALIBRATION
from src.application.arc_intelligence import ArcIntelligence, article_markdown
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
                        fact_ids=[
                            f["id"]
                            for f in facts
                            if f["statement"] == "Mira entered the observatory."
                        ],
                    )
                ]
                + [
                    dict(section_key="entry", facet="retrospective", fact_ids=[f["id"]])
                    for f in facts
                    if f["statement"] != "Mira entered the observatory."
                ]
            )
        if schema is ArcSectionDraft:
            facts = json.loads(prompt.split("\n", 1)[1])["facts"]
            facts = [f for f in facts if f["statement"] == "Mira entered the observatory."]
            return ArcSectionDraft(
                heading="Mira's arrival",
                paragraphs=[
                    dict(
                        text="Mira entered the observatory.",
                        fact_ids=[facts[0]["id"]],
                        claims=[
                            dict(text="Mira entered the observatory.", fact_ids=[facts[0]["id"]])
                        ],
                    )
                ],
            )
        if schema is ArcSemanticReview:
            context = json.loads(prompt.split("\n", 1)[1])
            if "cases" in context:
                verdicts = [
                    dict(
                        index=i,
                        verdict="supported" if c["expected"] else "unsupported",
                        reason="Owned calibration truth",
                    )
                    for i, c in enumerate(CALIBRATION)
                ]
            else:
                verdicts = [
                    dict(index=c["index"], verdict="supported", reason="Owned supported assertion")
                    for c in context["claims"]
                ]
            return ArcSemanticReview(claims=verdicts, paragraphs_faithful=True, coherent=True)
        raise AssertionError(schema)

    return infer


async def test_arc_survey_requires_no_development_plan_and_excludes_future_sections():
    service, universe, continuity, arc, _, _ = arc_fixture()
    calls = []

    async def plan(prompt, schema, task):
        calls.append(task)
        assert schema is ArcPlan
        assert "Mira entered the observatory." in prompt
        return ArcPlan.model_validate(
            {
                "sections": [
                    {
                        "key": "entry",
                        "title": "Arrival at the observatory",
                        "objective": "Investigate entry and its missing circumstances",
                        "first_position": 1,
                        "questions": ["Why enter?"],
                    },
                    {
                        "key": "later",
                        "title": "After the visit",
                        "objective": "Investigate what happened after the visit",
                        "first_position": 6,
                        "questions": ["Where did she go?"],
                    },
                ]
            }
        )

    kwargs = dict(compose=False, survey_only=True)
    result = await service.rebuild(universe, continuity, arc, 5, plan, lambda: [], **kwargs)
    assert result["survey"]["source_range"] == [1, 5]
    assert [s["key"] for s in result["survey"]["sections"]] == ["entry"]
    assert result["survey"]["questions"] == ["Owned arc / Arrival at the observatory — Why enter?"]
    assert (
        await service.rebuild(universe, continuity, arc, 5, plan, lambda: [], **kwargs)
    ) == result
    assert calls == ["planning"]
    assert (await service.read(universe, continuity, arc, 5))["status"] == "pending"


async def test_arc_scope_assignment_accounts_for_ids_and_preserves_existing_scope_on_error():
    service, universe, continuity, arc, _, _ = arc_fixture()
    result = await service.rebuild(universe, continuity, arc, 7, inference([]), lambda: [])
    dossier = ArcDossier.model_validate(result["dossier"])

    async def assign(_, schema, task):
        assert schema is ArcUnderstanding and task == "relationship_analysis"
        return ArcUnderstanding.model_validate(
            {
                "bindings": [{"section_key": "entry", "facet": "action", "fact_ids": ["1"]}],
                "omissions": [
                    {
                        "fact_ids": [str(i) for i in range(2, len(dossier.accepted_facts) + 1)],
                        "reason": "duplicate",
                        "explanation": "The same assertion appears more than once.",
                    }
                ],
            }
        )

    await service.assign_accepted_scope(dossier, assign)
    assert dossier.sections[0].accepted_scope_ids == [dossier.accepted_facts[0]["id"]]

    async def incomplete(*_):
        return ArcUnderstanding(bindings=[])

    with pytest.raises(ValueError, match="Every input assertion"):
        await service.assign_accepted_scope(dossier, incomplete)
    assert dossier.sections[0].accepted_scope_ids == [dossier.accepted_facts[0]["id"]]


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


async def test_prose_policy_change_reuses_unchanged_organization(monkeypatch):
    from src.application import arc_intelligence

    service, universe, continuity, arc, _, _ = arc_fixture()
    await service.rebuild(universe, continuity, arc, 7, inference([]), lambda: [])
    monkeypatch.setattr(arc_intelligence, "POLICY", "owned-prose-policy-revision")
    calls = []
    result = await service.rebuild(universe, continuity, arc, 7, inference(calls), lambda: [])
    assert "planning" not in calls and "relationship_analysis" not in calls
    assert "presentation" in calls and result["article"]["quality"]["validated_sections"] == 1


async def test_focused_rebuild_preserves_other_unchanged_validated_sections():
    service, universe, continuity, arc, _, _ = arc_fixture()
    calls = []
    base = inference(calls)

    async def two_sections(prompt, schema, task):
        result = await base(prompt, schema, task)
        if schema is ArcPlan:
            result.sections.append(
                result.sections[0].model_copy(
                    update={
                        "key": "aftermath",
                        "title": "The same supported context",
                    }
                )
            )
        if schema is ArcUnderstanding:
            data = json.loads(prompt.split("\n", 1)[1])
            if not data["requested_section_keys"]:
                result.bindings.append(
                    result.bindings[0].model_copy(
                        update={
                            "section_key": "aftermath",
                        }
                    )
                )
        return result

    first = await service.rebuild(universe, continuity, arc, 7, two_sections, lambda: [])
    assert len(first["article"]["sections"]) == 2
    before = len(calls)
    second = await service.rebuild(
        universe, continuity, arc, 7, two_sections, lambda: [], section_keys=["entry"]
    )
    assert second["article"]["sections"] == first["article"]["sections"]
    assert calls[before:] == ["relationship_analysis"]
    assert all(c["presentation"] == "validated" for c in second["article"]["coverage"])
    assert "https://example.org/owned" in article_markdown(second)


async def test_changed_evidence_invalidates_reads_and_bounded_views_do_not_reuse_full_lore():
    service, universe, continuity, arc, knowledge, _ = arc_fixture()
    await service.rebuild(universe, continuity, arc, None, inference([]), lambda: [])
    bounded = await service.read(universe, continuity, arc, 1)
    assert bounded["dossier"] is None
    knowledge.facts[1]["payload"]["description"] = "Mira entered a different observatory."
    assert (await service.read(universe, continuity, arc, None))["article"] is None


async def test_source_bounded_composition_reuses_only_provisional_plan_and_never_broader_prose():
    service, universe, continuity, arc, knowledge, _ = arc_fixture()
    await service.rebuild(universe, continuity, arc, 7, inference([]), lambda: [])
    source = UUID(knowledge.facts[0]["sources"][0]["id"])
    calls = []
    result = await service.rebuild(
        universe, continuity, arc, 7, inference(calls), lambda: [], allowed_sources=[source]
    )
    assert "planning" not in calls
    assert "presentation" in calls
    assert result["article"]["quality"]["validated_sections"] == 1
    empty = await service.rebuild(
        universe, continuity, arc, 7, inference([]), lambda: [], allowed_sources=[]
    )
    assert empty["dossier"]["accepted_facts"] == []
    assert not empty["article"]["sections"]
    assert (await service.read(universe, continuity, arc, 7))["article"]["sections"]


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
        if schema is ArcSemanticReview and '"cases"' not in prompt:
            return ArcSemanticReview(
                claims=[dict(index=0, verdict="unsupported", reason="Invented causal bridge")],
                paragraphs_faithful=False,
                coherent=True,
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


async def test_editorial_feedback_gets_one_revision_and_a_fresh_review():
    service, universe, continuity, arc, _, _ = arc_fixture()
    base = inference([])
    reviews = 0
    drafts = 0

    async def revise(prompt, schema, task):
        nonlocal reviews, drafts
        if schema is ArcSectionDraft:
            drafts += 1
            if drafts == 2:
                assert '"review"' in prompt and "Disconnected presentation" in prompt
        result = await base(prompt, schema, task)
        if schema is ArcSemanticReview and '"cases"' not in prompt:
            reviews += 1
            if reviews == 1:
                result.coherent = False
                result.coherence_issues = ["Disconnected presentation"]
        return result

    result = await service.rebuild(universe, continuity, arc, 7, revise, lambda: [])
    section = result["article"]["sections"][0]
    assert section["status"] == "validated" and drafts == reviews == 2
    assert len(section["assessment"]["review_attempts"]) == 2
    assert not section["assessment"]["review_attempts"][0]["coherent"]


async def test_partial_claim_projection_requires_fresh_review_and_retains_rejection_audit():
    service, universe, continuity, arc, _, _ = arc_fixture()
    base = inference([])
    reviews = 0

    async def partial(prompt, schema, task):
        nonlocal reviews
        result = await base(prompt, schema, task)
        if schema is ArcSectionDraft:
            claim = result.paragraphs[0].claims[0]
            result.paragraphs[0].claims.append(
                claim.model_copy(update={"text": "Mira stole treasure."})
            )
        if schema is ArcSemanticReview and '"cases"' not in prompt:
            reviews += 1
            if reviews < 3:
                result.claims[1].verdict = "unsupported"
                result.claims[1].reason = "No theft is present in the accepted assertion"
            else:
                assert len(result.claims) == 1
        return result

    result = await service.rebuild(universe, continuity, arc, 7, partial, lambda: [])
    section = result["article"]["sections"][0]
    assert section["status"] == "validated" and reviews == 3
    assert section["paragraphs"][0]["text"] == "Mira entered the observatory."
    assert len(section["assessment"]["review_attempts"]) == 3
    assert section["assessment"]["partial_projection"]["removed_claims"][0]["index"] == 1


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
        if schema is ArcSemanticReview and '"cases"' not in prompt:
            return ArcSemanticReview(
                claims=[dict(index=0, verdict="unsupported", reason="Unsupported subject")],
                paragraphs_faithful=False,
                coherent=True,
            )
        draft = await base(prompt, schema, task)
        if schema is ArcSectionDraft:
            draft.paragraphs[0].claims[0].text = text
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
