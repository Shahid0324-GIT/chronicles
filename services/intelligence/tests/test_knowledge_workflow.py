"""End-to-end orchestration with explicitly synthetic owned text and fake model outputs."""

import json
from uuid import UUID

from sqlalchemy import select

from src.application.inference import InferenceRouter
from src.application.knowledge_contracts import IdentityComparison, RelationshipAnalysis
from src.application.research import ResearchRequest, SourceInput
from src.application.research_contracts import (
    Extraction,
    InferenceResult,
    InferenceUsage,
    ResearchPlan,
)
from src.infrastructure.config.settings import Settings
from src.infrastructure.persistence.models import ContinuityModel
from src.infrastructure.research_runtime import build_workflow, knowledge_transactions

TEXT = (
    "Mira Vale entered the observatory. Mira Vale participated in the arrival. "
    "The arrival happened at the observatory."
)

SECOND_TEXT = (
    "Mira Vale reached the observatory during the arrival and was present for that occurrence."
)


class SyntheticInference:
    name, model, credential = "fake-test", "synthetic", "test"

    def __init__(self):
        self.tasks = []

    async def available(self):
        return True

    async def generate(self, system, prompt, schema, task):
        self.tasks.append(task)
        data = json.loads(prompt[prompt.index("{") :])
        if task == "planning":
            value = ResearchPlan(questions=["What does the synthetic source say?"], queries=[])
        elif task == "extraction":
            evidence = [
                {
                    "passage_id": next(p["id"] for p in data["passages"] if p["text"] == TEXT),
                    "quote": TEXT,
                }
            ]
            value = Extraction.model_validate(
                {
                    "entities": [
                        {
                            "name": "Mira Vale",
                            "type": "CHARACTER",
                            "description": "Mira Vale entered the observatory.",
                            "evidence": evidence
                            + [
                                {
                                    "passage_id": next(
                                        p["id"]
                                        for p in data["passages"]
                                        if p["text"] == SECOND_TEXT
                                    ),
                                    "quote": SECOND_TEXT,
                                }
                            ],
                        },
                        {
                            "name": "arrival",
                            "type": "EVENT",
                            "description": "The arrival happened at the observatory.",
                            "evidence": evidence,
                        },
                    ],
                    "relationships": [],
                }
            )
        elif task == "identity_resolution":
            value = IdentityComparison(
                entity_type_valid=True,
                decision="NEW_ENTITY",
                reason="Owned synthetic entity has no match.",
                evidence=data["candidate"]["evidence"],
            )
        elif task == "relationship_analysis":
            assert len(data["identities"]) == 2
            assert all(UUID(n["canonical_id"]) for n in data["identities"])
            value = RelationshipAnalysis.model_validate(
                {
                    "relationships": [
                        {
                            "source_name": "Mira Vale",
                            "target_name": "arrival",
                            "type": "PARTICIPATED_IN",
                            "description": "Mira Vale participated in the arrival.",
                            "evidence": [
                                {
                                    "passage_id": next(
                                        p["id"] for p in data["passages"] if p["text"] == TEXT
                                    ),
                                    "quote": TEXT,
                                }
                            ],
                        }
                    ]
                }
            )
        else:
            value = schema.model_validate(
                {
                    "assessments": [
                        {
                            "claim_id": data["candidates"][0]["claim_id"],
                            "decision": "supported",
                            "reason": "Synthetic excerpt supports fixture.",
                            **(
                                {"content_kind": "fictional-story"}
                                if schema.__name__ == "NarrativeVerification"
                                else {"in_universe": True}
                            ),
                            "entity_type_valid": True,
                        }
                    ]
                }
            )
        return InferenceResult(
            value, InferenceUsage(self.name, self.model, self.credential, task, "ok", 1)
        )


async def test_extended_workflow_orders_roles_promotes_and_resumes_without_inference(factory):
    tx = knowledge_transactions(factory)
    async with factory() as session:
        scope = await session.scalar(select(ContinuityModel))
    async with tx() as unit:
        identifier = await unit.archive.create_job(
            ResearchRequest(
                universe_id=scope.universe_id,
                continuity_id=scope.id,
                objective="Research owned synthetic source and build verified graph.",
                sources=[
                    SourceInput(
                        text=TEXT,
                        permission_basis="Owned synthetic test source",
                        source_scope="Test scope",
                        reference_url="https://first.example.org/story",
                    ),
                    SourceInput(
                        text=SECOND_TEXT,
                        permission_basis="Owned synthetic second source",
                        source_scope="Test scope",
                        reference_url="https://second.example.net/story",
                    ),
                ],
            )
        )
    fake, cloud = SyntheticInference(), SyntheticInference()
    router = InferenceRouter(fake, [cloud], mode="local", cloud_content_allowed=True)
    workflow = build_workflow(Settings(_env_file=None), factory, router)
    state = await workflow.run(identifier, {})
    assert fake.tasks == [
        "planning",
        "extraction",
        "identity_resolution",
        "identity_resolution",
        "relationship_analysis",
        "verification",
        "verification",
        "verification",
    ]
    assert not cloud.tasks
    assert len(state["publication"]["promoted"]) == 3
    calls = len(fake.tasks)
    await workflow.run(identifier, dict(state))
    assert len(fake.tasks) == calls
    async with tx() as unit:
        events = await unit.archive.events(identifier)
        assert "research.identity_resolver" in [event["stage"] for event in events]
        assert "research.relationship_analyst" in [event["stage"] for event in events]
        assert len(await unit.graph.records(identifier)) == 3
