"""Actual pgvector SQL execution, owned text and fake embeddings; no external inference."""

import pytest
from sqlalchemy import func, select

from src.infrastructure.persistence.models.source_intelligence import PassageEmbeddingModel

from .test_promotion_postgres import postgres_factory  # noqa: F401
from .test_source_intelligence import prepare_index


@pytest.mark.postgres
async def test_real_pgvector_index_retrieval_and_dimension_isolation(postgres_factory):  # noqa: F811
    scope, ids, service, embedding = await prepare_index(postgres_factory)
    assert (await service.index(scope.universe_id, scope.id))["indexed"] == 2
    results = await service.retrieve(scope.universe_id, scope.id, "arrival", names=["Mira Vale"])
    assert results[0].source.id == ids[0]
    async with postgres_factory() as session:
        assert set(
            await session.scalars(select(func.vector_dims(PassageEmbeddingModel.vector)))
        ) == {3}
    assert (await service.index(scope.universe_id, scope.id))["indexed"] == 0
    embedding.revision = "other-version"
    assert (await service.index(scope.universe_id, scope.id))["indexed"] == 2
