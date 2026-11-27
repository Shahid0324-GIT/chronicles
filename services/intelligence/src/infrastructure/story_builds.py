"""Composes the new-story screen's operations over the file library."""

from collections.abc import Awaitable, Callable
from pathlib import Path

from src.application.scout import PagePlan, PlannedPage
from src.application.site_suggest import SiteIdea, suggest_sites
from src.application.story_jobs import (
    JobError,
    NewStory,
    StoryJob,
    StoryJobs,
    add_arc,
    slug_of,
)
from src.application.story_library import LibraryWorld
from src.infrastructure.site_check import SiteReport, check_site
from src.infrastructure.story_library_files import StoryLibraryFiles
from src.infrastructure.story_pipeline import (
    build_arc,
    fetch_pages,
    find_pages,
    load_world,
    model_calls,
)

DEEP_PAGES = 12


def default_library() -> Path:
    return Path(__file__).resolve().parents[4] / "library"


class JobFiles:
    """``<world>/<arc>/job.json``."""

    def __init__(self, files: StoryLibraryFiles) -> None:
        self.files = files

    def _path(self, world: str, arc: str) -> Path:
        return self.files.folder(world) / slug_of(arc) / "job.json"

    def load(self, world: str, arc: str) -> StoryJob | None:
        path = self._path(world, arc)
        if not path.is_file():
            return None
        return StoryJob.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, job: StoryJob) -> None:
        path = self._path(job.world, job.arc)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Replaced in one step, so the screen never reads half a file.
        draft = path.with_suffix(".tmp")
        draft.write_text(job.model_dump_json(indent=2), encoding="utf-8")
        draft.replace(path)

    def every(self) -> list[StoryJob]:
        jobs = [
            StoryJob.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self.files.root.glob("*/*/job.json")
        ]
        return sorted(jobs, key=lambda j: j.updated, reverse=True)


class LibraryPipeline:
    def __init__(self, files: StoryLibraryFiles) -> None:
        self.files = files

    async def find(
        self, world: str, arc: str, about: str, start: str, report: Callable[[str], None]
    ) -> None:
        await find_pages(self.files, world, arc, about, [start] if start else [], report)

    async def build(self, world: str, arc: str, report: Callable[[str], None]) -> None:
        await fetch_pages(self.files, world, arc, report)
        await build_arc(self.files, world, arc, [], DEEP_PAGES, report)
        await load_world(self.files, world, report)


class StoryBuilds:
    def __init__(
        self,
        root: Path,
        jobs: StoryJobs | None = None,
        check: Callable[[str], Awaitable[SiteReport]] = check_site,
    ) -> None:
        self.files = StoryLibraryFiles(root)
        self.jobs = jobs or StoryJobs(JobFiles(self.files), LibraryPipeline(self.files))
        self.check = check

    async def suggest(self, story: str, arc: str, about: str) -> list[SiteIdea]:
        # Only the names the reader typed are sent, and nothing fetched from any site.
        infer = model_calls(self.files.root / ".suggestions", True, lambda _message: None)
        return await suggest_sites(story, arc, about, infer)

    def _existing(self, slug: str) -> LibraryWorld | None:
        if not (self.files.folder(slug) / "world.json").is_file():
            return None
        return self.files.world(slug)

    async def create(self, request: NewStory) -> StoryJob:
        if not request.terms_confirmed:
            raise JobError("Confirm that the site's terms allow automated reading")
        # Checked again here: what the screen was told is not trusted.
        report = await self.check(request.site_url)
        if not report.allowed or report.site is None:
            raise JobError(report.reason or "That site cannot be read")
        slug = slug_of(request.story)
        if not slug:
            raise JobError("Use some letters or numbers in the story name")
        site = report.site.model_copy(update={"cloud_allowed": request.cloud_allowed})
        world, key = add_arc(self._existing(slug), request, site)
        folder = self.files.folder(world.slug)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "world.json").write_text(world.model_dump_json(indent=2), encoding="utf-8")
        return self.jobs.start(
            StoryJob(
                world=world.slug,
                arc=key,
                story=world.title,
                title=request.arc.strip(),
                state="finding",
                about=request.about,
                start=report.page,
            )
        )

    def _plan_path(self, world: str, arc: str) -> Path:
        return self.files.folder(world) / slug_of(arc) / "pages.json"

    def pages(self, world: str, arc: str) -> list[PlannedPage]:
        path = self._plan_path(world, arc)
        if not path.is_file():
            return []
        return PagePlan.model_validate_json(path.read_text(encoding="utf-8-sig")).pages

    def confirm(self, world: str, arc: str, chosen: dict[str, int]) -> StoryJob:
        """Keep the listed pages the reader chose, at the positions they gave."""
        if self.jobs.get(world, arc).state != "choose_pages":
            raise JobError("The page list is not waiting for review")
        kept = [
            page.model_copy(update={"position": chosen[page.title]})
            for page in self.pages(world, arc)
            if page.title in chosen
        ]
        if len(kept) < 3:
            raise JobError("Keep at least three pages, enough to tell the arc")
        saved = PagePlan.model_validate_json(
            self._plan_path(world, arc).read_text(encoding="utf-8-sig")
        )
        plan = saved.model_copy(update={"pages": sorted(kept, key=lambda p: (p.position, p.title))})
        self._plan_path(world, arc).write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        return self.jobs.confirm(world, arc)
