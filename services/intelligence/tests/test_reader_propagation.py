"""Mandatory real HTTP/Next/browser propagation; inference and source text are OWNED FIXTURES.

No developer database, externally researched content or manual canonical/presentation inserts.
"""

import asyncio
import json
import os
import socket
import subprocess
from dataclasses import asdict
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
import pytest
import uvicorn
from playwright.async_api import async_playwright
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.application.encyclopedia_contracts import GroundingAssessment
from src.application.inference import InferenceRouter
from src.application.relationship_contracts import AtomicAssertion, InvestigationSubject
from src.application.research import ResearchRequest
from src.application.research_contracts import InferenceResult, InferenceUsage
from src.application.research_policy import ResearchPolicy, UniverseResearchProfile
from src.application.retrieval import EvidenceRetrieval
from src.application.story_scope import ArcResearchScope
from src.domain.entities import Continuity, Universe, now
from src.domain.research import SourceDocument, digest, passages_for
from src.domain.value_objects import Slug
from src.infrastructure.config.settings import Settings
from src.infrastructure.persistence.models import Base, ContinuityModel, UniverseModel
from src.infrastructure.persistence.models.research import ResearchJobModel
from src.infrastructure.persistence.research_memory import SqlResearchMemory
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.research_runtime import build_workflow, index_transactions
from src.main import create_app
from src.presentation.dependencies import get_session

from .test_relationship_workflow import TEXT, OwnedProvider
from .test_source_intelligence import FakeEmbeddings

UNIVERSE_ID = uuid5(NAMESPACE_URL, "chronicles:owned-world")
MANGA_ID = uuid5(UNIVERSE_ID, "original-manga")


async def configure(session):
    """An owned test world with one manga arc scope; it holds no story facts."""
    universe = Universe(
        id=UNIVERSE_ID,
        slug=Slug("owned-world"),
        title="Owned fixture world",
        description="Synthetic material used only by this test.",
    )
    session.add(UniverseModel(**{**asdict(universe), "slug": "owned-world"}))
    await session.flush()
    session.add(
        ContinuityModel(
            **asdict(
                Continuity(
                    id=MANGA_ID,
                    universe_id=UNIVERSE_ID,
                    name="Original manga",
                    medium="MANGA",
                    description="Owned synthetic continuity.",
                )
            )
        )
    )
    await session.flush()
    await SqlResearchMemory(session).save_profile(
        UniverseResearchProfile(
            universe_id=UNIVERSE_ID,
            original_medium="manga",
            continuity_media={MANGA_ID: "MANGA"},
            story_scopes=[
                ArcResearchScope(
                    slug="owned-arc",
                    title="Owned arc",
                    continuity_id=MANGA_ID,
                    first_position=1,
                    last_position=7,
                    references=["https://owned.example/arc"],
                )
            ],
        )
    )


def unused_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


class ReaderFixtureProvider(OwnedProvider):
    enriched = False

    async def generate(self, system, prompt, schema, task):
        if task not in {"presentation", "presentation_verification"}:
            result = await super().generate(system, prompt, schema, task)
            if schema.__name__ == "ConnectedAssertions" and self.enriched:
                data, _ = json.JSONDecoder().raw_decode(prompt[prompt.index("{") :])
                for sentence in data["sentences"]:
                    if "Mira helped Ron" in sentence["text"]:
                        result.value.assertions.append(
                            AtomicAssertion(
                                subject="Mira",
                                object="Ron",
                                predicate="helped",
                                sentence_ids=[sentence["id"]],
                            )
                        )
            return result
        data, _ = json.JSONDecoder().raw_decode(prompt[prompt.index("{") :])
        if schema is GroundingAssessment:
            value = GroundingAssessment(
                entailed=True,
                english=True,
                names_consistent=True,
                agency_and_tense_preserved=True,
                unsupported_relationships=False,
                reason="Owned deterministic grounding fixture; not live inference.",
            )
        else:
            actions = data["connected_actions"]
            facts = {f["id"]: f for f in data["facts"]}
            statements = [
                {
                    "text": data["evidence"][facts[a["fact_refs"][0]]["evidence_refs"][0]].rstrip(
                        "."
                    )
                    + ".",
                    "fact_ids": [a["fact_refs"][0]],
                }
                for a in actions
            ]
            if not statements:
                evidence = data["evidence"]
                statements = [
                    {"text": next(iter(evidence.values())), "fact_ids": [data["facts"][0]["id"]]}
                ]
            title = statements[0]["text"].rstrip(".")
            if data["resource"]["kind"] == "arc":
                title = "The partnership and training"
            value = schema.model_validate(
                {
                    "display_title": title,
                    "short_summary": statements[0]["text"],
                    "statements": statements[:4],
                }
            )
        return InferenceResult(
            value,
            InferenceUsage(
                self.name,
                self.model,
                self.credential,
                task,
                "ok",
                1,
                input_tokens=100,
                output_tokens=60,
            ),
        )


