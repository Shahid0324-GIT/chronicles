from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.research_policy import ResearchLead, UniverseResearchProfile
from src.domain.entities import now
from src.domain.exceptions import NotFoundError
from src.infrastructure.persistence.models import ContinuityModel, UniverseModel
from src.infrastructure.persistence.models.source_intelligence import (
    ResearchLeadModel,
    ResearchProfileModel,
)


class SqlResearchMemory:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock(self, identifier: UUID) -> None:
        if self.session.bind and self.session.bind.dialect.name == "postgresql":
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": int.from_bytes(identifier.bytes[:8], "big", signed=True)},
            )

    async def profile(self, universe: UUID) -> UniverseResearchProfile | None:
        row = await self.session.get(ResearchProfileModel, universe)
        return UniverseResearchProfile.model_validate(row.configuration) if row else None

    async def save_profile(self, profile: UniverseResearchProfile) -> None:
        await self.lock(profile.universe_id)
        if not await self.session.get(UniverseModel, profile.universe_id):
            raise NotFoundError("Universe not found")
        scopes = await self.session.scalars(
            select(ContinuityModel).where(ContinuityModel.universe_id == profile.universe_id)
        )
        if set(profile.continuity_media) - {s.id for s in scopes}:
            raise NotFoundError("Profile continuity does not belong to universe")
        row = await self.session.get(ResearchProfileModel, profile.universe_id)
        if row is None:
            row = ResearchProfileModel(universe_id=profile.universe_id)
            self.session.add(row)
        row.configuration = profile.model_dump(mode="json")
        row.updated_at = now()
        await self.session.flush()

    async def leads(self, universe: UUID, continuity: UUID, boundary: str) -> list[ResearchLead]:
        rows = await self.session.scalars(
            select(ResearchLeadModel)
            .where(
                ResearchLeadModel.universe_id == universe,
                ResearchLeadModel.continuity_id == continuity,
                ResearchLeadModel.boundary_key == boundary,
            )
            .order_by(ResearchLeadModel.id)
        )
        return [ResearchLead.model_validate(r.payload) for r in rows]

    async def save_lead(self, lead: ResearchLead) -> ResearchLead:
        await self.lock(lead.continuity_id)
        scope = await self.session.get(ContinuityModel, lead.continuity_id)
        if not scope or scope.universe_id != lead.universe_id:
            raise NotFoundError("Lead continuity does not belong to universe")
        row = await self.session.get(ResearchLeadModel, lead.id)
        if row is None:
            row = ResearchLeadModel(
                id=lead.id,
                universe_id=lead.universe_id,
                continuity_id=lead.continuity_id,
                boundary_key=lead.boundary_key,
            )
            self.session.add(row)
        elif (row.universe_id, row.continuity_id, row.boundary_key) != (
            lead.universe_id,
            lead.continuity_id,
            lead.boundary_key,
        ):
            raise ValueError("Lead identity scope cannot change")
        row.status, row.payload, row.updated_at = lead.status, lead.model_dump(mode="json"), now()
        await self.session.flush()
        return lead
