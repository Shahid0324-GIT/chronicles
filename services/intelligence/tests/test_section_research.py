"""Owned archive fixtures and injected inference; these are not autonomous research."""

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select

from src.application.arc_intelligence import ArcIntelligence
from src.application.inference import InferenceRouter
from src.application.knowledge_contracts import SectionVerification
from src.application.research import ResearchRequest, SourceInput
from src.application.research_budget import DeferredInference
from src.application.research_contracts import InferenceResult, InferenceUsage
from src.application.research_policy import ResearchPolicy
from src.domain.entities import now
from src.domain.research import SourceDocument, digest, passages_for
from src.infrastructure.persistence.models import ContinuityModel
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.orchestration.research_workflow import ResearchWorkflow
from src.research_worker import MAX_PROVIDER_DEFERRALS, defer_provider


async def prepared(factory, *, missing_focus=False):
    @asynccontextmanager
    async def transaction():
        async with factory() as session, session.begin():
            yield SqlResearchRepository(session)

    text = "Mira entered the observatory after lunch."
    async with factory() as session:
        continuity = await session.scalar(select(ContinuityModel))
    source = SourceDocument(
        uuid4(),
        continuity.universe_id,
        continuity.id,
        "local:owned-section",
        "Owned",
        "Owned",
        text,
        digest(text),
        now(),
        "Owned fixture permission",
        "Owned continuity",
        False,
        False,
    )
    passage = passages_for(source)[0]
    request = ResearchRequest(
        universe_id=continuity.universe_id,
        continuity_id=continuity.id,
        objective="Explain the supported arrival in this owned section",
        arc_id=uuid4(),
        arc_section_keys=["origin"],
        extraction_source_ids=[uuid4()] if missing_focus else [],
        sources=[
            SourceInput(
                text=text,
                permission_basis="Owned fixture permission",
                source_scope="Owned continuity",
            )
        ],
    )
    async with transaction() as archive:
        job = await archive.create_job(request)
        await archive.save_source(source, [passage])

    class Provider:
        name, model, credential = "fake", "owned", "test"

        async def available(self):
            return True

        async def generate(self, system, prompt, schema, task):
            assert schema is SectionVerification
            data = json.loads(prompt[prompt.index("{") :])
            claim = data["candidates"][0]
            assert claim["excerpts"][0]["quote"] == text
            value = schema(
                assessments=[
                    {
                        "claim_id": claim["claim_id"],
                        "decision": "supported",
                        "reason": "The owned source states the arrival and time",
                        "content_kind": "fictional-story",
                        "supporting_unit_ids": [0],
                        "entity_type_valid": True,
                        "continuity_matches": True,
                        "material_conflict": False,
                    }
                ]
            )
            return InferenceResult(value, InferenceUsage("fake", "owned", "test", task, "ok", 1))

    workflow = ResearchWorkflow(transaction, InferenceRouter(Provider(), [], mode="local"), None)

    async def empty_retrieval(state):
        return []

    workflow.selected_passages = empty_retrieval
    state = {
        "job_id": str(job),
        "source_ids": [str(source.id)],
        "context": {"continuity": "Owned"},
        "candidates": [
            {
                "id": str(uuid4()),
                "kind": "entity",
                "hash": "owned",
                "payload": {
                    "name": "Mira",
                    "type": "CHARACTER",
                    "description": text,
                    "evidence": [{"passage_id": str(passage.id), "quote": text}],
                },
            }
        ],
    }
    return workflow, state


async def test_acquired_exact_evidence_survives_an_empty_ranked_retrieval_window(factory):
    workflow, state = await prepared(factory)
    result = await workflow.verifier(state)
    assert result["verified"] == 1
    assert result["semantic_assessments"][state["candidates"][0]["id"]]["in_universe"] is True
    assert len(result["section_verification"]) == 1

    async def no_repeat(*args, **kwargs):
        raise AssertionError("Unchanged, valid section review should be reused")

    workflow.infer = no_repeat
    resumed = await workflow.verifier(result)
    assert resumed["verified"] == 1


async def test_extraction_focus_cannot_authorize_an_unacquired_source(factory):
    workflow, state = await prepared(factory, missing_focus=True)
    state["plan"] = {"queries": []}
    result = await workflow.extractor(state)
    assert not result["candidates"]
    assert "extraction_source_not_acquired" in result["errors"]


