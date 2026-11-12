from collections.abc import AsyncIterator

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.persistence.models import Base
from src.infrastructure.persistence.seed import seed
from src.main import create_app
from src.presentation.dependencies import get_session


@pytest.fixture
async def factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    # This fixture never reads DATABASE_URL and never uses a developer database.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session, session.begin():
        await seed(session)
    yield factory
    await engine.dispose()


@pytest.fixture
async def app(factory):
    app = create_app()

    async def isolated_session():
        async with factory() as session, session.begin():
            yield session

    app.dependency_overrides[get_session] = isolated_session
    yield app
    app.dependency_overrides.clear()
