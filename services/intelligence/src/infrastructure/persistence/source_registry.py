import json
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.source_contracts import SourceEntry, SourceRegistration
from src.domain.entities import now
from src.domain.exceptions import NotFoundError
from src.domain.research import digest
from src.infrastructure.persistence.models import ContinuityModel
from src.infrastructure.persistence.models.source_intelligence import SourceRegistryModel


class SqlSourceRegistry:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def entry(row: SourceRegistryModel) -> SourceEntry:
        return SourceEntry(
            **row.configuration,
            id=row.id,
            domain=row.domain,
            health=row.health,
            last_success=row.last_success,
            last_error=row.last_error,
        )

    async def register(self, entry: SourceRegistration) -> SourceEntry:
        scopes = list(
            await self.session.scalars(
                select(ContinuityModel).where(
                    ContinuityModel.id.in_(entry.continuity_ids),
                    ContinuityModel.universe_id == entry.universe_id,
                )
            )
        )
        if {s.id for s in scopes} != set(entry.continuity_ids):
            raise NotFoundError("Registry continuity does not belong to the universe")
        p = urlsplit(entry.url)
        url = urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", p.query, ""))
        if entry.selectors:
            url += "#selection-" + digest(json.dumps(entry.selectors, sort_keys=True))[:16]
        identifier = uuid5(entry.universe_id, "source-registry:" + url)
        row = await self.session.get(SourceRegistryModel, identifier)
        data = entry.model_copy(update={"url": url}).model_dump(mode="json")
        if row:
            row.configuration = data
        else:
            row = SourceRegistryModel(
                id=identifier,
                universe_id=entry.universe_id,
                url=url,
                domain=p.hostname or "",
                configuration=data,
                health="unknown",
                last_success=None,
                last_error=None,
            )
            self.session.add(row)
        await self.session.flush()
        return self.entry(row)

    async def entries(self, universe: UUID) -> list[SourceEntry]:
        return [
            self.entry(r)
            for r in await self.session.scalars(
                select(SourceRegistryModel)
                .where(SourceRegistryModel.universe_id == universe)
                .order_by(SourceRegistryModel.id)
            )
        ]

    async def health(self, identifier: UUID, error: str | None) -> None:
        row = await self.session.get(SourceRegistryModel, identifier)
        if row:
            row.health, row.last_error = ("failed" if error else "healthy"), error
            if not error:
                row.last_success = now()
            await self.session.flush()
