"""Owned fixtures/fake providers. Never live research evidence."""

from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from src.application.evidence_dossier import EvidenceDossierBuilder, expand_queries, token_estimate
from src.application.research import ResearchRequest, SourceInput
from src.application.research_contracts import InferenceFailure
from src.application.research_frontier import ResearchFrontierService
from src.application.research_policy import ResearchPolicy, UniverseResearchProfile
from src.application.source_contracts import SourceDiscovery, SourceEntry
from src.application.source_intelligence import SourceDiscoveryService, SourceSelector
from src.infrastructure.inference import LangChainProvider
from src.infrastructure.persistence.models import ContinuityModel
from src.infrastructure.persistence.research_memory import SqlResearchMemory
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.persistence.source_registry import SqlSourceRegistry
from src.infrastructure.research_runtime import memory_transactions
from src.orchestration.research_workflow import ResearchWorkflow


async def scope_of(factory):
    async with factory() as session:
        return await session.scalar(select(ContinuityModel))


async def test_frontier_survives_jobs_deduplicates_and_fences_boundaries(factory):
    scope = await scope_of(factory)
    service = ResearchFrontierService(memory_transactions(factory))
    args = (
        scope.universe_id,
        scope.id,
        1,
        "Mira's opening story",
        ["Who is Mira?"],
        "planner",
        ResearchPolicy(),
    )
    first = await service.discover(*args)
    repeated = await service.discover(*args)
    assert first[0].id == repeated[0].id
    async with service.transactions() as memory:
        lead = first[0].model_copy(update={"status": "PARTIALLY_RESOLVED", "attempt_count": 1})
        await memory.save_lead(lead)
    assert (await service.discover(*args))[0].attempt_count == 1
    bounded = await service.discover(
        scope.universe_id, scope.id, 2, args[3], args[4], "later", args[-1]
    )
    assert bounded[0].id != first[0].id
    assert len(await service.discover(*args, depth=9)) == 1


async def test_profile_does_not_grant_source_access_and_validates_continuity(factory):
    scope = await scope_of(factory)
    profile = UniverseResearchProfile(
        universe_id=scope.universe_id,
        original_medium="light-novel",
        continuity_media={scope.id: "anime"},
        authorized_sites=["example.org"],
    )
    async with factory() as session, session.begin():
        memory = SqlResearchMemory(session)
        await memory.save_profile(profile)
        assert (await memory.profile(scope.universe_id)).original_medium == "light-novel"
    async with factory() as session, session.begin():
        with pytest.raises(Exception, match="continuity"):
            await SqlResearchMemory(session).save_profile(
                profile.model_copy(update={"continuity_media": {uuid4(): "anime"}})
            )


def entry(universe, continuity, **changes):
    return SourceEntry(
        id=uuid4(),
        universe_id=universe,
        name="Owned character biography",
        url="https://owned.example/bio",
        domain="owned.example",
        category="character-profile",
        media=["anime"],
        continuity_ids=[continuity],
        access_method="html",
        authority="primary",
        permission_basis="Owned synthetic test source",
        attribution="Owned test",
        retrieval_policy="permitted",
        health="unknown",
        last_success=None,
        last_error=None,
        **changes,
    )


def test_ranking_respects_medium_scope_permission_and_source_diversity():
    universe, continuity = uuid4(), uuid4()
    bio = entry(universe, continuity, topics=["Mira background"])
    synopsis = bio.model_copy(
        update={"id": uuid4(), "name": "Episode guide", "category": "episode-guide", "topics": []}
    )
    blocked = bio.model_copy(
        update={"id": uuid4(), "retrieval_policy": "navigation-only", "discovery_priority": 100}
    )
    adaptation = bio.model_copy(update={"id": uuid4(), "continuity_ids": [uuid4()]})
    profile = UniverseResearchProfile(
        universe_id=universe,
        original_medium="light-novel",
        continuity_media={continuity: "anime"},
        source_priorities={"character-profile": 80},
    )
    ranked = SourceSelector().rank(
        [synopsis, blocked, bio, adaptation], str(continuity), "Mira background", universe, profile
    )
    assert [item[0].id for item in ranked] == [bio.id, synopsis.id]
    assert "retrieval-permitted" in ranked[0][2]


def test_queries_are_dynamic_diverse_and_bounded():
    values = expand_queries(
        "Mira biography",
        ["Mira biography", "Mira biography!", "Who is Mira's faction?"],
        ["ミラ"],
        ["character-profile", "book"],
        8,
    )
    assert len(values) <= 8 and values.count("Mira biography") == 1
    assert any("ミラ" in query for query in values)
    assert any("book" in query for query in values)
    assert expand_queries("Mira", [], [], [], 0) == []


async def test_discovery_keeps_searching_existing_registry_without_granting_ingestion(factory):
    scope = await scope_of(factory)

    @asynccontextmanager
    async def tx():
        async with factory() as session, session.begin():
            yield SqlSourceRegistry(session)

    class Search:
        calls = []

        async def search(self, query, limit):
            self.calls.append(query)
            return ["https://owned.example/novel-index"]

    search = Search()
    service = SourceDiscoveryService(search, tx)
    request = SourceDiscovery(
        universe_id=scope.universe_id, continuity_id=scope.id, universe_name="Owned universe"
    )
    first = await service.discover(request, queries=["Mira original chapter"], max_queries=1)
    second = await service.discover(request, queries=["Mira character records"], max_queries=1)
    assert len(search.calls) == 2
    assert first[0].retrieval_policy == second[0].retrieval_policy == "navigation-only"
    assert first[0].discovery_origin == "Mira original chapter"


