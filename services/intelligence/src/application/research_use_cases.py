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
            not command.sources and not command.allow_search and not command.use_registry
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


class ResumeResearch:
    """Bounded retries of a frozen extraction; new acquisition uses a refreshed job."""

    def __init__(self, archive: ResearchRepository) -> None:
        self.archive = archive

    async def execute(self, job_id: UUID, stage: str, reason: str) -> None:
        predecessors = {
            "identity_resolver": "extractor",
            "relationship_analyst": "identity_resolver",
            "verifier": "relationship_analyst",
            "promotion_policy": "verifier",
            "narrative_builder": "promotion_policy",
        }
        if stage not in predecessors:
            raise ResearchRequestError("Retry requires an immutable post-extraction boundary")
        job = await self.archive.lock_job(job_id)
        if not job:
            from src.domain.exceptions import NotFoundError

            raise NotFoundError("Research job not found")
        if job["status"] in {"queued", "running"}:
            raise ResearchRequestError("An active job cannot be requeued")
        checkpoint = dict(job["checkpoint"])
        count = checkpoint.get("resume_count", 0)
        if count >= 2 or not checkpoint.get("candidates"):
            raise ResearchRequestError("Retry budget exhausted or no completed extraction exists")
        clear = {
            "identity_resolver": [
                "resolutions",
                "semantic_assessments",
                "publication",
                "narrative",
            ],
            "relationship_analyst": ["semantic_assessments", "publication", "narrative"],
            "verifier": ["semantic_assessments", "publication", "narrative"],
            "promotion_policy": ["publication", "narrative"],
            "narrative_builder": ["narrative"],
        }
        for field in clear[stage]:
            checkpoint.pop(field, None)
        checkpoint.update(stage=predecessors[stage], resume_count=count + 1)
        await self.archive.update_job(
            job_id, status="queued", error=None, cancel_requested=False, checkpoint=checkpoint
        )
        await self.archive.event(
            job_id, "research.retry_requested", {"from_stage": stage, "reason": reason}
        )
