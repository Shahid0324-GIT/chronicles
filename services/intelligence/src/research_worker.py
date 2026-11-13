"""Single local PostgreSQL worker. Run with python -m src.research_worker --once."""

import argparse
import asyncio
from uuid import UUID

from sqlalchemy import select, text

from src.application.research_contracts import InferenceFailure
from src.domain.entities import now
from src.infrastructure.config.settings import Settings
from src.infrastructure.persistence.database import create_database
from src.infrastructure.persistence.models.research import ResearchJobModel
from src.infrastructure.persistence.research_repository import SqlResearchRepository
from src.infrastructure.research_runtime import build_workflow
from src.orchestration.research_workflow import ResearchCancelled

WORKER_LOCK = 1128813135


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
                        select(ResearchJobModel).where(ResearchJobModel.status == "running")
                    )
                    for job in interrupted:
                        job.status = "cancelled" if job.cancel_requested else "queued"
                        job.updated_at = now()
                workflow = build_workflow(settings, factory)
                while True:
                    async with factory() as session, session.begin():
                        query = (
                            select(ResearchJobModel)
                            .where(ResearchJobModel.status == "queued")
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
                            row.updated_at = now()
                    if selected_id is None:
                        if once:
                            return processed
                        await asyncio.sleep(1)
                        continue
                    status, error = "completed", None
                    try:
                        async with asyncio.timeout(settings.agent_max_job_seconds):
                            state = await workflow.run(selected_id, checkpoint)
                        if (
                            not state.get("verified")
                            or state["verified"] < len(state.get("candidates", []))
                            or state.get("errors")
                            or state.get("publication", {}).get("unresolved")
                            or state.get("narrative", {}).get("partial")
                        ):
                            status = "partial"
                    except ResearchCancelled:
                        status = "cancelled"
                    except InferenceFailure as failure:
                        status, error = (
                            ("partial" if "budget" in failure.code else "failed"),
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
                            status = "cancelled"
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
