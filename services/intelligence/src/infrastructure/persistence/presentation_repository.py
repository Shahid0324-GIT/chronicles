from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import now
from src.infrastructure.persistence.models.source_intelligence import KnowledgePresentationModel


class SqlPresentationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, identifier: UUID) -> dict[str, Any] | None:
        row = await self.session.get(KnowledgePresentationModel, identifier)
        if not row:
            return None
        return {
            "knowledge_revision": row.knowledge_revision,
            "policy_version": row.policy_version,
            "payload": row.payload,
            "grounding_status": row.grounding_status,
            "generated_at": row.generated_at.isoformat(),
            "provider_metadata": row.provider_metadata,
            "evidence_fingerprint": row.evidence_fingerprint,
        }

    async def save(
        self,
        identifier: UUID,
        universe: UUID,
        continuity: UUID,
        resource: UUID,
        kind: str,
        boundary: str,
        revision: str,
        evidence: str,
        language: str,
        policy: str,
        payload: dict[str, Any],
        status: str,
        provider: list[dict[str, Any]],
    ) -> None:
        if self.session.bind and self.session.bind.dialect.name == "postgresql":
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": identifier.int % (2**63 - 1)}
            )
        row = await self.session.get(KnowledgePresentationModel, identifier)
        values = dict(
            universe_id=universe,
            continuity_id=continuity,
            resource_id=resource,
            kind=kind,
            boundary_key=boundary,
            knowledge_revision=revision,
            evidence_fingerprint=evidence,
            language=language,
            policy_version=policy,
            payload=payload,
            grounding_status=status,
            provider_metadata=provider,
            generated_at=now(),
        )
        if row:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            self.session.add(KnowledgePresentationModel(id=identifier, **values))
        await self.session.flush()
