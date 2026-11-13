from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


class LocalModelLease:
    """Serialize local GPU work across the API and worker without an archive transaction."""

    namespace = 0x4348524F
    resource = 0x4D4F444C

    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        engine = factory.kw.get("bind")
        if not isinstance(engine, AsyncEngine):
            raise ValueError("Local model coordination needs the application's async engine")
        self.engine = engine

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[None]:
        if self.engine.dialect.name != "postgresql":
            raise ValueError("Cross-process local model coordination requires PostgreSQL")
        async with self.engine.connect() as connection:
            connection = await connection.execution_options(isolation_level="AUTOCOMMIT")
            values = {"namespace": self.namespace, "resource": self.resource}
            try:
                await connection.execute(
                    text("SELECT pg_advisory_lock(:namespace,:resource)"), values
                )
                yield
            finally:
                try:
                    await connection.execute(
                        text("SELECT pg_advisory_unlock(:namespace,:resource)"), values
                    )
                except SQLAlchemyError:
                    # Discard a broken pooled session rather than leaving an owned lock behind.
                    await connection.invalidate()