def test_dossier_uses_relevance_and_token_budget_not_insertion_order():
    facts = [
        {
            "id": str(i),
            "target_id": str(i),
            "kind": "entity",
            "payload": {"description": desc},
            "sources": [],
        }
        for i, desc in enumerate(["Unrelated city", "Mira's biography and faction"])
    ]
    size = token_estimate(facts[1])
    selected = EvidenceDossierBuilder().select(facts, "Mira biography", size)
    assert [f["id"] for f in selected["facts"]] == ["1"]
    assert selected["estimated_tokens"] <= size and selected["omitted_facts"] == 1


async def test_budget_failure_retains_root_question_before_planner_inference(factory):
    scope = await scope_of(factory)

    @asynccontextmanager
    async def tx():
        async with factory() as session, session.begin():
            yield SqlResearchRepository(session)

    class BudgetFailure:
        usage = []

        async def generate(self, *args, **kwargs):
            raise InferenceFailure("job_model_budget_exhausted")

    class Fetcher:
        async def fetch(self, url):
            raise AssertionError("No fetch after budget exhaustion")

    command = ResearchRequest(
        universe_id=scope.universe_id,
        continuity_id=scope.id,
        objective="Research Mira's background",
        sources=[
            SourceInput(
                text="Mira is a fictional researcher at the observatory.",
                permission_basis="Owned synthetic test",
                source_scope="Owned continuity",
            )
        ],
    )
    async with tx() as archive:
        job = await archive.create_job(command)
    workflow = ResearchWorkflow(tx, BudgetFailure(), Fetcher(), memory=memory_transactions(factory))
    with pytest.raises(InferenceFailure, match="budget"):
        await workflow.run(job, {})
    async with memory_transactions(factory)() as memory:
        leads = await memory.leads(
            scope.universe_id, scope.id, ResearchFrontierService.boundary(None)
        )
    assert len(leads) == 1 and leads[0].question == command.objective
    assert leads[0].status == "DISCOVERED"


def test_focused_policy_controls_effort_not_successful_page_count():
    small = ResearchPolicy(max_documents=2)
    large = ResearchPolicy(max_documents=100, max_passes=10)
    assert small.required_facets == large.required_facets
    assert small.min_relevant_facts == large.min_relevant_facts
    with pytest.raises(ValidationError):
        ResearchPolicy(max_documents=0)


def test_groq_limit_uses_retry_and_exhausted_token_reset():
    with pytest.raises(InferenceFailure) as raised:
        LangChainProvider._check_status(
            429,
            {
                "retry-after": "2",
                "x-ratelimit-remaining-tokens": "0",
                "x-ratelimit-reset-tokens": "2m7.5s",
            },
        )
    assert raised.value.retry_after == 127.5


async def test_byte_reservations_account_for_success_and_retain_unknown_failures(monkeypatch):
    from src.application.research import SourceRejected
    from src.infrastructure.sources import PublicDocumentFetcher

    class Policy:
        def validate(self, url):
            return "https", "owned.example", 443, "/"

    fetcher = PublicDocumentFetcher(Policy(), 1024, 500)
    charged = 0

    async def reserve(amount):
        nonlocal charged
        charged += amount

    async def complete(reserved, actual):
        nonlocal charged
        charged -= reserved - actual

    fetcher.budget_requests(reserve, complete)
    monkeypatch.setattr("src.infrastructure.sources.pinned_request", lambda *_: (200, {}, b"owned"))
    await fetcher._request("https://owned.example/")
    assert charged == 5

    def failure(*_):
        raise SourceRejected("source_fetch_failed")

    monkeypatch.setattr("src.infrastructure.sources.pinned_request", failure)
    with pytest.raises(SourceRejected):
        await fetcher._request("https://owned.example/")
    assert charged == 5 + 1025


async def test_pre_call_budget_failure_does_not_claim_an_actual_model_call():
    from src.application.inference import InferenceRouter
    from src.application.research_contracts import ResearchPlan

    from .test_inference import Provider

    provider = Provider()
    router = InferenceRouter(provider, [])

    async def reject(*_):
        raise InferenceFailure("job_token_budget_exhausted")

    router.before_call = reject
    with pytest.raises(InferenceFailure, match="token_budget"):
        await router.generate("Owned", "Owned", ResearchPlan, "planning")
    assert provider.calls == 0 and router.total_used == 0


def test_focused_stop_conditions_use_coverage_and_preserve_partial_outcome():
    class Inference:
        usage = []

    workflow = ResearchWorkflow(None, Inference(), None)
    state = {
        "policy": ResearchPolicy(max_passes=2).model_dump(),
        "iteration": 1,
        "source_ranking": [{"id": "owned"}],
        "coverage": {"outcome": "PARTIAL_COVERAGE"},
    }
    assert workflow.after_verification(state) == "refine"
    assert workflow.after_verification({**state, "iteration": 2}) == "end"
    assert (
        workflow.after_verification(
            {**state, "coverage": {"outcome": "SUFFICIENT_FOR_PRESENTATION"}}
        )
        == "end"
    )


async def test_dossier_arc_synthesis_has_separate_cache_and_validated_reader_output():
    from .test_knowledge_presentation import FakeInference, fixture_knowledge, memory_atlas

    universe, continuity, knowledge = fixture_knowledge()
    atlas, saved = memory_atlas(knowledge)
    inference = FakeInference()
    await atlas.rebuild(universe, continuity, inference)
    old = len(saved)
    await atlas.rebuild(universe, continuity, inference, cohesive_arc=True)
    assert len(saved) == old + 1
    catalog = await atlas.catalog(universe, continuity)
    assert catalog["journeys"][0]["presentation"]["synthesis"]["method"] == "grounded-dossier-v1"
    calls = inference.calls
    await atlas.rebuild(universe, continuity, inference, cohesive_arc=True)
    assert inference.calls == calls
