"""Single local PostgreSQL worker. Run with python -m src.research_worker --once."""

import argparse
import asyncio
import time
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select, text

from src.application.research_budget import DeferredInference, freeze_active_time
from src.application.research_contracts import InferenceFailure
from src.application.research_frontier import ResearchFrontierService
from src.domain.entities import now
from src.infrastructure.config.settings import Settings
from src.infrastructure.persistence.database import create_database
from src.infrastructure.persistence.models.research import ResearchJobModel
from src.infrastructure.persistence.research_memory import SqlResearchMemory
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.research_runtime import build_workflow
from src.orchestration.research_workflow import ResearchCancelled, ResearchPaused

WORKER_LOCK = 1128813135
MAX_PROVIDER_DEFERRALS = 3


def defer_provider(
    checkpoint: dict[str, Any], failure: DeferredInference, current_time: float
) -> bool:
    attempts = dict(checkpoint.get("provider_deferrals", {}))
    remaining = checkpoint.get("deadline_at", current_time) - current_time
    count = attempts.get(failure.operation, 0)
    if count >= MAX_PROVIDER_DEFERRALS or remaining <= 0:
        return False
    attempts[failure.operation] = count + 1
    checkpoint["provider_deferrals"] = attempts
    checkpoint["provider_resume_at"] = current_time + failure.delay
    checkpoint["active_seconds_remaining"] = remaining
    return True


