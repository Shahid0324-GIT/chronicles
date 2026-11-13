from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.application.knowledge_contracts import ResearchRetryRequest, RollbackRequest
from src.application.ports.knowledge import KnowledgeSession
from src.application.ports.research import ResearchRepository
from src.application.promotion import CanonicalGraphPromotionService
from src.application.research import ResearchRequest
from src.application.research_summary import research_summary
from src.application.research_use_cases import CancelResearch, QueueResearch, ResumeResearch
from src.domain.exceptions import NotFoundError
from src.domain.knowledge import PromotionPolicy
from src.infrastructure.config.settings import Settings
from src.infrastructure.inference import create_inference
from src.infrastructure.persistence.knowledge_repository import SqlKnowledgeRepository
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.sources import PublicSourcePolicy
from src.presentation.api.schemas.research import (
    AliasResponse,
    EventResponse,
    FindingResponse,
    JobResponse,
    KnowledgeResponse,
    PromotionResponse,
)
from src.presentation.dependencies import Session

router = APIRouter(prefix="/api")


def research_repository(session: Session) -> ResearchRepository:
    return SqlResearchRepository(session)


Archive = Annotated[ResearchRepository, Depends(research_repository)]


async def job_response(archive: ResearchRepository, job_id: UUID) -> JobResponse:
    job = await archive.get_job(job_id)
    if not job:
        raise NotFoundError("Research job not found")
    return JobResponse(
        **{key: job[key] for key in JobResponse.model_fields if key not in {"stage", "iteration"}},
        stage=job["checkpoint"].get("active_stage") or job["checkpoint"].get("stage", "queued"),
        iteration=job["checkpoint"].get("iteration", 0),
    )


@router.post("/research/jobs", response_model=JobResponse, status_code=202)
async def create_job(command: ResearchRequest, archive: Archive, request: Request) -> JobResponse:
    settings: Settings = request.app.state.settings
    use_case = QueueResearch(
        archive,
        PublicSourcePolicy(settings.research_allowed_hosts),
        settings.agent_max_sources,
        bool(settings.searxng_base_url),
    )
    return await job_response(archive, await use_case.execute(command))


@router.get("/research/jobs/{job_id}", response_model=JobResponse)
async def inspect_job(job_id: UUID, archive: Archive) -> JobResponse:
    return await job_response(archive, job_id)


@router.get("/research/jobs/{job_id}/summary")
async def inspect_summary(job_id: UUID, archive: Archive) -> dict[str, Any]:
    job = await archive.get_job(job_id)
    if not job:
        raise NotFoundError("Research job not found")
    return research_summary(job, await archive.findings(job_id))


@router.post("/research/jobs/{job_id}/retry", response_model=JobResponse, status_code=202)
async def retry_research(
    job_id: UUID, command: ResearchRetryRequest, archive: Archive
) -> JobResponse:
    await ResumeResearch(archive).execute(job_id, command.from_stage, command.reason)
    return await job_response(archive, job_id)


@router.get("/research/jobs/{job_id}/findings", response_model=list[FindingResponse])
async def findings(job_id: UUID, archive: Archive) -> list[dict[str, Any]]:
    await job_response(archive, job_id)
    return await archive.findings(job_id)


@router.get("/research/jobs/{job_id}/events", response_model=list[EventResponse])
async def events(job_id: UUID, archive: Archive) -> list[dict[str, Any]]:
    await job_response(archive, job_id)
    return await archive.events(job_id)


@router.post("/research/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel(job_id: UUID, archive: Archive) -> JobResponse:
    await CancelResearch(archive).execute(job_id)
    return await job_response(archive, job_id)


@router.get("/ai/providers/status")
async def provider_status(request: Request) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    inference = create_inference(settings)
    try:
        available = await inference.local.available()
    except Exception:
        available = False
    # No external health calls without the same explicit cloud permission boundary.
    return {
        **inference.status(),
        "ollama": {"available": available, "model": settings.ollama_chat_model},
        "groq": {
            "model": settings.groq_model,
            "credentials": [p.credential for p in inference.cloud],
            "probed": False,
        },
    }


@router.get("/research/jobs/{job_id}/knowledge", response_model=KnowledgeResponse)
async def inspect_knowledge(job_id: UUID, archive: Archive, session: Session) -> dict[str, Any]:
    await job_response(archive, job_id)
    graph = SqlKnowledgeRepository(session)
    decisions, records = await graph.decisions(job_id), await graph.records(job_id)
    return {
        "decisions": decisions,
        "promotions": records,
        "summary": {
            "active_promotions": sum(not r["reversed"] for r in records),
            "retractions": sum(r["reversed"] for r in records),
            "unresolved": sum(
                d.get("policy", {}).get("outcome") != "AUTO_PROMOTE" for d in decisions.values()
            ),
        },
    }


@router.get("/nodes/{node_id}/aliases", response_model=list[AliasResponse])
async def inspect_aliases(
    node_id: UUID, session: Session, allowed_source_id: Annotated[list[UUID] | None, Query()] = None
) -> list[dict[str, Any]]:
    graph = SqlKnowledgeRepository(session)
    if not await graph.node(node_id):
        raise NotFoundError("Node not found")
    # Hidden identity aliases are never exposed by this public inspection route.
    return await graph.aliases(node_id, allowed_source_id)


def promotion_service(session: Session, request: Request) -> CanonicalGraphPromotionService:
    @asynccontextmanager
    async def transaction() -> AsyncIterator[KnowledgeSession]:
        yield KnowledgeSession(SqlResearchRepository(session), SqlKnowledgeRepository(session))

    settings: Settings = request.app.state.settings
    return CanonicalGraphPromotionService(
        transaction,
        PromotionPolicy(settings.promotion_minimum_sources, settings.promotion_strong_sources),
    )


Promotion = Annotated[CanonicalGraphPromotionService, Depends(promotion_service)]


@router.post("/research/jobs/{job_id}/rollback", response_model=list[PromotionResponse])
async def rollback_knowledge(
    job_id: UUID, command: RollbackRequest, service: Promotion
) -> list[dict[str, Any]]:
    return await service.rollback_job(job_id, command.reason)


@router.post("/research/promotions/{promotion_id}/rollback", response_model=PromotionResponse)
async def rollback_one(
    promotion_id: UUID, command: RollbackRequest, service: Promotion
) -> dict[str, Any]:
    return await service.rollback_promotion(promotion_id, command.reason)
