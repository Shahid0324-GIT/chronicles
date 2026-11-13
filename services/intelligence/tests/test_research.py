"""Deterministic fake-inference tests. These are NOT the live research demonstration."""

import json
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from src.application.inference import InferenceRouter
from src.application.research import FetchedDocument, ResearchRequest, SourceInput
from src.application.research_contracts import (
    Extraction,
    InferenceFailure,
    InferenceResult,
    InferenceUsage,
    ResearchPlan,
    Verification,
)
from src.infrastructure.persistence.models import ContinuityModel, NodeModel, RelationshipModel
from src.infrastructure.persistence.models.research import ResearchClaimModel, SourceDocumentModel
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.orchestration.research_workflow import ResearchCancelled, ResearchWorkflow

TEXT = (
    "Mira entered the observatory. The arrival took place at the observatory. "
    "Mira participated in the arrival."
)


class FakeInference:
    name, model, credential = "test-fake", "test-only", "test"

    def __init__(self, fabricated_quote=False, decision="supported"):
        self.tasks = []
        self.fabricated_quote, self.decision = fabricated_quote, decision

    async def available(self):
        return True

    async def generate(self, system, prompt, schema, task):
        self.tasks.append(task)
        if task == "planning":
            value = ResearchPlan(
                questions=["What does the test source explicitly state?"],
                queries=["synthetic source"],
            )
        else:
            data = json.loads(prompt[prompt.index("{") :])
            if task == "extraction":
                passage_id = data["passages"][0]["id"]
                evidence = [
                    {
                        "passage_id": passage_id,
                        "quote": "A fabricated quote that does not exist"
                        if self.fabricated_quote
                        else TEXT,
                    }
                ]
                value = Extraction.model_validate(
                    {
                        "entities": [
                            {
                                "name": "Mira",
                                "type": "CHARACTER",
                                "description": "Mira entered the observatory.",
                                "evidence": evidence,
                            },
                            {
                                "name": "The arrival",
                                "type": "EVENT",
                                "description": "The arrival took place at the observatory.",
                                "evidence": evidence,
                            },
                        ],
                        "relationships": [
                            {
                                "source_name": "Mira",
                                "target_name": "The arrival",
                                "type": "PARTICIPATED_IN",
                                "description": "Mira participated in the arrival.",
                                "evidence": evidence,
                            }
                        ],
                    }
                )
            else:
                value = Verification.model_validate(
                    {
                        "assessments": [
                            {
                                "claim_id": c["claim_id"],
                                "decision": self.decision,
                                "reason": "Test-only assessment of the supplied excerpt.",
                            }
                            for c in data["candidates"]
                        ]
                    }
                )
        return InferenceResult(
            value, InferenceUsage(self.name, self.model, self.credential, task, "ok", 1)
        )


class FakeFetcher:
    def __init__(self):
        self.calls = 0

    async def fetch(self, url):
        self.calls += 1
        return FetchedDocument(
            url=url, title="Synthetic test source", publisher="test", text=TEXT, truncated=False
        )


class FakeSearch:
    def __init__(self):
        self.calls = 0

    async def search(self, query, limit):
        self.calls += 1
        return ["https://example.org/test"]


async def prepare(factory, fake=None, search=None, sources=None, allow_search=False, **limits):
    @asynccontextmanager
    async def transaction():
        async with factory() as session, session.begin():
            yield SqlResearchRepository(session)

    async with factory() as session:
        continuity = await session.scalar(select(ContinuityModel))
        request = ResearchRequest(
            universe_id=continuity.universe_id,
            continuity_id=continuity.id,
            objective="Research the explicit synthetic observatory arrival.",
            sources=sources
            if sources is not None
            else [
                SourceInput(
                    text=TEXT,
                    permission_basis="Synthetic test fixture owned by this test",
                    source_scope="Synthetic test continuity",
                )
            ],
            allow_search=allow_search,
        )
    async with transaction() as archive:
        identifier = await archive.create_job(request)
    provider, fetcher = fake or FakeInference(), FakeFetcher()
    router = InferenceRouter(provider, [], mode="local")
    workflow = ResearchWorkflow(transaction, router, fetcher, search, **limits)
    return identifier, workflow, provider, fetcher, transaction


async def test_unavailable_verifier_does_not_block_other_claims(factory):
    class OneUnavailableClaim(FakeInference):
        def __init__(self):
            super().__init__()
            self.failed_claim = None

        async def generate(self, system, prompt, schema, task):
            if task == "verification":
                data = json.loads(prompt[prompt.index("{") :])
                claim_id = data["candidates"][0]["claim_id"]
                if self.failed_claim is None:
                    self.failed_claim = claim_id
                if claim_id == self.failed_claim:
                    raise InferenceFailure("model_unavailable")
            return await super().generate(system, prompt, schema, task)

    identifier, workflow, _, _, tx = await prepare(factory, fake=OneUnavailableClaim())
    state = await workflow.run(identifier, {})
    assert state["verified"] == 2
    async with tx() as archive:
        findings = await archive.findings(identifier)
    failed = [f for f in findings if f["decision"] == "insufficient"]
    assert len(failed) == 1
    assert "Verifier inference unavailable" in failed[0]["reason"]


