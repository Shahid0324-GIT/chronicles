"""Actual pgvector SQL execution, owned text and fake embeddings; no external inference."""

import asyncio

import pytest
from sqlalchemy import func, select, text

from src.infrastructure.model_runtime import LocalModelLease
from src.infrastructure.persistence.models.source_intelligence import (
    InferenceCacheModel,
    PassageEmbeddingModel,
)
from src.infrastructure.research_runtime import build_inference_cache

from .test_promotion_postgres import postgres_factory  # noqa: F401
from .test_source_intelligence import prepare_index


@pytest.mark.postgres
async def test_inference_cache_concurrent_writes_are_idempotent(postgres_factory):  # noqa: F811
    cache = build_inference_cache(postgres_factory)
    await asyncio.gather(
        cache.save("a" * 64, {"owned": True}), cache.save("a" * 64, {"owned": True})
    )
    assert await cache.get("a" * 64) == {"owned": True}
    async with postgres_factory() as session:
        assert await session.scalar(select(func.count()).select_from(InferenceCacheModel)) == 1


@pytest.mark.postgres
async def test_real_pgvector_index_retrieval_and_dimension_isolation(postgres_factory):  # noqa: F811
    scope, ids, service, embedding = await prepare_index(postgres_factory)
    assert (await service.index(scope.universe_id, scope.id))["indexed"] == 2
    results = await service.retrieve(scope.universe_id, scope.id, "arrival", names=["Mira Vale"])
    assert results[0].source.id == ids[0]
    assert type(results[0].distance) is float
    async with postgres_factory() as session:
        assert set(
            await session.scalars(select(func.vector_dims(PassageEmbeddingModel.vector)))
        ) == {3}
    assert (await service.index(scope.universe_id, scope.id))["indexed"] == 0
    embedding.revision = "other-version"
    assert (await service.index(scope.universe_id, scope.id))["indexed"] == 2


@pytest.mark.postgres
async def test_local_model_lease_coordinates_sessions_and_releases(postgres_factory):  # noqa: F811
    lease = LocalModelLease(postgres_factory)
    values = {"namespace": lease.namespace, "resource": lease.resource}
    async with lease():
        async with lease.engine.connect() as connection:
            assert not await connection.scalar(
                text("SELECT pg_try_advisory_lock(:namespace,:resource)"), values
            )
    async with lease.engine.connect() as connection:
        assert await connection.scalar(
            text("SELECT pg_try_advisory_lock(:namespace,:resource)"), values
        )
        await connection.execute(text("SELECT pg_advisory_unlock(:namespace,:resource)"), values)
