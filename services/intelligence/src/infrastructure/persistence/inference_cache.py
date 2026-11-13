from datetime import timedelta
from typing import Any

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import now
from src.infrastructure.persistence.models.source_intelligence import InferenceCacheModel


class SqlInferenceCache:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> dict[str, Any] | None:
        row = await self.session.get(InferenceCacheModel, key)
        if row and row.created_at.replace(tzinfo=now().tzinfo) > now() - timedelta(hours=24):
            return row.payload
        return None

    async def save(self, key: str, payload: dict[str, Any]) -> None:
        session = self.session
        insert = (
            pg_insert
            if session.bind and session.bind.dialect.name == "postgresql"
            else sqlite_insert
        )
        statement = insert(InferenceCacheModel).values(key=key, payload=payload, created_at=now())
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[InferenceCacheModel.key],
                set_={"payload": payload, "created_at": now()},
            )
        )
        await session.execute(
            delete(InferenceCacheModel).where(
                InferenceCacheModel.created_at < now() - timedelta(hours=24)
            )
        )