async def test_workflow_persists_source_evidence_and_keeps_canonical_graph_unchanged(factory):
    identifier, workflow, provider, fetcher, tx = await prepare(factory)
    state = await workflow.run(identifier, {})
    assert state["verified"] == 3
    assert provider.tasks == ["planning", "extraction"] + ["verification"] * 3
    assert fetcher.calls == 0  # imported documents work without Internet access
    async with tx() as archive:
        findings = await archive.findings(identifier)
        events = await archive.events(identifier)
        job = await archive.get_job(identifier)
    assert len(findings) == 3 and all(not row["canonical"] for row in findings)
    assert all(
        row["decision"] == "supported" and row["evidence"][0]["quote"] == TEXT for row in findings
    )
    assert [row["stage"] for row in events] == [
        "research.queued",
        "research.planner",
        "research.researcher",
        "research.extractor",
        "research.verifier",
    ]
    assert len(job["provider_usage"]) == 5
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(NodeModel)) == 15
        assert await session.scalar(select(func.count()).select_from(RelationshipModel)) == 25


async def test_bad_citations_cannot_be_supported_even_if_model_would_agree(factory):
    identifier, workflow, provider, _, tx = await prepare(
        factory, FakeInference(fabricated_quote=True)
    )
    state = await workflow.run(identifier, {})
    assert state["verified"] == 0
    assert provider.tasks == ["planning", "extraction"]
    async with tx() as archive:
        assert all(
            row["decision"] == "insufficient" and not row["evidence"]
            for row in await archive.findings(identifier)
        )


async def test_disputed_claims_remain_candidates(factory):
    identifier, workflow, _, _, tx = await prepare(factory, FakeInference(decision="disputed"))
    await workflow.run(identifier, {})
    async with tx() as archive:
        assert all(row["decision"] == "disputed" for row in await archive.findings(identifier))


async def test_findings_api_serializes_completed_evidence_without_a_model_call(factory, app):
    identifier, workflow, provider, _, _ = await prepare(factory)
    await workflow.run(identifier, {})
    calls = len(provider.tasks)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/research/jobs/{identifier}/findings")
        assert response.status_code == 200
        findings = response.json()
        assert len(findings) == 3 and all(row["canonical"] is False for row in findings)
        assert findings[0]["evidence"][0]["content_hash"]
        assert findings[0]["evidence"][0]["retrieved_at"]
    assert len(provider.tasks) == calls


async def test_node_boundary_checkpoint_resume_does_not_repeat_finished_roles(factory):
    identifier, workflow, provider, _, tx = await prepare(factory)
    state = await workflow.planner({"job_id": str(identifier)})
    state = await workflow.researcher(state)
    state = await workflow.extractor(state)
    assert provider.tasks == ["planning", "extraction"]
    async with tx() as archive:
        saved = (await archive.get_job(identifier))["checkpoint"]
    await workflow.run(identifier, saved)
    assert provider.tasks == ["planning", "extraction"] + ["verification"] * 3
    async with tx() as archive:
        completed = (await archive.get_job(identifier))["checkpoint"]
    await workflow.run(identifier, completed)
    assert len(provider.tasks) == 5
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(ResearchClaimModel)) == 3


async def test_cancelled_job_runs_no_inference(factory):
    identifier, workflow, provider, _, tx = await prepare(factory)
    async with tx() as archive:
        await archive.update_job(identifier, cancel_requested=True)
    with pytest.raises(ResearchCancelled):
        await workflow.run(identifier, {})
    assert not provider.tasks


async def test_cancellation_cannot_resurrect_a_finished_job(factory):
    identifier, _, _, _, tx = await prepare(factory)
    async with tx() as archive:
        await archive.update_job(identifier, status="completed")
        assert not await archive.cancel_job(identifier)
        job = await archive.get_job(identifier)
        assert job["status"] == "completed" and not job["cancel_requested"]


async def test_search_query_and_iteration_limits_are_enforced(factory):
    search = FakeSearch()
    identifier, workflow, provider, fetcher, _ = await prepare(
        factory,
        FakeInference(fabricated_quote=True),
        search,
        sources=[],
        allow_search=True,
        max_iterations=2,
        max_queries=1,
        max_sources=1,
    )
    state = await workflow.run(identifier, {})
    assert state["iteration"] <= 2 and search.calls == 1 and fetcher.calls == 1
    assert len(state["source_ids"]) == 1


async def test_sources_and_identical_jobs_are_deduplicated(factory):
    identifier, workflow, _, _, tx = await prepare(factory)
    await workflow.run(identifier, {})
    async with tx() as archive:
        job = await archive.get_job(identifier)
        assert (
            await archive.create_job(ResearchRequest.model_validate(job["request"])) == identifier
        )
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(SourceDocumentModel)) == 1


