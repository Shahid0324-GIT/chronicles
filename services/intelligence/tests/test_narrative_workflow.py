"""Owned synthetic end-to-end RAG/event/publication journey; fake models are explicit."""

import json
from uuid import UUID

import pytest

from src.application.event_extraction import EventFrames
from src.application.inference import InferenceRouter
from src.application.knowledge_contracts import RelationshipAnalysis
from src.application.research import ResearchRequest, SourceInput
from src.application.research_contracts import InferenceResult, InferenceUsage
from src.application.retrieval import EvidenceRetrieval
from src.infrastructure.config.settings import Settings
from src.infrastructure.research_runtime import build_workflow, index_transactions

from .test_knowledge import prepared
from .test_knowledge_workflow import SyntheticInference
from .test_source_intelligence import FakeEmbeddings


class NarrativeInference(SyntheticInference):
    content_kind = "fictional-story"

    async def generate(self, system, prompt, schema, task):
        data = json.loads(prompt[prompt.index("{") :])
        if schema is EventFrames:
            self.tasks.append(task)
            sentence = next(s for s in data["sentences"] if "Mira Vale" in s["text"])
            value = EventFrames.model_validate(
                {
                    "events": [
                        {
                            "trigger": "entered",
                            "occurrence_status": "actual",
                            "participants": [{"name": "Mira Vale", "role": "actor"}],
                            "location": "observatory",
                            "sentence_ids": [sentence["id"]],
                        }
                    ]
                }
            )
        elif task == "identity_resolution":
            self.tasks.append(task)
            target = next(
                (n for n in data["matches"] if n["name"] == data["candidate"]["name"]), None
            )
            value = schema.model_validate(
                dict(
                    decision="SAME_ENTITY" if target else "NEW_ENTITY",
                    target_index=target["index"] if target else None,
                    entity_type_valid=True,
                    reason="Owned test comparison with exact current identity.",
                    evidence_indices=[0],
                    **(
                        {
                            "same_occurrence": bool(target),
                            "same_granularity": bool(target),
                            "repeated_occurrence_excluded": bool(target),
                        }
                        if schema.__name__ == "EventIdentityComparison"
                        else {}
                    ),
                )
            )
        elif task == "relationship_analysis":
            self.tasks.append(task)
            value = RelationshipAnalysis(relationships=[])
        elif task == "verification":
            self.tasks.append(task)
            value = schema.model_validate(
                {
                    "assessments": [
                        {
                            "claim_id": data["candidates"][0]["claim_id"],
                            "decision": "supported",
                            "reason": "Owned synthetic content classification fixture.",
                            "content_kind": self.content_kind,
                            "entity_type_valid": True,
                        }
                    ]
                }
            )
        else:
            return await super().generate(system, prompt, schema, task)
        return InferenceResult(
            value, InferenceUsage(self.name, self.model, self.credential, task, "ok", 1)
        )


@pytest.mark.parametrize(
    "content_kind,accepted", [("fictional-story", True), ("real-world-publication", False)]
)
async def test_complete_narrative_workflow_indexes_resolves_promotes_and_resumes(
    factory, content_kind, accepted
):
    old_job, service, tx, _, resolutions = await prepared(factory)
    await service.publish(old_job, resolutions, {}, False)
    async with tx() as unit:
        old = await unit.archive.get_job(old_job)
        request = ResearchRequest(
            universe_id=UUID(old["universe_id"]),
            continuity_id=UUID(old["continuity_id"]),
            narrative_research=True,
            spoiler_position=1,
            objective="Research the owned observatory arrival.",
            sources=[
                SourceInput(
                    text=(
                        "Mira Vale entered the observatory. Mira Vale participated in the arrival."
                    ),
                    permission_basis="Owned synthetic test permission",
                    source_scope="Owned test scope",
                    presentation_position=1,
                    position_basis="broadcast-presentation",
                )
            ],
        )
        job = await unit.archive.create_job(request)
    fake = NarrativeInference()
    fake.content_kind = content_kind
    workflow = build_workflow(
        Settings(_env_file=None), factory, InferenceRouter(fake, [], mode="local")
    )
    embeddings = FakeEmbeddings()
    workflow.retrieval = EvidenceRetrieval(index_transactions(factory), embeddings)
    state = await workflow.run(job, {})
    assert state["indexing"]["indexed"] == 1
    assert bool(state["publication"]["promoted"]) == accepted
    assert state["narrative"]["journeys"] == int(accepted)
    async with tx() as unit:
        findings = await unit.archive.findings(job)
    assert any(f["kind"] == "relationship" and f["canonical"] for f in findings) == accepted
    before = (len(fake.tasks), embeddings.calls)
    await workflow.run(job, dict(state))
    assert before == (len(fake.tasks), embeddings.calls)
