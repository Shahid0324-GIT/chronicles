"""Build a story from the app: one background job per arc, paused for page review.

A job's state is saved as it goes, so the screen can follow it and a restart can resume
it. Finished model replies and saved pages are reused, so resuming repeats little work.
"""

import asyncio
import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal, Protocol

from pydantic import Field

from src.application.research_contracts import StructuredModel
from src.application.story_library import SLUG, LibraryArc, LibrarySite, LibraryWorld

logger = logging.getLogger(__name__)

JobState = Literal["finding", "choose_pages", "building", "ready", "failed", "interrupted"]
RUNNING = ("finding", "building")
KEPT_MESSAGES = 60
POSITION_WORDS = {
    "manga": "chapter",
    "novel": "chapter",
    "anime": "episode",
    "show": "episode",
    "game": "part",
}


class NewStory(StructuredModel):
    story: str = Field(min_length=2, max_length=180)
    arc: str = Field(min_length=2, max_length=100)
    about: str = Field(default="", max_length=400)
    medium: Literal["game", "manga", "anime", "novel", "show"]
    site_url: str = Field(pattern=r"^https://", max_length=1000)
    # Headings that hold this arc's story, when a page covers several stories.
    sections: list[str] = Field(default_factory=list, max_length=10)
    terms_confirmed: bool
    cloud_allowed: bool


class StoryJob(StructuredModel):
    world: str = Field(pattern=SLUG)
    arc: str = Field(pattern=SLUG)
    story: str
    title: str
    state: JobState
    about: str = ""
    start: str = ""
    # Set once the reader has confirmed the page list, so resuming goes on to build.
    pages_confirmed: bool = False
    messages: list[str] = Field(default_factory=list)
    error: str = ""
    updated: str = ""


class JobError(ValueError):
    """A request the current state of a job does not allow; safe to show the reader."""


class JobStore(Protocol):
    def load(self, world: str, arc: str) -> StoryJob | None: ...

    def save(self, job: StoryJob) -> None: ...

    def every(self) -> list[StoryJob]: ...


class ArcPipeline(Protocol):
    async def find(
        self, world: str, arc: str, about: str, start: str, report: Callable[[str], None]
    ) -> None: ...

    async def build(self, world: str, arc: str, report: Callable[[str], None]) -> None: ...


def slug_of(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:70].strip("-")


def add_arc(
    existing: LibraryWorld | None, request: NewStory, site: LibrarySite
) -> tuple[LibraryWorld, str]:
    """The world with this arc and its approved site added, keeping what it already had."""
    slug, key = slug_of(request.story), slug_of(request.arc)
    if not slug or not key:
        raise JobError("Use some letters or numbers in the story and arc names")
    arc = LibraryArc(key=key, title=request.arc.strip(), sections=request.sections)
    if existing is None:
        world = LibraryWorld(
            slug=slug,
            title=request.story.strip(),
            medium=request.medium,
            position_word=POSITION_WORDS[request.medium],
            arcs=[arc],
            sites=[site],
        )
        return world, key
    if existing.medium != request.medium:
        raise JobError(f"This story is already saved as a {existing.medium}")
    if any(a.key == key for a in existing.arcs):
        raise JobError("That arc already exists; open it or use another arc name")
    sites = [s for s in existing.sites if s.address != site.address]
    return (
        existing.model_copy(update={"arcs": [*existing.arcs, arc], "sites": [*sites, site]}),
        key,
    )


class StoryJobs:
    """Runs one build at a time, so free model allowances are not spread thin."""

    def __init__(self, store: JobStore, pipeline: ArcPipeline) -> None:
        self.store, self.pipeline = store, pipeline
        self.tasks: dict[tuple[str, str], asyncio.Task[None]] = {}
        self.gate = asyncio.Lock()

    def get(self, world: str, arc: str) -> StoryJob:
        job = self.store.load(world, arc)
        if job is None:
            raise JobError("No build is recorded for that arc")
        task = self.tasks.get((world, arc))
        if job.state in RUNNING and (task is None or task.done()):
            # The application stopped while this was running.
            job = job.model_copy(update={"state": "interrupted"})
        return job

    def every(self) -> list[StoryJob]:
        return [self.get(job.world, job.arc) for job in self.store.every()]

    def start(self, job: StoryJob) -> StoryJob:
        return self._launch(job.model_copy(update={"state": "finding"}))

    def confirm(self, world: str, arc: str) -> StoryJob:
        job = self.get(world, arc)
        if job.state != "choose_pages":
            raise JobError("The page list is not waiting for review")
        return self._launch(job.model_copy(update={"state": "building", "pages_confirmed": True}))

    def resume(self, world: str, arc: str) -> StoryJob:
        job = self.get(world, arc)
        if job.state not in ("failed", "interrupted"):
            raise JobError("Only a stopped build can be resumed")
        state = "building" if job.pages_confirmed else "finding"
        return self._launch(job.model_copy(update={"state": state, "error": ""}))

    def _save(self, job: StoryJob) -> StoryJob:
        job = job.model_copy(update={"updated": datetime.now(UTC).isoformat()})
        self.store.save(job)
        return job

    def _launch(self, job: StoryJob) -> StoryJob:
        job = self._save(job)
        self.tasks[(job.world, job.arc)] = asyncio.get_running_loop().create_task(self._run(job))
        return job

    async def _run(self, job: StoryJob) -> None:
        def report(message: str) -> None:
            nonlocal job
            messages = [*job.messages, message.strip()[:300]][-KEPT_MESSAGES:]
            job = self._save(job.model_copy(update={"messages": messages}))

        try:
            if self.gate.locked():
                report("Waiting for another build to finish")
            async with self.gate:
                if job.state == "finding":
                    await self.pipeline.find(job.world, job.arc, job.about, job.start, report)
                    job = self._save(job.model_copy(update={"state": "choose_pages"}))
                else:
                    await self.pipeline.build(job.world, job.arc, report)
                    job = self._save(job.model_copy(update={"state": "ready"}))
        except Exception as error:
            logger.warning("Story build failed for %s/%s", job.world, job.arc, exc_info=error)
            # Only our own short messages and codes are shown; never provider bodies.
            reason = str(error) if isinstance(error, ValueError) else ""
            code = getattr(error, "code", "") or type(error).__name__
            self._save(job.model_copy(update={"state": "failed", "error": (reason or code)[:300]}))
