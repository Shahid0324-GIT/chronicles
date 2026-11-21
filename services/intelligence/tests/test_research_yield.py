"""Owned regression text and fake inference only; never live research evidence."""

from dataclasses import replace
from uuid import uuid4, uuid5

from sqlalchemy import select

from src.application.atomic_verification import assess_atomic_batch, candidate_assessment
from src.application.connected_extraction import (
    candidate_rows,
    compile_connected,
    corroborate_candidates,
    repair_connected,
)
from src.application.event_extraction import evidence_units
from src.application.evidence_bundles import EvidenceBundleBuilder, connection_score
from src.application.identity import IdentityResolver
from src.application.inference import InferenceRouter
from src.application.knowledge_contracts import ContextIdentityReview
from src.application.relationship_contracts import ConnectedAssertions
from src.application.research import ResearchRequest
from src.application.research_contracts import InferenceResult, InferenceUsage
from src.application.research_frontier import ResearchFrontierService
from src.application.research_policy import ResearchLead, ResearchPolicy, UniverseResearchProfile
from src.application.retrieval import EvidenceRetrieval
from src.application.source_intelligence import SourceSelector
from src.domain.atomic_evidence import atomic_payload_support, atomic_support
from src.domain.entities import now
from src.domain.knowledge import short_name_bridge
from src.domain.research import SourceDocument, digest, passages_for
from src.infrastructure.config.settings import Settings
from src.infrastructure.persistence.models.research import SourceDocumentModel
from src.infrastructure.persistence.research_memory import SqlResearchMemory
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.research_runtime import build_workflow, index_transactions

from .test_adaptive_research import entry
from .test_relationship_bundles import SUBJECTS, evidence
from .test_relationship_workflow import OwnedProvider, prepare
from .test_source_intelligence import FakeEmbeddings


def test_middle_initial_is_not_a_sentence_boundary_and_short_names_need_explicit_context():
    hit = evidence("Mira D. Vale saves Ron. Mira gives Ron a map.")
    units = evidence_units([hit.passage])
    assert [u["text"] for u in units] == ["Mira D. Vale saves Ron.", "Mira gives Ron a map."]
    assert all(
        hit.passage.text[u["start"] : u["start"] + len(u["text"])] == u["text"] for u in units
    )
    assert short_name_bridge("Mira", "Mira D. Vale", [hit.passage.text])
    assert not short_name_bridge("Mira", "Mira D. Vale", ["Mira D. Vale saves Ron."])
    assert not short_name_bridge("D", "Mira D. Vale", [hit.passage.text])


def test_present_tense_and_coordinated_rescue_still_reject_negation_and_reversed_roles():
    atom = {"subject": "Mira", "predicate": "saves", "object": "Ron"}
    assert atomic_support(atom, ["Mira saves Ron from the river."]).supported
    assert atomic_support(atom, ["Mira shows up and saves Ron."]).supported
    assert not atomic_support(atom, ["Ron saves Mira."]).supported
    assert not atomic_support(atom, ["Mira never saves Ron."]).supported
    assert not atomic_support(atom, ["Mira might save Ron."]).supported
    assert not atomic_support(atom, ["Mira met Ron and Taro saves Ron."]).supported
    assert atomic_support(
        {"subject": "Mira", "predicate": "recruits a sailor named", "object": "Ron"},
        ["Mira recruits a sailor named Ron."],
    ).supported
    assert connection_score("Mira saves Ron.", SUBJECTS, "Mira and Ron") > connection_score(
        "Mira dreams of adventure, inspired by Ron.", SUBJECTS, "Mira and Ron"
    )


