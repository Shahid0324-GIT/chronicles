from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.application.ports.research import ResearchRepository
from src.application.research import ResearchRequest
from src.application.research_use_cases import CancelResearch, QueueResearch
from src.domain.exceptions import NotFoundError
from src.infrastructure.config.settings import Settings
from src.infrastructure.inference import create_inference
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.sources import PublicSourcePolicy
from src.presentation.api.schemas.research import EventResponse, FindingResponse, JobResponse
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
        stage=job["checkpoint"].get("stage", "queued"),
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