async def test_current_source_revocation_blocks_acquired_passage_reuse(factory):
    workflow, state = await prepared(factory)

    class Index:
        async def source_metadata(self, universe, continuity, sources):
            assert sources
            return {}

    @asynccontextmanager
    async def transaction():
        yield Index()

    workflow.retrieval = SimpleNamespace(transactions=transaction)
    result = await workflow.verifier(state)
    assert result["verified"] == 0


def test_story_research_questions_do_not_include_failed_plan_or_reviewer_diagnostics():
    scope = {"key": "opening", "title": "Opening", "questions": ["Who reached the harbor?"]}
    section = {
        "plan": scope,
        "coverage": {"gaps": ["Grounding batch has incomplete IDs?"]},
        "development_plan": {
            "factual": {"status": "passed"},
            "structural": {"status": "passed"},
            "relationship_review": {"issues": ["Was the reviewer unavailable?"]},
            "gaps": ["Why was the reviewer unavailable?"],
            "evidence_questions": ["Who opened the gate?", "Why did the visitors leave?"],
            "developments": [{"unresolved": ["Was the archive witness misattributed?"]}],
        },
    }
    dossier = {"sections": [section], "accepted_facts": [{"id": "archived"}]}
    assert ArcIntelligence.research_questions(dossier, ["opening"]) == [
        "Opening — Who opened the gate?",
        "Opening — Why did the visitors leave?",
    ]
    assert not ArcIntelligence.research_questions(dossier, ["another-section"])
    section["development_plan"]["structural"]["status"] = "unavailable"
    assert not ArcIntelligence.research_questions(dossier, ["opening"])
    section["development_plan"] = None
    assert not ArcIntelligence.research_questions(dossier, ["opening"])
    dossier["accepted_facts"] = []
    assert ArcIntelligence.research_questions(dossier, ["opening"]) == [
        "Opening — Who reached the harbor?"
    ]


def test_targeted_arc_research_reopens_only_when_essential_coverage_advances():
    workflow = ResearchWorkflow(None, SimpleNamespace(usage=[]), None, knowledge=object())
    state = {
        "stage": "promotion_policy",
        "policy": ResearchPolicy(max_passes=2).model_dump(),
        "iteration": 1,
        "search_allowed": True,
        "coverage": {"outcome": "SUFFICIENT_FOR_PRESENTATION"},
        "arc_research": {
            "targeted_online": True,
            "questions": ["What connected the rescue and departure?"],
            "essential_progress": True,
        },
    }
    assert workflow.resume_stage(state) == "planner"
    stalled = {**state, "arc_research": {**state["arc_research"], "essential_progress": False}}
    assert workflow.resume_stage(stalled) == "narrative_builder"
    assert workflow.resume_stage({**state, "iteration": 2}) == "narrative_builder"
    denied = {**state, "coverage": {"outcome": "BLOCKED_BY_SOURCE_ACCESS"}}
    assert workflow.resume_stage(denied) == "narrative_builder"


def test_whole_arc_online_request_enters_coverage_path_without_section_keys():
    request = ResearchRequest(
        universe_id=uuid4(),
        continuity_id=uuid4(),
        arc_id=uuid4(),
        objective="Research the complete owned arc",
        allow_search=True,
    )
    assert ResearchWorkflow.targeted_arc_research(request)
    assert not ResearchWorkflow.targeted_arc_research(
        request.model_copy(update={"allow_search": False})
    )


def test_provider_deferral_preserves_progress_and_active_allowance_with_bounded_attempts():
    checkpoint = {"stage": "extractor", "deadline_at": 750.0, "candidates": ["kept"]}
    failure = DeferredInference("review-1", 90, "rate_limited")
    for _ in range(MAX_PROVIDER_DEFERRALS):
        assert defer_provider(checkpoint, failure, 500.0)
    assert not defer_provider(checkpoint, failure, 500.0)
    assert checkpoint["provider_resume_at"] == 590.0
    assert checkpoint["active_seconds_remaining"] == 250.0
    assert checkpoint["candidates"] == ["kept"] and checkpoint["stage"] == "extractor"
    assert not defer_provider(checkpoint, DeferredInference("review-2", 3, "timeout"), 750.0)