def test_matching_corroboration_preserves_separate_assertions_but_not_name_mentions():
    first = evidence("Mira saves Ron. Mira gives Ron a map.")
    second = evidence("Mira shows up and saves Ron. Mira met Taro.")
    second = replace(
        second, source=replace(second.source, continuity_id=first.source.continuity_id)
    )
    bundles = EvidenceBundleBuilder().build(
        [first, second], SUBJECTS, "Mira and Ron", first.source.continuity_id, None, 2000
    )
    bundle = next(b for b in bundles if b.anchor_passage_id == first.passage.id)
    extraction, _ = compile_connected(
        bundle,
        ConnectedAssertions.model_validate(
            {
                "assertions": [
                    {"subject": "Mira", "object": "Ron", "predicate": "saves", "sentence_ids": [0]},
                    {"subject": "Mira", "object": "Ron", "predicate": "gives", "sentence_ids": [1]},
                ]
            }
        ),
    )
    rows = candidate_rows(extraction, uuid4())
    # A later same-name assertion from another extraction must not be dropped.
    later = {
        **rows[0],
        "payload": {**rows[0]["payload"], "description": "A distinct accepted clause"},
    }
    result = corroborate_candidates([*rows, later], bundles, uuid4())
    assert len(result) == len(rows) + 1
    rescue = next(r for r in result if r["payload"].get("atomic", {}).get("predicate") == "saves")
    assert len(rescue["payload"]["evidence"]) == 2
    gift = next(r for r in result if r["payload"].get("atomic", {}).get("predicate") == "gives")
    assert len(gift["payload"]["evidence"]) == 1
    payload = rescue["payload"]
    quotes = [e["quote"] for e in payload["evidence"]]
    assert atomic_payload_support(payload, quotes).supported
    assert atomic_payload_support(payload, list(reversed(quotes))).supported
    assert not atomic_payload_support(
        {**payload, "description": "Mira saves Ron and secretly rules the city"}, quotes
    ).supported


async def test_model_can_distinguish_unrelated_same_type_identity_without_spelling_filter():
    hit = evidence("Mira D. Vale saves Ron.")
    candidate = {
        "id": str(uuid4()),
        "payload": {
            "name": "Mira D. Vale",
            "type": "CHARACTER",
            "description": hit.passage.text,
            "evidence": [{"passage_id": str(hit.passage.id), "quote": hit.passage.text}],
        },
    }

    async def infer(prompt, schema):
        if schema is ContextIdentityReview:
            return schema(
                decision="new",
                alternative_status="distinguished",
                evidence_indices=[0],
                hidden_identity=False,
                reason="Owned source identifies one new person",
            )
        assert schema.__name__ == "IndexedIdentityComparison"
        assert '"name": "Taro"' in prompt
        return schema.model_validate(
            {
                "decision": "NEW_ENTITY",
                "entity_type_valid": True,
                "evidence_indices": [0],
                "hidden_identity": False,
                "reason": "Owned new identity.",
            }
        )

    result = await IdentityResolver().resolve(
        candidate,
        [{"id": str(uuid4()), "name": "Taro", "type": "CHARACTER"}],
        [hit.passage],
        infer,
        uuid4(),
        indexed_evidence=True,
    )
    assert result["accepted"] and result["canonical_id"]


def test_medium_ranking_prefers_manga_prose_and_keeps_permission_a_gate():
    universe, continuity = uuid4(), uuid4()
    manga = entry(universe, continuity).model_copy(
        update={"media": ["manga"], "name": "Mira rescue review"}
    )
    anime = manga.model_copy(
        update={
            "id": uuid4(),
            "media": ["anime"],
            "category": "episode-guide",
            "discovery_priority": 100,
        }
    )
    blocked = manga.model_copy(update={"id": uuid4(), "retrieval_policy": "navigation-only"})
    profile = UniverseResearchProfile(universe_id=universe, original_medium="manga")
    ranked = SourceSelector().rank(
        [anime, blocked, manga], str(continuity), "Mira rescue", universe, profile
    )
    assert [row[0].id for row in ranked] == [manga.id, anime.id]


