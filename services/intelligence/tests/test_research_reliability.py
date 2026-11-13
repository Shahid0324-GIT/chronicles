"""Owned synthetic inference and event evidence. No live model results here."""

import pytest
from pydantic import RootModel, ValidationError

from src.application.event_extraction import EventFrames, extract_events
from src.application.inference import InferenceRouter
from src.application.research_contracts import InferenceFailure, ResearchPlan, validation_issues
from src.infrastructure.research_runtime import build_inference_cache

from .test_event_narrative import passage
from .test_inference import Provider
from .test_research import prepare


@pytest.mark.parametrize("role,expected", [("actor", 3), ("opponent", 3), ("mentioned", 2)])
async def test_publication_checks_participant_role_even_when_model_says_supported(
    factory, role, expected
):
    from uuid import UUID

    from src.infrastructure.persistence.models.research import ResearchClaimModel

    from .test_knowledge import prepared

    job, service, _, claims, resolutions = await prepared(factory)
    event = next(c for c in claims if c["payload"].get("type") == "EVENT")
    async with factory() as session, session.begin():
        row = await session.get(ResearchClaimModel, UUID(event["id"]))
        row.payload = {
            **row.payload,
            "event": {"occurrence_status": "actual", "participant_roles": {"Mira Vale": role}},
        }
    result = await service.publish(job, resolutions, {}, False)
    assert len(result["promoted"]) == expected


def test_real_world_promotional_location_cannot_pass_story_structure():
    from src.domain.knowledge import in_world_structure

    assert not in_world_structure(
        {
            "name": "Town Square",
            "type": "LOCATION",
            "description": "The advertisement names Town Square as its promotional event venue.",
        },
        ["The advertisement names Town Square as its promotional event venue."],
    )
    assert in_world_structure(
        {
            "name": "Observatory",
            "type": "LOCATION",
            "description": "Mira enters the observatory in the story.",
        },
        ["Mira enters the observatory in the story."],
    )


def test_occurrence_reuse_normalizes_unique_aliases_without_merging_repeated_events():
    from src.application.event_identity import same_scoped_occurrence

    catalog = [
        {"id": "owned-mira-id", "name": "Mira Vale", "type": "CHARACTER", "aliases": ["ミラ"]}
    ]
    left = {
        "source_id": "owned-source",
        "participants": ["Mira Vale"],
        "trigger_start": 10,
        "trigger_end": 18,
    }
    right = {**left, "participants": ["ミラ"], "trigger_start": 8}
    assert same_scoped_occurrence(left, right, catalog)
    assert not same_scoped_occurrence(
        left, {**right, "trigger_start": 30, "trigger_end": 38}, catalog
    )
    assert not same_scoped_occurrence(left, {**right, "source_id": "another-source"}, catalog)
    assert not same_scoped_occurrence(
        left,
        right,
        [
            *catalog,
            {"id": "other", "name": "Other person", "type": "CHARACTER", "aliases": ["ミラ"]},
        ],
    )


class RecordingProvider(Provider):
    revision = "owned-model-digest-1"

    def __init__(self, failures=()):
        super().__init__(failures=failures)
        self.prompts = []

    async def generate(self, system, prompt, schema, task):
        self.prompts.append(prompt)
        return await super().generate(system, prompt, schema, task)


async def test_structured_repair_changes_prompt_and_terminates():
    provider = RecordingProvider(
        [InferenceFailure("invalid_output", issues=("questions:missing",))]
    )
    router = InferenceRouter(provider, [])
    await router.generate("Owned test", "Owned question", ResearchPlan, "planning")
    assert provider.prompts[0] != provider.prompts[1]
    assert "questions:missing" in provider.prompts[1]
    assert router.usage[0].validation_errors == ("questions:missing",)
    assert router.usage[1].retry == 1
    provider = RecordingProvider([InferenceFailure("invalid_output")] * 5)
    with pytest.raises(InferenceFailure, match="structured_output_exhausted"):
        await InferenceRouter(provider, [], attempts=2).generate(
            "Owned", "Owned", ResearchPlan, "planning"
        )
    assert provider.calls == 2


async def test_provider_failure_is_distinct_from_schema_failure():
    with pytest.raises(InferenceFailure, match="provider_unavailable"):
        await InferenceRouter(
            RecordingProvider([InferenceFailure("model_unavailable")]), []
        ).generate("Test", "Test", ResearchPlan, "planning")


def test_validation_diagnostics_omit_values_and_unexpected_field_names():
    try:
        ResearchPlan.model_validate({"questions": [123], "private-secret-key": "private input"})
    except ValidationError as error:
        issues = validation_issues(error, ResearchPlan)
    assert "questions.0:string_type" in issues
    assert "private" not in repr(issues)


