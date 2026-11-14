import json
from datetime import timedelta
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.source_contracts import SourceEntry, SourceRegistration
from src.domain.entities import now
from src.domain.exceptions import DomainError, NotFoundError
from src.domain.research import digest
from src.infrastructure.persistence.models import ContinuityModel
from src.infrastructure.persistence.models.source_intelligence import SourceRegistryModel


class SqlSourceRegistry:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def entry(row: SourceRegistryModel) -> SourceEntry:
        return SourceEntry(
            **{k: v for k, v in row.configuration.items() if not k.startswith("_")},
            id=row.id,
            domain=row.domain,
            health=row.health,
            last_success=row.last_success,
            last_error=row.last_error,
            retry_at=row.configuration.get("_retry_at"),
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
        if entry.retrieval_policy == "permitted" and any(
            s.medium.casefold() not in {medium.casefold() for medium in entry.media} for s in scopes
        ):
            raise DomainError("Declared source media do not cover the requested continuities")
        p = urlsplit(entry.url)
        url = urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", p.query, ""))
        if entry.selectors:
            url += "#selection-" + digest(json.dumps(entry.selectors, sort_keys=True))[:16]
        elif entry.discovery_path_prefix or entry.discovery_api:
            url += (
                "#discovery-"
                + digest(json.dumps([entry.discovery_path_prefix, entry.discovery_api]))[:16]
            )
        if entry.eligible_section_terms:
            url += "#sections-" + digest(json.dumps(entry.eligible_section_terms))[:16]
        identifier = uuid5(entry.universe_id, "source-registry:" + url)
        row = await self.session.get(SourceRegistryModel, identifier)
        data = entry.model_copy(update={"url": url}).model_dump(mode="json")
        if row:
            row.configuration = {
                **data,
                **{k: v for k, v in row.configuration.items() if k.startswith("_")},
            }
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

    async def entries(self, universe: UUID, *, lock: bool = False) -> list[SourceEntry]:
        query = (
            select(SourceRegistryModel)
            .where(SourceRegistryModel.universe_id == universe)
            .order_by(SourceRegistryModel.id)
        )
        if lock:
            query = query.with_for_update()
        return [self.entry(r) for r in await self.session.scalars(query)]

    async def health(
        self, identifier: UUID, error: str | None, retry_after: float | None = None
    ) -> None:
        row = await self.session.get(SourceRegistryModel, identifier)
        if row:
            row.health, row.last_error = ("failed" if error else "healthy"), error
            if not error:
                row.last_success = now()
                row.configuration = {k: v for k, v in row.configuration.items() if k != "_retry_at"}
            elif error == "source_rate_limited":
                row.configuration = {
                    **row.configuration,
                    "_retry_at": (now() + timedelta(seconds=max(1, retry_after or 60))).isoformat(),
                }
            await self.session.flush()
