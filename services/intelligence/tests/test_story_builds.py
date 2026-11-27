import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.scout import PagePlan, PlannedPage
from src.application.site_suggest import SiteIdeas, refusal, suggest_sites
from src.application.story_jobs import JobError, NewStory, StoryJobs, add_arc
from src.application.story_library import LibrarySite
from src.infrastructure.config.settings import Settings
from src.infrastructure.site_check import SiteReport, check_site
from src.infrastructure.story_builds import JobFiles, StoryBuilds
from src.infrastructure.story_library_files import StoryLibraryFiles
from src.main import create_app

SITE = LibrarySite(pages="https://wiki.example.org/")
LOCAL = {"X-Chronicles-Local": "1"}
STORY = {
    "story": "The Lantern Marsh",
    "arc": "The Search",
    "medium": "game",
    "site_url": "https://wiki.example.org/The_Search",
    "terms_confirmed": True,
    "cloud_allowed": True,
}


class Pipeline:
    """Finds three pages, then builds; can be told to fail once."""

    def __init__(self, files, fail=False):
        self.files, self.fail, self.built = files, fail, []

    async def find(self, world, arc, about, start, report):
        report("reading overview")
        pages = [
            PlannedPage(site=SITE.address, title=t, position=n)
            for n, t in enumerate(("Harbor", "Marsh", "Tower"), 1)
        ]
        folder = self.files.folder(world) / arc
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "pages.json").write_text(PagePlan(pages=pages).model_dump_json())

    async def build(self, world, arc, report):
        if self.fail:
            self.fail = False
            raise ValueError("The model allowance ran out")
        report("telling the story")
        self.built.append((world, arc))


def service(tmp_path, **options):
    files = StoryLibraryFiles(tmp_path)
    pipeline = Pipeline(files, **options)

    async def check(url):
        if "refused" in url:
            return SiteReport(False, "The site shows a bot check")
        return SiteReport(True, name="Wiki", page="The Search", site=SITE)

    return StoryBuilds(tmp_path, StoryJobs(JobFiles(files), pipeline), check), pipeline


async def settle(builds):
    await asyncio.gather(*builds.jobs.tasks.values())


async def test_a_new_story_pauses_for_page_review_then_builds(tmp_path):
    builds, pipeline = service(tmp_path)
    job = await builds.create(NewStory(**STORY))
    assert (job.world, job.arc, job.state) == ("the-lantern-marsh", "the-search", "finding")
    await settle(builds)
    assert builds.jobs.get(job.world, job.arc).state == "choose_pages"
    world = builds.files.world(job.world)
    assert world.position_word == "part" and world.sites[0].cloud_allowed
    with pytest.raises(JobError, match="at least three"):
        builds.confirm(job.world, job.arc, {"Harbor": 1})
    # Only listed pages can be kept; the reader may reorder them.
    builds.confirm(job.world, job.arc, {"Tower": 1, "Harbor": 2, "Marsh": 3, "Injected": 4})
    await settle(builds)
    done = builds.jobs.get(job.world, job.arc)
    assert done.state == "ready" and pipeline.built == [(job.world, job.arc)]
    assert [p.title for p in builds.pages(job.world, job.arc)] == ["Tower", "Harbor", "Marsh"]
    assert "telling the story" in done.messages
    with pytest.raises(JobError, match="already exists"):
        await builds.create(NewStory(**STORY))
    # A second arc joins the same story.
    await builds.create(NewStory(**{**STORY, "arc": "The Return"}))
    await settle(builds)
    assert [a.key for a in builds.files.world(job.world).arcs] == ["the-search", "the-return"]


async def test_a_stopped_build_resumes_where_it_was(tmp_path):
    builds, pipeline = service(tmp_path, fail=True)
    job = await builds.create(NewStory(**STORY))
    await settle(builds)
    builds.confirm(job.world, job.arc, {"Harbor": 1, "Marsh": 2, "Tower": 3})
    await settle(builds)
    failed = builds.jobs.get(job.world, job.arc)
    assert failed.state == "failed" and failed.error == "The model allowance ran out"
    builds.jobs.resume(job.world, job.arc)
    await settle(builds)
    assert builds.jobs.get(job.world, job.arc).state == "ready"
    # A job saved as running with nothing running it was interrupted.
    builds.jobs.store.save(failed.model_copy(update={"state": "building"}))
    builds.jobs.tasks.clear()
    assert builds.jobs.get(job.world, job.arc).state == "interrupted"


@pytest.mark.parametrize(
    "change",
    [{"terms_confirmed": False}, {"site_url": "https://refused.example.org/Page"}],
)
async def test_nothing_is_saved_without_permission_or_a_readable_site(tmp_path, change):
    builds, _ = service(tmp_path)
    with pytest.raises(JobError):
        await builds.create(NewStory(**{**STORY, **change}))
    assert list(tmp_path.iterdir()) == []


async def test_the_api_serves_the_flow_and_refuses_outside_callers(tmp_path):
    app = create_app(Settings(story_library_path=str(tmp_path)))
    app.state.builds, _ = service(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/api/builds", json=STORY)).status_code == 403
        created = await client.post("/api/builds", json=STORY, headers=LOCAL)
        assert created.status_code == 202
        await settle(app.state.builds)
        job = (await client.get("/api/builds/the-lantern-marsh/the-search")).json()
        assert job["state"] == "choose_pages" and len(job["pages"]) == 3
        assert job["slug"] == "the-lantern-marsh-draft"
        listed = (await client.get("/api/builds")).json()["jobs"]
        assert [j["arc"] for j in listed] == ["the-search"]
        again = await client.post("/api/builds", json=STORY, headers=LOCAL)
        assert again.status_code == 409 and "already exists" in again.text
        started = await client.post(
            "/api/builds/the-lantern-marsh/the-search/pages",
            json={"pages": job["pages"]},
            headers=LOCAL,
        )
        assert started.json()["state"] == "building"
        assert (await client.get("/api/builds/nowhere/nothing")).status_code == 404
        assert (await client.get("/api/builds/..%2F/x")).status_code in (404, 422)


def test_an_arc_cannot_change_the_story_medium():
    world, _ = add_arc(None, NewStory(**STORY), SITE)
    with pytest.raises(JobError, match="saved as a game"):
        add_arc(world, NewStory(**{**STORY, "arc": "Other", "medium": "anime"}), SITE)


async def test_suggestions_leave_out_refused_and_unsafe_sites():
    async def infer(prompt, schema, task):
        return SiteIdeas.model_validate(
            {
                "sites": [
                    {"name": "Fan", "url": "https://lantern.fandom.com/wiki/Search"},
                    {"name": "Plain", "url": "http://wiki.example.org/Search"},
                    {"name": "Wiki", "url": "https://wiki.example.org/Search"},
                    {"name": "Again", "url": "https://wiki.example.org/Other"},
                ]
            }
        )

    assert [i.name for i in await suggest_sites("Lantern", "Search", "", infer)] == ["Wiki"]
    assert "terms" in refusal("https://x.fandom.com/wiki/A")


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("http://wiki.example.org/Page", "https"),
        ("https://127.0.0.1/Page", "public"),
        ("https://a.fandom.com/wiki/Page", "terms"),
        ("https://wiki.example.org/", "front page"),
    ],
)
async def test_unusable_addresses_are_refused_before_any_request(url, reason):
    report = await check_site(url)
    assert not report.allowed and reason in report.reason