async def test_job_stage_and_restored_budgets_stop_before_call():
    provider = RecordingProvider()
    router = InferenceRouter(provider, [], max_calls=2, stage_limits={"planning": 1})
    await router.generate("Test", "Test", ResearchPlan, "planning")
    with pytest.raises(InferenceFailure, match="stage_model_budget_exhausted"):
        await router.generate("Test", "Test", ResearchPlan, "planning")
    router.restore_budget(
        [{"status": "ok", "task": "extraction"}] * 2 + [{"status": "cache_hit", "task": "planning"}]
    )
    with pytest.raises(InferenceFailure, match="job_model_budget_exhausted"):
        await router.generate("Test", "Test", ResearchPlan, "verification")
    assert provider.calls == 1


async def test_incompatible_root_contract_fails_without_provider_call():
    provider = RecordingProvider()
    with pytest.raises(InferenceFailure, match="schema_incompatible"):
        await InferenceRouter(provider, []).generate(
            "Test", "Test", RootModel[list[str]], "extraction"
        )
    assert not provider.calls


async def test_persistent_exact_context_cache_validates_and_separates_revision(factory):
    provider = RecordingProvider()
    router = InferenceRouter(provider, [], cache=build_inference_cache(factory))
    await router.generate("Owned", "Unchanged source evidence", ResearchPlan, "extraction")
    await router.generate("Owned", "Unchanged source evidence", ResearchPlan, "extraction")
    assert provider.calls == 1 and router.usage[-1].status == "cache_hit"
    provider.revision = "owned-model-digest-2"
    await router.generate("Owned", "Unchanged source evidence", ResearchPlan, "extraction")
    await router.generate("Owned", "Changed evidence", ResearchPlan, "extraction")
    assert provider.calls == 3


@pytest.mark.parametrize("status", ["intended", "hypothetical", "denied", "reported", "uncertain"])
async def test_nonactual_event_is_archived_without_participation(status):
    async def infer(prompt, schema):
        return EventFrames.model_validate(
            {
                "events": [
                    {
                        "trigger": "entered",
                        "occurrence_status": status,
                        "participants": [{"name": "Mira Vale", "role": "actor"}],
                        "sentence_ids": [0],
                    }
                ]
            }
        )

    result = await extract_events([passage()], "Owned event research", infer)
    assert result.entities[0].event["occurrence_status"] == status
    assert not result.relationships


async def test_stage_telemetry_and_summary_are_persisted(factory, app):
    from httpx import ASGITransport, AsyncClient

    job, workflow, _, _, tx = await prepare(factory)
    await workflow.run(job, {})
    async with tx() as archive:
        events = await archive.events(job)
    assert len([e for e in events if e["stage"] == "stage.started"]) == 4
    assert len([e for e in events if e["stage"] == "stage.completed"]) == 4
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/research/jobs/{job}/summary")
    assert response.status_code == 200
    summary = response.json()
    assert summary["model_calls"] == 5 and summary["candidate_entities"] == 2
    assert summary["accepted_relationships"] == 0 and len(summary["stage_elapsed_ms"]) == 4


async def test_interrupted_call_reservation_survives_worker_restart_budget(factory, app):
    from httpx import ASGITransport, AsyncClient

    job, workflow, provider, _, tx = await prepare(factory)
    workflow.inference.max_calls = 1
    async with tx() as archive:
        await archive.event(
            job,
            "inference.started",
            {"reservation_id": "owned-interrupted-call", "task": "planning"},
        )
    with pytest.raises(InferenceFailure, match="job_model_budget_exhausted"):
        await workflow.run(job, {})
    assert not provider.tasks
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        summary = (await client.get(f"/api/research/jobs/{job}/summary")).json()
    assert summary["model_calls"] == 1 and summary["incomplete_call_reservations"] == 1


async def test_persisted_deadline_stops_restarted_execution_before_any_model_call(factory):
    job, workflow, provider, _, _ = await prepare(factory)
    with pytest.raises(InferenceFailure, match="job_duration_exceeded"):
        await workflow.run(job, {"deadline_at": 1.0})
    assert not provider.tasks


def test_summary_discoveries_deduplicate_support_records_and_use_readable_labels():
    from src.application.research_summary import research_summary

    job = {
        "id": "owned-job",
        "status": "partial",
        "error": None,
        "checkpoint": {},
        "provider_usage": [],
        "created_at": "2026-11-13T10:00:00+00:00",
        "updated_at": "2026-11-13T10:01:00+00:00",
    }
    fact = {
        "id": "owned-claim",
        "canonical": True,
        "canonical_id": "owned-edge",
        "kind": "relationship",
        "payload": {
            "type": "PARTICIPATED_IN",
            "source_name": "Mira Vale",
            "target_name": "Arrival",
        },
    }
    summary = research_summary(job, [fact, {**fact, "id": "second-support"}])
    assert summary["accepted_relationships"] == 1 and len(summary["discoveries"]) == 1
    assert summary["discoveries"][0]["label"] == "Mira Vale → Arrival · participated in"
