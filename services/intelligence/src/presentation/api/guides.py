"""Search and guide pages. Writes need the local header, as for story builds."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import Field

from src.application.guide_jobs import KEY, GuideJob, GuideRequest
from src.application.research_contracts import InferenceFailure, StructuredModel
from src.application.story_jobs import JobError
from src.infrastructure.guide_service import Guides
from src.presentation.api.builds import Local

router = APIRouter(prefix="/api/guides", tags=["guides"])
Key = Annotated[str, Path(pattern=KEY, max_length=90)]


class Query(StructuredModel):
    query: str = Field(min_length=2, max_length=300)


def guides(request: Request) -> Guides:
    service: Guides = request.app.state.guides
    return service


Service = Annotated[Guides, Depends(guides)]


def _job(job: GuideJob) -> dict[str, Any]:
    return {
        "key": job.key,
        "kind": job.request.kind,
        "story": job.request.story,
        "title": job.title,
        "state": job.state,
        "messages": job.messages,
        "error": job.error,
    }


@router.post("/understand", dependencies=[Local])
async def understand(search: Query, service: Service) -> dict[str, Any]:
    try:
        intent = await service.understand(search.query)
    except InferenceFailure as error:
        raise HTTPException(503, f"The search could not be read now ({error.code})") from None
    return intent.model_dump()


@router.get("")
async def every(service: Service) -> dict[str, Any]:
    return {"jobs": [_job(job) for job in service.jobs.every()]}


@router.get("/{key}")
async def one(key: Key, service: Service) -> dict[str, Any]:
    try:
        job = service.jobs.get(key)
    except JobError as error:
        raise HTTPException(404, str(error)) from None
    guide = service.files.guide(key) if job.state == "ready" else None
    return {"job": _job(job), "guide": guide.model_dump(mode="json") if guide else None}


@router.post("", dependencies=[Local], status_code=202)
async def create(wanted: GuideRequest, service: Service) -> dict[str, Any]:
    try:
        return _job(service.jobs.start(wanted))
    except JobError as error:
        raise HTTPException(409, str(error)) from None


@router.post("/{key}/resume", dependencies=[Local], status_code=202)
async def resume(key: Key, service: Service) -> dict[str, Any]:
    try:
        return _job(service.jobs.resume(key))
    except JobError as error:
        raise HTTPException(409, str(error)) from None
