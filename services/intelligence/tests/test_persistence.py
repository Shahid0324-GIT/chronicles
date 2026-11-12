from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.infrastructure.persistence.models import NodeModel, RelationshipModel, UniverseModel
from src.infrastructure.persistence.seed import seed


async def test_seed_is_idempotent_and_preserves_edits(factory):
    async with factory() as session, session.begin():
        row = await session.scalar(select(NodeModel).limit(1))
        row.title = "User-edited title"
    async with factory() as session, session.begin():
        await seed(session)
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(UniverseModel)) == 1
        assert await session.scalar(select(func.count()).select_from(NodeModel)) == 10
        assert await session.scalar(select(func.count()).select_from(RelationshipModel)) == 12
        assert await session.scalar(select(NodeModel).where(NodeModel.title == "User-edited title"))


async def test_database_rejects_cross_universe_edge(factory):
    async with factory() as session:
        edge = await session.scalar(select(RelationshipModel).limit(1))
        universe = await session.scalar(select(UniverseModel).limit(1))
        other_universe = UniverseModel(
            id=uuid4(),
            slug="other",
            title="Other",
            description="",
            created_at=universe.created_at,
            updated_at=universe.updated_at,
        )
        session.add(other_universe)
        await session.flush()
        other_node = NodeModel(
            id=uuid4(),
            universe_id=other_universe.id,
            continuity_id=None,
            type="CHARACTER",
            title="Other node",
            summary="",
            node_metadata={},
            created_at=universe.created_at,
            updated_at=universe.updated_at,
        )
        session.add(other_node)
        await session.flush()
        # Both endpoint and universe rows exist; the composite ownership key must reject this.
        edge.target_node_id = other_node.id
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


async def test_transaction_rolls_back_failed_work(factory):
    async with factory() as session:
        with pytest.raises(RuntimeError):
            async with session.begin():
                row = await session.scalar(select(NodeModel).limit(1))
                row.title = "Rolled back title"
                await session.flush()
                raise RuntimeError("abort")
        assert not await session.scalar(
            select(NodeModel).where(NodeModel.title == "Rolled back title")
        )
