"""Whole pipeline with owned text and explicitly fake providers, never a real research demo."""

import json
from uuid import uuid4

from sqlalchemy import func, select

from src.application.inference import InferenceRouter
from src.application.relationship_contracts import InvestigationSubject
from src.application.research import ResearchRequest
from src.application.research_contracts import (
    InferenceFailure,
    InferenceResult,
    InferenceUsage,
    ResearchPlan,
)
from src.application.research_policy import ResearchPolicy
from src.application.retrieval import EvidenceRetrieval
from src.domain.entities import now
from src.domain.research import SourceDocument, digest, passages_for
from src.infrastructure.config.settings import Settings
from src.infrastructure.persistence.models import ContinuityModel, NodeModel, RelationshipModel
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.research_runtime import build_workflow, index_transactions

from .test_source_intelligence import FakeEmbeddings

TEXT = (
    "Mira and Ron became partners. Mira and Taro started training for magic. "
    "Mira invented Ember Shield."
)


class OwnedProvider:
    name, model, credential = "fake-owned", "owned-v1", "test"

    def __init__(self):
        self.calls = []

    async def available(self):
        return True

    async def generate(self, system, prompt, schema, task):
        self.calls.append(task)
        data, _ = json.JSONDecoder().raw_decode(prompt[prompt.index("{") :])
        if task == "planning":
            value = ResearchPlan(questions=["How are Mira and Ron connected?"], queries=[])
        elif schema.__name__ == "ConnectedAssertions":
            value = schema.model_validate(
                {
                    "assertions": [
                        {
                            "subject": "Mira",
                            "object": "Ron",
                            "predicate": "became partners",
                            "sentence_ids": [0],
                        },
                        {
                            "subject": "Mira",
                            "object": "Taro",
                            "predicate": "started training for magic",
                            "sentence_ids": [1],
                        },
                        {
                            "subject": "Mira",
                            "object": "Ember Shield",
                            "object_type": "LORE",
                            "predicate": "invented",
                            "sentence_ids": [2],
                        },
                    ]
                }
            )
        elif task == "identity_resolution":
            if schema.__name__ == "ContextIdentityReview":
                return InferenceResult(
                    schema(
                        decision="new",
                        alternative_status="distinguished",
                        evidence_indices=[0],
                        hidden_identity=False,
                        reason="Owned source identifies one new person",
                    ),
                    InferenceUsage(
                        self.name,
                        self.model,
                        self.credential,
                        task,
                        "ok",
                        1,
                        input_tokens=100,
                        output_tokens=30,
                    ),
                )
            value = schema.model_validate(
                {
                    "decision": "NEW_ENTITY",
                    "entity_type_valid": True,
                    "evidence_indices": [0],
                    "hidden_identity": False,
                    "reason": "Owned grounded identity.",
                    **(
                        {
                            "same_occurrence": False,
                            "same_granularity": False,
                            "repeated_occurrence_excluded": False,
                        }
                        if schema.__name__ == "EventIdentityComparison"
                        else {}
                    ),
                }
            )
        elif schema.__name__ == "AtomicVerdicts":
            value = schema.model_validate(
                {
                    "assessments": [
                        {
                            "index": i,
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
                            "reason": "Owned atomic support.",
                        }
                        for i in range(len(data["claims"]))
                    ]
                }
            )
        else:
            raise AssertionError((task, schema.__name__))
        return InferenceResult(
            value,
            InferenceUsage(
                self.name,
                self.model,
                self.credential,
                task,
                "ok",
                1,
                input_tokens=100,
                output_tokens=30,
            ),
        )


async def prepare(factory):
    async with factory() as s, s.begin():
        scope = await s.scalar(select(ContinuityModel))
        source = SourceDocument(
            uuid4(),
            scope.universe_id,
            scope.id,
            "https://owned.example/relationships",
            "Owned primary",
            "Owned publisher",
            TEXT,
            digest(TEXT),
            now(),
            "Owned synthetic permission",
            "Owned scoped text",
            True,
            False,
            "owned-publisher",
            {"authority": "primary", "language": "en"},
        )
        await SqlResearchRepository(s).save_source(source, passages_for(source))
    return scope


