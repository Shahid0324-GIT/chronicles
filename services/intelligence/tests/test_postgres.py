"""Opt-in PostgreSQL migration/repository test; never reads normal DATABASE_URL."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.application.research import ResearchRequest, SourceInput
from src.domain.entities import now
from src.domain.research import SourceDocument, digest, passages_for
from src.infrastructure.persistence.models import ContinuityModel, NodeModel, RelationshipModel
from src.infrastructure.persistence.models.research import ClaimEvidenceModel
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.persistence.seed import seed
from src.main import create_app
from src.presentation.dependencies import get_session


@pytest.mark.postgres
async def test_postgres_migrations_seed_and_api():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to an explicit disposable database ending in _test")
    parsed = make_url(url)
    if parsed.drivername != "postgresql+asyncpg" or not (parsed.database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must use asyncpg and a disposable database ending in _test")
    schema = "atlas_test_" + uuid4().hex
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))

            def migrate(sync_connection):
                config.attributes["connection"] = sync_connection
                command.upgrade(config, "head")

            await connection.run_sync(migrate)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        for _ in range(2):
            async with factory() as session, session.begin():
                await seed(session)
        async with factory() as session:
            assert await session.scalar(select(func.count()).select_from(NodeModel)) == 15
            assert await session.scalar(select(func.count()).select_from(RelationshipModel)) == 25
        # Exercise the actual PostgreSQL archive and its composite evidence scope constraints.
        async with factory() as session, session.begin():
            archive = SqlResearchRepository(session)
            continuity = await session.scalar(select(ContinuityModel))
            document = SourceDocument(
                uuid4(),
                continuity.universe_id,
                continuity.id,
                "local:synthetic",
                "Synthetic migration test",
                "Test fixture",
                "A synthetic character entered the observatory.",
                digest("synthetic"),
                now(),
                "Owned synthetic test material",
                "Test continuity",
                False,
                False,
            )
            passages = passages_for(document)
            await archive.save_source(document, passages)
            identifier = await archive.create_job(
                ResearchRequest(
                    universe_id=continuity.universe_id,
                    continuity_id=continuity.id,
                    objective="Exercise PostgreSQL evidence storage with a synthetic fixture.",
                    sources=[
                        SourceInput(
                            text=document.text,
                            permission_basis=document.permission_basis,
                            source_scope=document.source_scope,
                        )
                    ],
                )
            )
            claim_id = uuid4()
            await archive.save_claim(
                identifier,
                {
                    "id": str(claim_id),
                    "kind": "entity",
                    "hash": digest("test claim"),
                    "payload": {"name": "Synthetic character"},
                },
                [
                    {
                        "passage_id": str(passages[0].id),
                        "quote": document.text,
                        "start": 0,
                        "end": len(document.text),
                    }
                ],
                "review",
                "Synthetic test only",
            )
            assert (await archive.findings(identifier))[0]["evidence"][0]["quote"] == document.text
            other_continuity = uuid4()
            session.add(
                ContinuityModel(
                    id=other_continuity,
                    universe_id=continuity.universe_id,
                    name="Separate synthetic adaptation",
                    medium="test",
                    description="Test only",
                )
            )
            await session.flush()
            with pytest.raises(IntegrityError):
                async with session.begin_nested():
                    session.add(
                        ClaimEvidenceModel(
                            claim_id=claim_id,
                            passage_id=passages[0].id,
                            universe_id=continuity.universe_id,
                            continuity_id=other_continuity,
                            quote=document.text,
                            quote_start=1,
                            quote_end=len(document.text),
                        )
                    )
                    await session.flush()
        app = create_app()

        async def isolated_session():
            async with factory() as session, session.begin():
                yield session

        app.dependency_overrides[get_session] = isolated_session
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/health")).status_code == 200
            graph = (await client.get("/api/universes/re-zero/graph")).json()
            assert len(graph["nodes"]) == 15
            assert len(graph["edges"]) == 25
        async with engine.begin() as connection:

            def downgrade(sync_connection):
                config.attributes["connection"] = sync_connection
                command.downgrade(config, "base")

            await connection.run_sync(downgrade)
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()