def test_frontier_favors_missing_connections_and_discounts_repeated_attempts():
    base = dict(
        universe_id=uuid4(),
        continuity_id=uuid4(),
        boundary_key="one",
        objective_key="arc",
        topic="opening arc",
        discovery_origin="owned",
        priority=70,
    )
    connection = ResearchLead(
        id=uuid4(), question="How did Mira recruit Ron?", source_ids=[uuid4()], **base
    )
    trivia = ResearchLead(id=uuid4(), question="What is Mira's alias spelling?", **base)
    repeated = connection.model_copy(update={"id": uuid4(), "attempt_count": 8})
    resolved = connection.model_copy(update={"id": uuid4(), "status": "RESOLVED"})
    result = ResearchFrontierService.rank(
        [trivia, repeated, resolved, connection], "Mira and Ron opening arc"
    )
    assert result[0].id == connection.id and result[-1].id == resolved.id
    assert result.index(repeated) > result.index(connection)


async def test_related_source_permissions_are_checked_before_atomic_cloud_inference(factory):
    scope = await prepare(factory)
    async with factory() as session, session.begin():
        row = await session.scalar(
            select(SourceDocumentModel).where(SourceDocumentModel.universe_id == scope.universe_id)
        )
        row.provenance = {**row.provenance, "cloud_content_allowed": True}
        text = "Mira and Ron became partners. Ron reads the map."
        other = SourceDocument(
            uuid4(),
            scope.universe_id,
            scope.id,
            "https://second-owned.example/story",
            "Owned related",
            "Second owned",
            text,
            digest(text),
            now(),
            "Owned permission",
            "Owned scope",
            True,
            False,
            "second-owned",
            {"authority": "primary", "cloud_content_allowed": False},
        )
        await SqlResearchRepository(session).save_source(other, passages_for(other))
        request = ResearchRequest(
            universe_id=scope.universe_id,
            continuity_id=scope.id,
            objective="Mira and Ron's connected interactions",
            relationship_subjects=SUBJECTS,
            refresh=True,
            research_policy=ResearchPolicy(max_passes=1, investigation_bundle_limit=1),
        )
        job = await SqlResearchRepository(session).create_job(request)
    workflow = build_workflow(
        Settings(_env_file=None), factory, InferenceRouter(OwnedProvider(), [], mode="local")
    )
    workflow.retrieval = EvidenceRetrieval(index_transactions(factory), FakeEmbeddings())
    workflow.memory = workflow.atlas = workflow.narratives = None
    original = workflow.infer
    checked = []

    async def capture(state, prompt, schema, task, public=False):
        if task == "verification" and "Ron reads the map" in prompt:
            checked.append(public)
        return await original(state, prompt, schema, task, public)

    workflow.infer = capture
    await workflow.run(job, {})
    assert checked and not any(checked)


async def test_semantic_context_is_explicit_but_negative_verdict_still_withholds():
    hit = evidence("Mira saves Ron.")
    bundle = EvidenceBundleBuilder().build(
        [hit], SUBJECTS, "Mira and Ron", hit.source.continuity_id, None, 1000
    )[0]
    extraction, _ = compile_connected(
        bundle,
        ConnectedAssertions.model_validate(
            {
                "assertions": [
                    {"subject": "Mira", "object": "Ron", "predicate": "saves", "sentence_ids": [0]}
                ]
            }
        ),
    )
    payload = extraction.entities[0].model_dump(mode="json")

    async def infer(prompt, schema):
        assert '"continuity_label": "Original manga"' in prompt
        assert '"authority": "primary"' in prompt and hit.source.url in prompt
        return schema.model_validate(
            {
                "assessments": [
                    {
                        "index": 0,
                        "subject_supported": True,
                        "predicate_supported": True,
                        "object_supported": True,
                        "direction_valid": True,
                        "subject_type_valid": True,
                        "object_type_valid": True,
                        "actual_occurrence": True,
                        "in_universe": True,
                        "material_conflict": False,
                        "continuity_matches": False,
                        "reason": "Owned mismatch verdict.",
                    }
                ]
            }
        )

    results = await assess_atomic_batch(
        [payload["atomic"]], bundle, infer, continuity_label="Original manga"
    )
    verdict = next(iter(results.values()))
    assert candidate_assessment(payload, verdict, [hit.passage.text])["decision"] == "insufficient"


