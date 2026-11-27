"""The new-story screen's local API.

Writes need the ``X-Chronicles-Local`` header. Browsers will not send a custom header
across origins without permission, which is not granted, so another website cannot
start builds that spend your model allowance.
"""

from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request
from pydantic import Field

from src.application.research_contracts import InferenceFailure, StructuredModel
from src.application.story_jobs import JobError, NewStory, StoryJob
from src.application.story_library import SLUG
from src.infrastructure.story_builds import StoryBuilds

router = APIRouter(prefix="/api/builds", tags=["builds"])
Slug = Annotated[str, Path(pattern=SLUG, max_length=90)]


class Idea(StructuredModel):
    story: str = Field(min_length=2, max_length=180)
    arc: str = Field(min_length=2, max_length=100)
    about: str = Field(default="", max_length=400)


class Address(StructuredModel):
    url: str = Field(min_length=10, max_length=1000)


class ChosenPage(StructuredModel):
    title: str = Field(min_length=1, max_length=250)
    position: int = Field(ge=1, le=100000)


class Chosen(StructuredModel):
    pages: list[ChosenPage] = Field(min_length=1, max_length=80)


def builds(request: Request) -> StoryBuilds:
    service: StoryBuilds = request.app.state.builds
    return service


def local(x_chronicles_local: Annotated[str | None, Header()] = None) -> None:
    if x_chronicles_local != "1":
        raise HTTPException(403, "This request must come from the local app")


Service = Annotated[StoryBuilds, Depends(builds)]
Local = Depends(local)


def _job(service: StoryBuilds, job: StoryJob) -> dict[str, Any]:
    pages = service.pages(job.world, job.arc) if job.state == "choose_pages" else []
    return {
        **job.model_dump(mode="json"),
        "slug": f"{job.world}-draft",
        "pages": [{"title": p.title, "position": p.position} for p in pages],
    }


@router.post("/sites/suggest", dependencies=[Local])
async def suggest(idea: Idea, service: Service) -> dict[str, Any]:
    try:
        ideas = await service.suggest(idea.story, idea.arc, idea.about)
    except InferenceFailure as error:
        raise HTTPException(503, f"No suggestion right now ({error.code})") from None
    return {"sites": [i.model_dump() for i in ideas]}


@router.post("/sites/check", dependencies=[Local])
async def check(address: Address, service: Service) -> dict[str, Any]:
    report = await service.check(address.url)
    found = asdict(report)
    found.pop("site")
    return found


@router.get("")
async def every(service: Service) -> dict[str, Any]:
    return {"jobs": [_job(service, job) for job in service.jobs.every()]}


@router.get("/{world}/{arc}")
async def one(world: Slug, arc: Slug, service: Service) -> dict[str, Any]:
    try:
        return _job(service, service.jobs.get(world, arc))
    except JobError as error:
        raise HTTPException(404, str(error)) from None


@router.post("", dependencies=[Local], status_code=202)
async def create(story: NewStory, service: Service) -> dict[str, Any]:
    try:
        return _job(service, await service.create(story))
    except JobError as error:
        raise HTTPException(409, str(error)) from None


@router.post("/{world}/{arc}/pages", dependencies=[Local], status_code=202)
async def confirm(world: Slug, arc: Slug, chosen: Chosen, service: Service) -> dict[str, Any]:
    try:
        job = service.confirm(world, arc, {p.title: p.position for p in chosen.pages})
    except JobError as error:
        raise HTTPException(409, str(error)) from None
    return _job(service, job)


@router.post("/{world}/{arc}/resume", dependencies=[Local], status_code=202)
async def resume(world: Slug, arc: Slug, service: Service) -> dict[str, Any]:
    try:
        return _job(service, service.jobs.resume(world, arc))
    except JobError as error:
        raise HTTPException(409, str(error)) from None