async def test_research_api_queue_cancel_and_input_validation(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        graph = (await client.get("/api/universes/re-zero/graph")).json()
        payload = {
            "universe_id": graph["universe"]["id"],
            "continuity_id": graph["continuities"][0]["id"],
            "objective": "Research the source with explicit evidence.",
            "sources": [
                {
                    "text": TEXT,
                    "permission_basis": "Synthetic test source",
                    "source_scope": "Test-only continuity",
                }
            ],
        }
        response = await client.post("/api/research/jobs", json=payload)
        assert response.status_code == 202
        identifier = response.json()["id"]
        assert (await client.get(f"/api/research/jobs/{identifier}/findings")).json() == []
        assert (await client.post(f"/api/research/jobs/{identifier}/cancel")).json()[
            "status"
        ] == "cancelled"
        payload["sources"] = [
            {
                "url": "http://127.0.0.1/private",
                "permission_basis": "Synthetic test source",
                "source_scope": "Test-only continuity",
            }
        ]
        assert (await client.post("/api/research/jobs", json=payload)).status_code == 422
        payload["continuity_id"] = str(uuid4())
        payload["sources"] = [
            {
                "text": TEXT,
                "permission_basis": "Synthetic test source",
                "source_scope": "Test-only continuity",
            }
        ]
        assert (await client.post("/api/research/jobs", json=payload)).status_code == 404


def test_structured_outputs_reject_unknown_types_and_invented_passage_ids():
    with pytest.raises(ValueError):
        Extraction.model_validate(
            {
                "entities": [
                    {
                        "name": "Test",
                        "type": "UNKNOWN",
                        "description": "Synthetic description",
                        "evidence": [{"passage_id": "made-up", "quote": "Synthetic test quote"}],
                    }
                ]
            }
        )


async def test_import_reference_sections_and_source_groups_preserve_provenance(factory):
    source = SourceInput(
        text="Owned preface. " + TEXT + " Owned footer.",
        start_at="Mira entered",
        end_before="Owned footer.",
        reference_url="https://example.org/owned-story",
        source_group="owned-editorial-family",
        permission_basis="Owned synthetic fixture with attributed reference",
        source_scope="Test continuity",
    )
    identifier, workflow, _, fetcher, tx = await prepare(factory, sources=[source])
    state = await workflow.planner({"job_id": str(identifier)})
    state = await workflow.researcher(state)
    async with tx() as archive:
        passages = await archive.get_passages([UUID(value) for value in state["source_ids"]])
    assert passages[0].text == TEXT
    assert not state["public_only"] and fetcher.calls == 0
    async with factory() as session:
        document = await session.scalar(select(SourceDocumentModel))
        assert document.url.startswith("https://example.org/owned-story#")
        assert document.independence_key == "owned-editorial-family"
        assert document.public_web is False


def test_import_references_are_attribution_only_and_reject_active_url_schemes():
    with pytest.raises(ValueError):
        SourceInput(
            text=TEXT,
            reference_url="javascript:alert(1)",
            permission_basis="Owned test fixture",
            source_scope="Test continuity",
        )


async def test_terminal_retry_keeps_frozen_evidence_and_is_bounded(factory):
    from src.application.research_use_cases import ResearchRequestError, ResumeResearch

    identifier, workflow, _, _, tx = await prepare(factory)
    state = await workflow.run(identifier, {})
    async with tx() as archive:
        await archive.update_job(identifier, status="partial")
        await ResumeResearch(archive).execute(
            identifier, "identity_resolver", "Retry owned frozen extraction after a tested fix"
        )
        job = await archive.get_job(identifier)
        assert job["status"] == "queued" and job["checkpoint"]["stage"] == "extractor"
        assert job["checkpoint"]["candidates"] == state["candidates"]
        assert job["checkpoint"]["source_ids"] == state["source_ids"]
        with pytest.raises(ResearchRequestError, match="active"):
            await ResumeResearch(archive).execute(
                identifier, "identity_resolver", "An active job must not be requeued"
            )
        await archive.update_job(identifier, status="partial")
        await ResumeResearch(archive).execute(
            identifier, "verifier", "Second bounded retry of owned evidence"
        )
        await archive.update_job(identifier, status="partial")
        with pytest.raises(ResearchRequestError, match="budget"):
            await ResumeResearch(archive).execute(
                identifier, "verifier", "A third retry exceeds the allowed budget"
            )


async def test_explicit_refresh_creates_new_job_without_erasing_old_archive(factory):
    identifier, _, _, _, tx = await prepare(factory)
    async with tx() as archive:
        job = await archive.get_job(identifier)
        request = ResearchRequest.model_validate({**job["request"], "refresh": True})
        second = await archive.create_job(request)
        third = await archive.create_job(request)
        assert len({identifier, second, third}) == 3
        assert await archive.get_job(identifier)
