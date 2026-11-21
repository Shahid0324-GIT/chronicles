"""Owned archive fixtures and injected inference; these are not autonomous research."""

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import select

from src.application.inference import InferenceRouter
from src.application.knowledge_contracts import SectionVerification
from src.application.research import ResearchRequest, SourceInput
from src.application.research_contracts import InferenceResult, InferenceUsage
from src.domain.entities import now
from src.domain.research import SourceDocument, digest, passages_for
from src.infrastructure.persistence.models import ContinuityModel
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.orchestration.research_workflow import ResearchWorkflow


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