@pytest.fixture
async def reader_factory(tmp_path):
    # Chrome reads while the worker writes: use independent SQLite connections.
    # StaticPool in-memory SQLite permits one request to roll back another transaction.
    engine = create_async_engine("sqlite+aiosqlite:///" + (tmp_path / "reader.db").as_posix())

    @event.listens_for(engine.sync_engine, "connect")
    def configure_connection(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def test_new_research_reaches_next_provider_browser_and_enrichment(reader_factory, tmp_path):
    factory = reader_factory
    # All world, Mira and Ron content is synthetic and lives in isolated SQLite.
    async with factory() as session, session.begin():
        await configure(session)
    provider = ReaderFixtureProvider()
    workflow = build_workflow(
        Settings(_env_file=None), factory, InferenceRouter(provider, [], mode="local")
    )
    workflow.retrieval = EvidenceRetrieval(index_transactions(factory), FakeEmbeddings())
    workflow.memory = None

    async def investigate(text, phase):
        source = SourceDocument(
            uuid4(),
            UNIVERSE_ID,
            MANGA_ID,
            f"https://owned.example/propagation/{phase}",
            "Owned propagation fixture",
            "Owned",
            text,
            digest(text),
            now(),
            "Owned synthetic test material",
            "Synthetic manga chapter 1",
            True,
            False,
            "owned-publisher",
            {
                "authority": "primary",
                "language": "en",
                "position_basis": "manga-chapter",
                "presentation_position": 1,
            },
        )
        command = ResearchRequest(
            universe_id=UNIVERSE_ID,
            continuity_id=MANGA_ID,
            objective="Investigate the owned Mira and Ron partnership and connected actions.",
            relationship_subjects=[
                InvestigationSubject(name="Mira"),
                InvestigationSubject(name="Ron"),
            ],
            compose_presentations=True,
            spoiler_position=7,
            refresh=True,
            research_policy=ResearchPolicy(
                max_passes=1,
                investigation_bundle_limit=2,
                presentation_requires_coverage=False,
                max_model_calls=100,
            ),
        )
        async with factory() as session, session.begin():
            await SqlResearchRepository(session).save_source(source, passages_for(source))
            job = await SqlResearchRepository(session).create_job(command)
        state = await workflow.run(job, {})
        assert state["publication"]["promoted"], state
        assert state["narrative"]["generated"] or state["narrative"]["reused"], state
        return job

    api = create_app(Settings(_env_file=None))
    api.state.session_factory = factory

    async def session_override():
        async with factory() as session, session.begin():
            yield session

    api.dependency_overrides[get_session] = session_override
    api_port, web_port = unused_port(), unused_port()
    server = uvicorn.Server(
        uvicorn.Config(api, host="127.0.0.1", port=api_port, lifespan="off", log_level="error")
    )
    api_task = asyncio.create_task(server.serve())
    root = Path(__file__).resolve().parents[3]
    web = root / "apps" / "web"
    environment = {
        **os.environ,
        "API_BASE_URL": f"http://127.0.0.1:{api_port}",
        "CHRONICLES_BUILD_DIR": ".next-propagation",
        "NEXT_TELEMETRY_DISABLED": "1",
    }
    log = (tmp_path / "next.log").open("w")
    process = subprocess.Popen(
        [
            "node",
            str(web / "node_modules/next/dist/bin/next"),
            "dev",
            "--hostname",
            "127.0.0.1",
            "--port",
            str(web_port),
        ],
        cwd=web,
        env=environment,
        stdout=log,
        stderr=log,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        async with httpx.AsyncClient() as client:
            for _ in range(90):
                try:
                    response = await client.get(f"http://127.0.0.1:{web_port}", timeout=2)
                    if response.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(1)
            else:
                raise AssertionError((tmp_path / "next.log").read_text())
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(channel="chrome", headless=True)
            page = await browser.new_page(
                viewport={"width": 1920, "height": 1080}, base_url=f"http://127.0.0.1:{web_port}"
            )
            await page.goto(f"http://127.0.0.1:{web_port}")
            await page.get_by_role("status").filter(has_text="No verified story events").wait_for()
            screenshots = Path(
                os.environ.get("CHRONICLES_FIXTURE_EVIDENCE_DIR", tmp_path / "screenshots")
            )
            screenshots.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(screenshots / "fixture-before.png"))
            await investigate(TEXT, "first")
            await page.get_by_role("button", name="Research", exact=True).click()
            await page.get_by_role("button", name="Refresh story atlas", exact=True).click()
            await page.get_by_role("button", name="Close research").click()
            await (
                page.locator("p:visible")
                .filter(has_text="Mira and Ron became partners.")
                .first.wait_for()
            )
            response = await page.request.get(
                f"/api/atlas/universes/owned-world/narrative?continuity_id={MANGA_ID}&spoiler_position=7"
            )
            catalog = await response.json()
            assert catalog["coverage"]["validatedMilestones"] > 0
            assert catalog["journeys"][0]["ordering"]["basis"] == "manga-chapter"
            assert catalog["journeys"][0]["presentationState"]["status"] == "validated"
            selected_step = catalog["journeys"][0]["steps"][0]["id"]
            before_revision = catalog["revision"]
            await page.screenshot(path=str(screenshots / "fixture-after.png"))
            graph = await (await page.request.get("/api/atlas/universes/owned-world/graph")).json()
            mira = next(
                n for n in graph["nodes"] if n["type"] == "CHARACTER" and n["title"] == "Mira"
            )
            await page.get_by_label("Open encyclopedia entry").select_option(mira["id"])
            panel = page.get_by_role("complementary", name="Story information")
            await panel.get_by_text("Sources & evidence", exact=False).wait_for()
            await panel.locator(".context-threads button").first.click()
            await page.get_by_role("button", name="Return to journey", exact=False).click()
            assert (
                await page.get_by_role("progressbar", name="Journey progress").get_attribute(
                    "value"
                )
                == "1"
            )
            # New source-backed action must enrich current artifacts, not require hand edits.
            provider.enriched = True
            enrichment_job = await investigate("Mira helped Ron.", "enriched")
            await page.get_by_role("button", name="Research", exact=True).click()
            await page.get_by_role("button", name="Refresh story atlas", exact=True).click()
            await page.get_by_role("button", name="Close research").click()
            await page.locator("p:visible").filter(has_text="Mira helped Ron.").first.wait_for()
            async with factory() as session:
                stored = await session.get(ResearchJobModel, enrichment_job)
                assert stored.checkpoint["narrative"]["generated"] > 0
            response = await page.request.get(
                f"/api/atlas/universes/owned-world/narrative?continuity_id={MANGA_ID}&spoiler_position=7"
            )
            enriched = await response.json()
            assert enriched["coverage"]["acceptedEvents"] == 4
            assert enriched["journeys"][0]["steps"][0]["id"] == selected_step
            refreshed_graph = await (
                await page.request.get("/api/atlas/universes/owned-world/graph")
            ).json()
            assert len(refreshed_graph["nodes"]) == len(graph["nodes"]) + 1
            assert (
                next(n["id"] for n in refreshed_graph["nodes"] if n["title"] == "Mira")
                == mira["id"]
            )
            assert enriched["revision"] != before_revision
            assert enriched["coverage"]["acceptedEvents"] > catalog["coverage"]["acceptedEvents"]
            assert (
                enriched["coverage"]["validatedMilestones"]
                > catalog["coverage"]["validatedMilestones"]
            )
            await page.screenshot(path=str(screenshots / "fixture-enriched.png"))
            await browser.close()
    finally:
        process.terminate()
        await asyncio.to_thread(process.wait, 15)
        log.close()
        server.should_exit = True
        await api_task
