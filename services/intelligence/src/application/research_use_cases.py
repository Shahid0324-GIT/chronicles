from typing import Protocol
from uuid import UUID

from src.application.ports.research import ResearchRepository
from src.application.research import ResearchRequest


class ResearchRequestError(Exception):
    pass


class SourceApprovalPolicy(Protocol):
    def is_approved(self, url: str) -> bool: ...


class QueueResearch:
    def __init__(
        self,
        archive: ResearchRepository,
        policy: SourceApprovalPolicy,
        source_limit: int,
        search_enabled: bool,
    ) -> None:
        self.archive, self.policy = archive, policy
        self.source_limit, self.search_enabled = source_limit, search_enabled

    async def execute(self, command: ResearchRequest) -> UUID:
        if len(command.sources) > self.source_limit or (
            not command.sources and not command.allow_search
        ):
            raise ResearchRequestError(
                "Provide approved sources within the configured source limit"
            )
        if command.allow_search and not self.search_enabled:
            raise ResearchRequestError(
                "Search is not configured; supply approved source URLs or text"
            )
        if any(
            source.url and not self.policy.is_approved(source.url) for source in command.sources
        ):
            raise ResearchRequestError("Source URL is not permitted by the configured host policy")
        return await self.archive.create_job(command)


class CancelResearch:
    def __init__(self, archive: ResearchRepository) -> None:
        self.archive = archive

    async def execute(self, job_id: UUID) -> None:
        if await self.archive.cancel_job(job_id):
            await self.archive.event(job_id, "research.cancel_requested", {})
