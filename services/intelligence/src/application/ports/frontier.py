from contextlib import AbstractAsyncContextManager
from typing import Protocol
from uuid import UUID

from src.application.research_policy import ResearchLead, UniverseResearchProfile


class ResearchMemory(Protocol):
    async def profile(self, universe: UUID) -> UniverseResearchProfile | None: ...
    async def save_profile(self, profile: UniverseResearchProfile) -> None: ...
    async def leads(
        self, universe: UUID, continuity: UUID, boundary: str
    ) -> list[ResearchLead]: ...
    async def save_lead(self, lead: ResearchLead) -> ResearchLead: ...


class ResearchMemoryTransaction(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[ResearchMemory]: ...
