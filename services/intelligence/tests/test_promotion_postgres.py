"""Real PostgreSQL concurrency using owned synthetic fixtures and no inference/network calls."""

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.infrastructure.persistence.models import NodeModel, RelationshipModel
from src.infrastructure.persistence.seed import seed

from .test_knowledge import prepared


@pytest.fixture
async def postgres_factory():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires explicit disposable TEST_DATABASE_URL ending in _test")
    parsed = make_url(url)
    if parsed.drivername != "postgresql+asyncpg" or not (parsed.database or "").endswith("_test"):
        pytest.fail("Only explicit asyncpg _test databases are allowed")
    schema = "knowledge_test_" + uuid4().hex
    engine = create_async_engine(
        url, connect_args={"server_settings": {"search_path": schema + ",public"}}
    )
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))

            def upgrade(sync):
                config.attributes["connection"] = sync
                command.upgrade(config, "head")

            await connection.run_sync(upgrade)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session, session.begin():
            await seed(session)
        yield factory
        async with engine.begin() as connection:

            def downgrade(sync):
                config.attributes["connection"] = sync
                command.downgrade(config, "base")

            await connection.run_sync(downgrade)
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


@pytest.mark.postgres
async def test_concurrent_same_job_promotion_is_atomic_and_idempotent(postgres_factory):
    job, service, tx, _, resolutions = await prepared(postgres_factory)
    results = await asyncio.gather(
        *[service.publish(job, resolutions, {}, False) for _ in range(3)]
    )
    assert all(len(r["promoted"]) == 3 for r in results)
    async with tx() as unit:
        assert len(await unit.graph.records(job)) == 3
    async with postgres_factory() as session:
        assert await session.scalar(select(func.count()).select_from(NodeModel)) == 17
        assert await session.scalar(select(func.count()).select_from(RelationshipModel)) == 26


@pytest.mark.postgres
async def test_different_jobs_cannot_publish_duplicate_stale_new_identity_proposals(
    postgres_factory,
):
    job1, service1, _, _, resolutions1 = await prepared(postgres_factory, label="First request")
    job2, service2, tx, _, resolutions2 = await prepared(postgres_factory, label="Second request")
    assert job1 != job2
    results = await asyncio.gather(
        service1.publish(job1, resolutions1, {}, False),
        service2.publish(job2, resolutions2, {}, False),
    )
    assert sorted(len(r["promoted"]) for r in results) == [0, 3]
    async with postgres_factory() as session:
        assert await session.scalar(select(func.count()).select_from(NodeModel)) == 17
        assert await session.scalar(select(func.count()).select_from(RelationshipModel)) == 26


@pytest.mark.postgres
async def test_shared_support_survives_one_retraction_then_cleans_up_after_last(postgres_factory):
    job1, service, tx, claims1, resolutions1 = await prepared(
        postgres_factory, label="First evidence"
    )
    await service.publish(job1, resolutions1, {}, False)
    job2, service2, _, claims2, resolutions2 = await prepared(
        postgres_factory, label="Second evidence"
    )
    for c1, c2 in zip(claims1[:2], claims2[:2], strict=True):
        resolutions2[c2["id"]].update(
            decision="SAME_ENTITY",
            canonical_id=resolutions1[c1["id"]]["canonical_id"],
            proof="exact_scoped_name",
        )
    assert len((await service2.publish(job2, resolutions2, {}, False))["promoted"]) == 3
    await service.rollback_job(job1, "Withdraw only the first synthetic evidence claim.")
    async with postgres_factory() as session:
        assert await session.scalar(select(func.count()).select_from(NodeModel)) == 17
        assert await session.scalar(select(func.count()).select_from(RelationshipModel)) == 26
    await service2.rollback_job(job2, "Withdraw the final synthetic evidence claim.")
    async with postgres_factory() as session:
        assert await session.scalar(select(func.count()).select_from(NodeModel)) == 15
        assert await session.scalar(select(func.count()).select_from(RelationshipModel)) == 25