async def worker(settings: Settings, once: bool = False, job_id: UUID | None = None) -> int:
    engine, factory = create_database(settings.database_url)
    processed = 0
    try:
        # Session-level advisory lock also prevents multiple worker processes loading models.
        async with engine.connect() as connection:
            acquired = await connection.scalar(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": WORKER_LOCK}
            )
            await connection.commit()
            if not acquired:
                raise RuntimeError("A research worker is already active")
            try:
                async with factory() as session, session.begin():
                    interrupted = await session.scalars(
                        select(ResearchJobModel).where(
                            ResearchJobModel.status.in_(["running", "pausing"])
                        )
                    )
                    for job in interrupted:
                        if job.cancel_requested:
                            job.status = "cancelled"
                        elif job.status == "pausing":
                            job.status = "paused"
                            checkpoint = dict(job.checkpoint)
                            freeze_active_time(checkpoint, time.time())
                            job.checkpoint = checkpoint
                        else:
                            job.status = "queued"
                        job.updated_at = now()
                workflow = build_workflow(settings, factory)
                while True:
                    async with factory() as session, session.begin():
                        query = (
                            select(ResearchJobModel)
                            .where(ResearchJobModel.status == "queued")
                            .where(
                                or_(
                                    ResearchJobModel.checkpoint["provider_resume_at"]
                                    .as_float()
                                    .is_(None),
                                    ResearchJobModel.checkpoint["provider_resume_at"].as_float()
                                    <= time.time(),
                                )
                            )
                            .order_by(ResearchJobModel.created_at)
                            .with_for_update(skip_locked=True)
                            .limit(1)
                        )
                        if job_id:
                            query = query.where(ResearchJobModel.id == job_id)
                        row = await session.scalar(query)
                        selected_id = row.id if row else None
                        checkpoint = dict(row.checkpoint) if row else {}
                        if row:
                            row.status = "running"
                            checkpoint.pop("provider_resume_at", None)
                            if "active_seconds_remaining" in checkpoint:
                                checkpoint["deadline_at"] = time.time() + checkpoint.pop(
                                    "active_seconds_remaining"
                                )
                                row.error = None
                            checkpoint.setdefault(
                                "deadline_at",
                                time.time()
                                + min(
                                    settings.agent_max_job_seconds,
                                    (row.request.get("research_policy") or {}).get(
                                        "max_seconds",
                                        settings.research_focused_policy.max_seconds
                                        if row.request.get("arc_id")
                                        and row.request.get("adaptive_research")
                                        else settings.agent_max_job_seconds,
                                    ),
                                ),
                            )
                            row.checkpoint = checkpoint
                            row.updated_at = now()
                    if selected_id is None:
                        if once:
                            return processed
                        await asyncio.sleep(1)
                        continue
                    status, error = "completed", None
                    deferred: DeferredInference | None = None
                    try:
                        async with asyncio.timeout(max(0, checkpoint["deadline_at"] - time.time())):
                            state = await workflow.run(selected_id, checkpoint)
                        coverage_sufficient = (
                            state.get("coverage", {}).get("outcome")
                            == "SUFFICIENT_FOR_PRESENTATION"
                        )
                        if (
                            not state.get("verified")
                            or state["verified"] < len(state.get("candidates", []))
                            or state.get("errors")
                            or state.get("publication", {}).get("unresolved")
                            or state.get("narrative", {}).get("partial")
                            or (state.get("coverage") and not coverage_sufficient)
                        ):
                            status = "partial"
                    except ResearchCancelled:
                        status = "cancelled"
                    except ResearchPaused:
                        status, error = "paused", "user_paused"
                    except DeferredInference as failure:
                        deferred = failure
                        status, error = "failed", failure.cause
                    except InferenceFailure as failure:
                        status, error = (
                            (
                                "partial"
                                if "budget" in failure.code
                                or failure.code == "job_duration_exceeded"
                                else "failed"
                            ),
                            failure.code,
                        )
                    except TimeoutError:
                        status, error = "partial", "job_duration_exceeded"
                    except Exception:
                        status, error = "failed", "research_execution_failed"
                    async with factory() as session, session.begin():
                        archive = SqlResearchRepository(session)
                        finished_job = await session.scalar(
                            select(ResearchJobModel)
                            .where(ResearchJobModel.id == selected_id)
                            .with_for_update()
                        )
                        if finished_job and finished_job.cancel_requested:
                            status, error = "cancelled", None
                        elif finished_job and finished_job.status == "pausing":
                            status, error = "paused", "user_paused"
                            frozen = dict(finished_job.checkpoint)
                            freeze_active_time(frozen, time.time())
                            await archive.update_job(selected_id, checkpoint=frozen)
                        if finished_job and deferred and status not in {"cancelled", "paused"}:
                            retry_checkpoint = dict(finished_job.checkpoint)
                            if defer_provider(retry_checkpoint, deferred, time.time()):
                                status = "queued"
                                await archive.update_job(selected_id, checkpoint=retry_checkpoint)
                                await archive.event(
                                    selected_id,
                                    "research.provider_paused",
                                    {
                                        "cause": deferred.cause,
                                        "resume_at": retry_checkpoint["provider_resume_at"],
                                        "operation": deferred.operation,
                                    },
                                )
                        if finished_job and finished_job.checkpoint.get("policy"):
                            final_state = dict(finished_job.checkpoint)
                            coverage = dict(final_state.get("coverage", {}))
                            if error and ("budget" in error or error == "job_duration_exceeded"):
                                coverage.update(outcome="BUDGET_EXHAUSTED", reason=error)
                            elif not deferred and status != "paused":
                                coverage.setdefault("outcome", "PARTIAL_COVERAGE")
                            if coverage:
                                final_state["coverage"] = coverage
                            await archive.update_job(selected_id, checkpoint=final_state)
                            memory = SqlResearchMemory(session)
                            leads = await memory.leads(
                                finished_job.universe_id,
                                finished_job.continuity_id,
                                ResearchFrontierService.boundary(
                                    finished_job.request.get("spoiler_position")
                                ),
                            )
                            for lead in leads:
                                if lead.last_job_id == selected_id and lead.status != "RESOLVED":
                                    lead.status = (
                                        "PARTIALLY_RESOLVED" if lead.evidence_ids else "QUEUED"
                                    )
                                    if coverage.get("outcome") == "BLOCKED_BY_SOURCE_ACCESS":
                                        lead.status = "BLOCKED"
                                    lead.last_stop_reason = error or str(coverage.get("outcome"))
                                    await memory.save_lead(lead)
                        await archive.update_job(selected_id, status=status, error=error)
                        await archive.event(selected_id, "research." + status, {"error": error})
                    print(
                        f"Research job {selected_id}: {status}" + (f" ({error})" if error else "")
                    )
                    workflow.inference.usage.clear()
                    processed += 1
                    if once:
                        return processed
            finally:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": WORKER_LOCK}
                )
                await connection.commit()
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Chronicles research queue")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--job-id", type=UUID)
    arguments = parser.parse_args()
    asyncio.run(worker(Settings(), arguments.once, arguments.job_id))


if __name__ == "__main__":
    main()
