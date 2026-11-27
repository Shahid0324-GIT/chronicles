"""One background job per guide. Saved as it goes, so a stopped one can be resumed."""

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal, Protocol

from pydantic import Field

from src.application.guide import Guide, Kind
from src.application.research_contracts import StructuredModel
from src.application.story_jobs import KEPT_MESSAGES, JobError, slug_of

logger = logging.getLogger(__name__)

KEY = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class GuideRequest(StructuredModel):
    kind: Kind
    story: str = Field(min_length=2, max_length=180)
    subject: str = Field(default="", max_length=120)
    wikipedia_title: str = Field(default="", max_length=250)
    # A Wikipedia page to start from, when the name alone does not find the story.
    link: str = Field(default="", pattern=r"^(https://(en|ja|zh)\.wikipedia\.org/wiki/\S+)?$")
    # The reader agreed to reading Wikipedia and sending its text to the cloud models.
    approved: bool


class GuideJob(StructuredModel):
    key: str = Field(pattern=KEY)
    request: GuideRequest
    title: str
    state: Literal["building", "ready", "failed", "interrupted"]
    messages: list[str] = Field(default_factory=list)
    error: str = ""
    updated: str = ""


class GuideStore(Protocol):
    def load(self, key: str) -> GuideJob | None: ...

    def save(self, job: GuideJob) -> None: ...

    def every(self) -> list[GuideJob]: ...

    def guide(self, key: str) -> Guide | None: ...

    def keep(self, key: str, guide: Guide) -> None: ...


class GuideMaker(Protocol):
    async def make(self, request: GuideRequest, report: Callable[[str], None]) -> Guide: ...


def guide_key(request: GuideRequest) -> str:
    """The same request always names the same guide."""
    parts = [request.kind, request.story, request.subject]
    wanted = json.dumps([p.strip().casefold() for p in parts], ensure_ascii=False)
    name = slug_of(f"{request.story} {request.subject or request.kind}")[:60].strip("-")
    return f"{name or request.kind}-{hashlib.sha256(wanted.encode()).hexdigest()[:8]}"


class GuideJobs:
    """Runs one guide at a time, so free model allowances are not spread thin."""

    def __init__(self, store: GuideStore, maker: GuideMaker) -> None:
        self.store, self.maker = store, maker
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.gate = asyncio.Lock()

    def get(self, key: str) -> GuideJob:
        job = self.store.load(key)
        if job is None:
            raise JobError("No page is recorded under that name")
        task = self.tasks.get(key)
        if job.state == "building" and (task is None or task.done()):
            # The application stopped while this was running.
            job = job.model_copy(update={"state": "interrupted"})
        return job

    def every(self) -> list[GuideJob]:
        return [self.get(job.key) for job in self.store.every()]

    def start(self, request: GuideRequest) -> GuideJob:
        if not request.approved:
            raise JobError("Approve reading Wikipedia and using the cloud models first")
        if request.kind != "summary" and not request.subject.strip():
            raise JobError("Name the arc or character")
        key = guide_key(request)
        if self.store.load(key) is not None:
            job = self.get(key)
            # A finished or running page is not paid for twice.
            if job.state in ("ready", "building"):
                return job
        title = request.subject.strip() or "Summary and cast"
        return self._launch(GuideJob(key=key, request=request, title=title, state="building"))

    def resume(self, key: str) -> GuideJob:
        job = self.get(key)
        if job.state not in ("failed", "interrupted"):
            raise JobError("Only a stopped page can be resumed")
        return self._launch(job.model_copy(update={"state": "building", "error": ""}))

    def _save(self, job: GuideJob) -> GuideJob:
        job = job.model_copy(update={"updated": datetime.now(UTC).isoformat()})
        self.store.save(job)
        return job

    def _launch(self, job: GuideJob) -> GuideJob:
        job = self._save(job)
        self.tasks[job.key] = asyncio.get_running_loop().create_task(self._run(job))
        return job

    async def _run(self, job: GuideJob) -> None:
        def report(message: str) -> None:
            nonlocal job
            messages = [*job.messages, message.strip()[:300]][-KEPT_MESSAGES:]
            job = self._save(job.model_copy(update={"messages": messages}))

        try:
            if self.gate.locked():
                report("Waiting for another page to finish")
            async with self.gate:
                self.store.keep(job.key, await self.maker.make(job.request, report))
                job = self._save(job.model_copy(update={"state": "ready"}))
        except Exception as error:
            logger.warning("Guide build failed for %s", job.key, exc_info=error)
            # Only our own short messages and codes are shown; never provider bodies.
            reason = str(error) if isinstance(error, ValueError) else ""
            code = getattr(error, "code", "") or type(error).__name__
            self._save(job.model_copy(update={"state": "failed", "error": (reason or code)[:300]}))
