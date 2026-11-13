import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.research import ResearchRequest
from src.domain.entities import now
from src.domain.exceptions import NotFoundError
from src.domain.research import SourceDocument, SourcePassage, digest
from src.infrastructure.persistence.models import ContinuityModel, NodeModel, UniverseModel
from src.infrastructure.persistence.models.knowledge import PromotionRecordModel
from src.infrastructure.persistence.models.research import (
    ClaimEvidenceModel,
    ProviderUsageModel,
    ResearchClaimModel,
    ResearchEventModel,
    ResearchJobModel,
    SourceDocumentModel,
    SourcePassageModel,
)


def source_entity(row: SourceDocumentModel) -> SourceDocument:
    return SourceDocument(
        row.id,
        row.universe_id,
        row.continuity_id,
        row.url,
        row.title,
        row.publisher,
        row.text,
        row.content_hash,
        row.retrieved_at,
        row.permission_basis,
        row.source_scope,
        row.public_web,
        row.truncated,
        row.independence_key,
    )


class SqlResearchRepository:
    """One injected session; the calling transaction owns commit/rollback."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def context(self, universe_id: UUID, continuity_id: UUID) -> dict[str, Any]:
        universe = await self.session.get(UniverseModel, universe_id)
        continuity = await self.session.get(ContinuityModel, continuity_id)
        if not universe or not continuity or continuity.universe_id != universe_id:
            raise NotFoundError("Universe/continuity combination not found")
        titles = await self.session.scalars(
            select(NodeModel.title).where(
                NodeModel.universe_id == universe_id, NodeModel.continuity_id == continuity_id
            )
        )
        known = await self.session.scalars(
            select(ResearchClaimModel)
            .where(
                ResearchClaimModel.universe_id == universe_id,
                ResearchClaimModel.continuity_id == continuity_id,
                ResearchClaimModel.decision == "supported",
                ResearchClaimModel.id.in_(
                    select(PromotionRecordModel.claim_id).where(
                        PromotionRecordModel.reversed.is_(False)
                    )
                ),
            )
            .limit(10)
        )
        return {
            "universe": universe.title,
            "continuity": continuity.name,
            "curated_titles_not_evidence": list(titles),
            "previous_published_claims": [row.payload for row in known],
        }

    async def create_job(self, request: ResearchRequest) -> UUID:
        await self.context(request.universe_id, request.continuity_id)
        data = request.model_dump(mode="json")
        key = digest(json.dumps(data, sort_keys=True, ensure_ascii=False))
        existing = await self.session.scalar(
            select(ResearchJobModel)
            .where(
                ResearchJobModel.request_hash == key,
                ResearchJobModel.status.in_(["queued", "running", "completed", "partial"]),
                ResearchJobModel.created_at >= now() - timedelta(hours=24),
            )
            .order_by(ResearchJobModel.created_at.desc())
        )
        if existing:
            return existing.id
        identifier = uuid4()
        self.session.add(
            ResearchJobModel(
                id=identifier,
                universe_id=request.universe_id,
                continuity_id=request.continuity_id,
                objective=request.objective,
                request=data,
                request_hash=key,
                status="queued",
                checkpoint={},
                cancel_requested=False,
                error=None,
                created_at=now(),
                updated_at=now(),
            )
        )
        await self.session.flush()
        await self.event(identifier, "research.queued", {})
        return identifier

    async def get_job(self, job_id: UUID) -> dict[str, Any] | None:
        row = await self.session.get(ResearchJobModel, job_id)
        if not row:
            return None
        usage = await self.session.scalars(
            select(ProviderUsageModel).where(ProviderUsageModel.job_id == job_id)
        )
        return {
            "id": str(row.id),
            "universe_id": str(row.universe_id),
            "continuity_id": str(row.continuity_id),
            "objective": row.objective,
            "request": row.request,
            "status": row.status,
            "checkpoint": row.checkpoint,
            "cancel_requested": row.cancel_requested,
            "error": row.error,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
            "provider_usage": [item.detail for item in usage],
        }

    async def lock_job(self, job_id: UUID) -> dict[str, Any] | None:
        row = await self.session.scalar(
            select(ResearchJobModel)
            .where(ResearchJobModel.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return await self.get_job(job_id) if row else None

    async def update_job(self, job_id: UUID, **values: Any) -> None:
        row = await self.session.scalar(
            select(ResearchJobModel).where(ResearchJobModel.id == job_id).with_for_update()
        )
        if not row:
            raise NotFoundError("Research job not found")
        if not set(values) <= {"status", "checkpoint", "cancel_requested", "error"}:
            raise ValueError("Unsupported job mutation")
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = now()
        await self.session.flush()

    async def cached_source(
        self, url: str, universe_id: UUID, continuity_id: UUID, after: datetime
    ) -> SourceDocument | None:
        row = await self.session.scalar(
            select(SourceDocumentModel)
            .where(
                SourceDocumentModel.url_hash == digest(url),
                SourceDocumentModel.universe_id == universe_id,
                SourceDocumentModel.continuity_id == continuity_id,
                SourceDocumentModel.retrieved_at >= after,
            )
            .order_by(SourceDocumentModel.retrieved_at.desc())
        )
        return source_entity(row) if row else None

    async def cancel_job(self, job_id: UUID) -> bool:
        row = await self.session.scalar(
            select(ResearchJobModel)
            .where(ResearchJobModel.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not row:
            raise NotFoundError("Research job not found")
        if row.status not in {"queued", "running"}:
            return False
        row.cancel_requested = True
        if row.status == "queued":
            row.status = "cancelled"
        row.updated_at = now()
        await self.session.flush()
        return True

    async def save_source(self, source: SourceDocument, passages: list[SourcePassage]) -> None:
        if await self.session.get(SourceDocumentModel, source.id):
            return
        self.session.add(
            SourceDocumentModel(
                id=source.id,
                universe_id=source.universe_id,
                continuity_id=source.continuity_id,
                url=source.url,
                url_hash=digest(source.url),
                title=source.title,
                publisher=source.publisher,
                text=source.text,
                content_hash=source.content_hash,
                retrieved_at=source.retrieved_at,
                permission_basis=source.permission_basis,
                source_scope=source.source_scope,
                public_web=source.public_web,
                truncated=source.truncated,
                independence_key=source.independence_key,
            )
        )
        await self.session.flush()
        self.session.add_all(
            [
                SourcePassageModel(
                    id=p.id,
                    universe_id=source.universe_id,
                    continuity_id=source.continuity_id,
                    source_id=source.id,
                    ordinal=p.ordinal,
                    start=p.start,
                    end=p.end,
                    text=p.text,
                    content_hash=p.content_hash,
                )
                for p in passages
            ]
        )
        await self.session.flush()

    async def get_passages(self, source_ids: list[UUID]) -> list[SourcePassage]:
        rows = await self.session.scalars(
            select(SourcePassageModel)
            .where(SourcePassageModel.source_id.in_(source_ids))
            .order_by(SourcePassageModel.source_id, SourcePassageModel.ordinal)
        )
        return [
            SourcePassage(
                row.id, row.source_id, row.ordinal, row.start, row.end, row.text, row.content_hash
            )
            for row in rows
        ]

    async def save_claim(
        self,
        job_id: UUID,
        claim: dict[str, Any],
        evidence: list[dict[str, Any]],
        decision: str,
        reason: str,
    ) -> None:
        job = await self.session.get(ResearchJobModel, job_id)
        if not job:
            raise NotFoundError("Research job not found")
        identifier = UUID(claim["id"])
        row = await self.session.get(ResearchClaimModel, identifier)
        if row is None:
            row = ResearchClaimModel(
                id=identifier,
                job_id=job_id,
                universe_id=job.universe_id,
                continuity_id=job.continuity_id,
                kind=claim["kind"],
                content_hash=claim["hash"],
                payload=claim["payload"],
                decision=decision,
                reason=reason,
            )
            self.session.add(row)
        else:
            row.decision, row.reason = decision, reason
        await self.session.flush()
        await self.session.execute(
            delete(ClaimEvidenceModel).where(ClaimEvidenceModel.claim_id == identifier)
        )
        for item in evidence:
            self.session.add(
                ClaimEvidenceModel(
                    claim_id=identifier,
                    universe_id=job.universe_id,
                    continuity_id=job.continuity_id,
                    passage_id=UUID(item["passage_id"]),
                    quote=item["quote"],
                    quote_start=item["start"],
                    quote_end=item["end"],
                )
            )
        await self.session.flush()

    async def findings(self, job_id: UUID) -> list[dict[str, Any]]:
        rows = await self.session.scalars(
            select(ResearchClaimModel)
            .where(ResearchClaimModel.job_id == job_id)
            .order_by(ResearchClaimModel.id)
        )
        publications = {
            record.claim_id: record
            for record in await self.session.scalars(
                select(PromotionRecordModel).where(
                    PromotionRecordModel.job_id == job_id, PromotionRecordModel.reversed.is_(False)
                )
            )
        }
        result = []
        for row in rows:
            evidence = (
                await self.session.execute(
                    select(ClaimEvidenceModel, SourcePassageModel, SourceDocumentModel)
                    .join(
                        SourcePassageModel, ClaimEvidenceModel.passage_id == SourcePassageModel.id
                    )
                    .join(
                        SourceDocumentModel, SourcePassageModel.source_id == SourceDocumentModel.id
                    )
                    .where(ClaimEvidenceModel.claim_id == row.id)
                )
            ).all()
            result.append(
                {
                    "id": str(row.id),
                    "kind": row.kind,
                    "payload": row.payload,
                    "decision": row.decision,
                    "reason": row.reason,
                    "canonical": row.id in publications,
                    "canonical_id": str(publications[row.id].target_id)
                    if row.id in publications
                    else None,
                    "promotion_id": str(publications[row.id].id)
                    if row.id in publications
                    else None,
                    "evidence": [
                        {
                            "passage_id": str(p.id),
                            "source_id": str(s.id),
                            "quote": e.quote,
                            "passage_start": p.start,
                            "quote_start": e.quote_start,
                            "quote_end": e.quote_end,
                            "url": s.url,
                            "title": s.title,
                            "publisher": s.publisher,
                            "content_hash": s.content_hash,
                            "retrieved_at": s.retrieved_at.isoformat(),
                            "source_scope": s.source_scope,
                            "permission_basis": s.permission_basis,
                            "public_web": s.public_web,
                            "truncated": s.truncated,
                            "independence_key": s.independence_key,
                        }
                        for e, p, s in evidence
                    ],
                }
            )
        return result

    async def event(self, job_id: UUID, stage: str, detail: dict[str, Any]) -> None:
        self.session.add(
            ResearchEventModel(job_id=job_id, stage=stage, detail=detail, created_at=now())
        )
        await self.session.flush()

    async def events(self, job_id: UUID) -> list[dict[str, Any]]:
        rows = await self.session.scalars(
            select(ResearchEventModel)
            .where(ResearchEventModel.job_id == job_id)
            .order_by(ResearchEventModel.id)
        )
        return [
            {
                "id": row.id,
                "stage": row.stage,
                "detail": row.detail,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    async def usage(self, job_id: UUID, values: list[dict[str, Any]]) -> None:
        self.session.add_all(
            [ProviderUsageModel(id=uuid4(), job_id=job_id, detail=value) for value in values]
        )
        await self.session.flush()