async def test_cached_new_identity_rebinds_to_current_claim_without_changing_budget(factory):
    scope = await prepare(factory)
    request = ResearchRequest(
        universe_id=scope.universe_id,
        continuity_id=scope.id,
        objective="Resolve the owned Mira identity",
        refresh=True,
    )
    async with factory() as session, session.begin():
        first = await SqlResearchRepository(session).create_job(request)
        second = await SqlResearchRepository(session).create_job(request)
    hit = evidence("Mira saves Ron.")
    payload = {
        "name": "Mira",
        "type": "CHARACTER",
        "description": hit.passage.text,
        "evidence": [{"passage_id": str(hit.passage.id), "quote": hit.passage.text}],
    }
    pipeline = build_workflow(Settings(_env_file=None), factory).knowledge
    assert pipeline
    cached = {}

    async def progress(key, decision):
        cached[key] = decision

    calls = []

    async def infer(prompt, schema, task):
        calls.append(task)
        if schema is ContextIdentityReview:
            return schema(
                decision="new",
                alternative_status="distinguished",
                evidence_indices=[0],
                hidden_identity=False,
                reason="Owned source identifies one new person",
            )
        return schema.model_validate(
            {
                "decision": "NEW_ENTITY",
                "entity_type_valid": True,
                "evidence_indices": [0],
                "hidden_identity": False,
                "reason": "Owned grounded identity.",
            }
        )

    a, b = str(uuid4()), str(uuid4())
    initial = await pipeline.resolve(
        first,
        [{"id": a, "kind": "entity", "payload": payload}],
        [hit.passage],
        infer,
        grounded=True,
        progress=progress,
    )
    repeated = await pipeline.resolve(
        second,
        [{"id": b, "kind": "entity", "payload": payload}],
        [hit.passage],
        infer,
        grounded=True,
        completed=cached,
    )
    assert calls == ["identity_resolution", "identity_resolution"]
    assert initial[a]["canonical_id"] == str(uuid5(scope.id, "entity:" + a))
    assert repeated[b]["canonical_id"] == str(uuid5(scope.id, "entity:" + b))


async def test_one_bounded_repair_preserves_literal_complements_and_unfinished_assertions():
    hit = evidence("Mira recruits a sailor named Ron.")
    bundle = EvidenceBundleBuilder().build(
        [hit], SUBJECTS, "Mira and Ron", hit.source.continuity_id, None, 1000
    )[0]
    answer = ConnectedAssertions.model_validate(
        {
            "assertions": [
                {"subject": "Mira", "object": "Ron", "predicate": "recruits", "sentence_ids": [0]}
            ]
        }
    )
    calls = []

    async def infer(prompt, schema):
        calls.append(prompt)
        return schema.model_validate(
            {
                "assertions": [
                    {
                        "subject": "Mira",
                        "object": "Ron",
                        "predicate": "recruits a sailor named",
                        "sentence_ids": [0],
                    }
                ]
            }
        )

    repaired = await repair_connected(bundle, answer, infer)
    extraction, _ = compile_connected(bundle, repaired)
    assert len(calls) == 1 and extraction.relationships
    await repair_connected(bundle, repaired, infer)
    assert len(calls) == 1

    async def empty(prompt, schema):
        return schema.model_validate({"assertions": []})

    assert (await repair_connected(bundle, answer, empty)).assertions == answer.assertions