async def run(factory, scope, provider, policy=None):
    request = ResearchRequest(
        universe_id=scope.universe_id,
        continuity_id=scope.id,
        objective="Investigate Mira and Ron's relationship and connected interactions.",
        relationship_subjects=[InvestigationSubject(name="Mira"), InvestigationSubject(name="Ron")],
        refresh=True,
        research_policy=policy or ResearchPolicy(max_passes=1, investigation_bundle_limit=1),
    )
    async with factory() as s, s.begin():
        identifier = await SqlResearchRepository(s).create_job(request)
    workflow = build_workflow(
        Settings(_env_file=None), factory, InferenceRouter(provider, [], mode="local")
    )
    workflow.retrieval = EvidenceRetrieval(index_transactions(factory), FakeEmbeddings())
    workflow.memory = None
    workflow.atlas = None
    workflow.narratives = None
    state = await workflow.run(identifier, {})
    return identifier, state


async def test_connected_workflow_publishes_and_repeat_reuses_verification_without_duplicates(
    factory,
):
    scope = await prepare(factory)
    provider = OwnedProvider()
    first, state = await run(factory, scope, provider)
    assert len(state["publication"]["promoted"]) == 15
    assert not state["investigation"]["pending_claims"]
    async with factory() as s:
        counts = [
            await s.scalar(select(func.count()).select_from(model))
            for model in [NodeModel, RelationshipModel]
        ]
    before = len(provider.calls)
    second, repeated = await run(factory, scope, provider)
    assert first != second
    assert len(repeated["publication"]["promoted"]) == 15
    assert provider.calls[before:] == ["planning"]
    async with factory() as s:
        assert counts == [
            await s.scalar(select(func.count()).select_from(model))
            for model in [NodeModel, RelationshipModel]
        ]
        findings = await SqlResearchRepository(s).findings(second)
    assert len(findings) == 15 and all(f["canonical"] for f in findings)


class InterruptedProvider(OwnedProvider):
    def __init__(self):
        super().__init__()
        self.verified_batches = 0

    async def generate(self, system, prompt, schema, task):
        if task == "verification":
            self.verified_batches += 1
            if self.verified_batches > 1:
                raise InferenceFailure("job_token_budget_exhausted")
        return await super().generate(system, prompt, schema, task)


async def test_partial_verification_survives_and_new_bounded_job_finishes_only_pending_work(
    factory,
):
    scope = await prepare(factory)
    policy = ResearchPolicy(max_passes=1, investigation_bundle_limit=1, verification_batch_size=1)
    job, partial = await run(factory, scope, InterruptedProvider(), policy)
    assert len(partial["investigation"]["assessments"]) == 1, [
        (v["method"], v["verdict"]) for v in partial["investigation"]["assessments"].values()
    ]
    assert len(partial["investigation"]["pending_claims"]) == 2
    assert len(partial["publication"]["promoted"]) == 6
    async with factory() as s:
        saved = await SqlResearchRepository(s).get_job(job)
    assert (
        saved["checkpoint"]["investigation"]["assessments"]
        == partial["investigation"]["assessments"]
    )
    provider = OwnedProvider()
    _, finished = await run(factory, scope, provider, policy)
    assert provider.calls.count("verification") == 2
    assert "relationship_analysis" not in provider.calls
    assert len(finished["publication"]["promoted"]) == 15
    assert not finished["investigation"]["pending_claims"]
    async with factory() as s:
        assert await s.scalar(select(func.count()).select_from(NodeModel)) == 22
        assert await s.scalar(select(func.count()).select_from(RelationshipModel)) == 33
