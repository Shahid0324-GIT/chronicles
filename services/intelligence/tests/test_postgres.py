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
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.infrastructure.persistence.models import NodeModel, RelationshipModel
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
            assert await session.scalar(select(func.count()).select_from(NodeModel)) == 10
            assert await session.scalar(select(func.count()).select_from(RelationshipModel)) == 12
        app = create_app()

        async def isolated_session():
            async with factory() as session, session.begin():
                yield session

        app.dependency_overrides[get_session] = isolated_session
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/health")).status_code == 200
            graph = (await client.get("/api/universes/re-zero/graph")).json()
            assert len(graph["nodes"]) == 10
            assert len(graph["edges"]) == 12
        async with engine.begin() as connection:

            def downgrade(sync_connection):
                config.attributes["connection"] = sync_connection
                command.downgrade(config, "base")

            await connection.run_sync(downgrade)
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()