async def test_connected_publication_updates_frontier_coverage_from_accepted_facts(factory):
    scope = await prepare(factory)

    class CoverageProvider(OwnedProvider):
        async def generate(self, system, prompt, schema, task):
            if schema.__name__ == "CoverageReview":
                self.calls.append(task)
                return InferenceResult(
                    schema.model_validate(
                        {
                            "answers": [
                                {"lead_index": 0, "fact_indices": [0], "fully_answered": False}
                            ]
                        }
                    ),
                    InferenceUsage(self.name, self.model, self.credential, task, "ok", 1, 20, 10),
                )
            return await super().generate(system, prompt, schema, task)

    request = ResearchRequest(
        universe_id=scope.universe_id,
        continuity_id=scope.id,
        objective="Investigate Mira and Ron's connected story",
        relationship_subjects=SUBJECTS,
        research_policy=ResearchPolicy(max_passes=1, investigation_bundle_limit=1),
        refresh=True,
    )
    async with factory() as session, session.begin():
        job = await SqlResearchRepository(session).create_job(request)
    workflow = build_workflow(
        Settings(_env_file=None), factory, InferenceRouter(CoverageProvider(), [], mode="local")
    )
    workflow.retrieval = EvidenceRetrieval(index_transactions(factory), FakeEmbeddings())
    state = await workflow.run(job, {})
    assert state["publication"]["promoted"] and state["coverage"]["relevant_facts"] > 0
    async with factory() as session:
        leads = await SqlResearchMemory(session).leads(
            scope.universe_id, scope.id, ResearchFrontierService.boundary(None)
        )
    answered = [lead for lead in leads if lead.status == "PARTIALLY_RESOLVED"]
    assert answered and answered[0].evidence_ids and answered[0].last_job_id == job


async def test_joint_arrival_verifier_receives_coactors_not_a_destination_object():
    hit = evidence("Mira and Ron arriving at the observatory.")
    bundle = EvidenceBundleBuilder().build(
        [hit], SUBJECTS, "Mira and Ron", hit.source.continuity_id, None, 1000
    )[0]
    extraction, _ = compile_connected(
        bundle,
        ConnectedAssertions.model_validate(
            {
                "assertions": [
                    {
                        "subject": "Mira",
                        "object": "Ron",
                        "predicate": "arriving at the observatory",
                        "sentence_ids": [0],
                    }
                ]
            }
        ),
    )
    payload = extraction.entities[0].model_dump(mode="json")

    async def infer(prompt, schema):
        assert '"binding_kind": "joint_role"' in prompt
        return schema.model_validate(
            {
                "assessments": [
                    {
                        "index": 0,
                        "subject_supported": True,
                        "predicate_supported": True,
                        "object_supported": True,
                        "direction_valid": True,
                        "subject_type_valid": True,
                        "object_type_valid": True,
                        "actual_occurrence": True,
                        "in_universe": True,
                        "material_conflict": False,
                        "continuity_matches": True,
                        "reason": "Owned explicit co-actors.",
                    }
                ]
            }
        )

    results = await assess_atomic_batch([payload["atomic"]], bundle, infer)
    assert (
        candidate_assessment(payload, next(iter(results.values())), [hit.passage.text])["decision"]
        == "supported"
    )
    assert extraction.entities[-1].event["participant_roles"] == {"Mira": "actor", "Ron": "actor"}


async def test_reconstruction_only_coverage_has_an_explicit_worker_outcome(factory):
    scope = await prepare(factory)
    request = ResearchRequest(
        universe_id=scope.universe_id,
        continuity_id=scope.id,
        objective="Rebuild an owned presentation",
        presentation_only=True,
    )
    async with factory() as session, session.begin():
        job = await SqlResearchRepository(session).create_job(request)
    workflow = build_workflow(Settings(_env_file=None), factory)
    state = await workflow.reconstruction_stage({"job_id": str(job)}, request)
    assert state["coverage"]["outcome"] == "INSUFFICIENT_EVIDENCE"
    assert state["reconstruction"]["status"] == "no_verified_segments"
