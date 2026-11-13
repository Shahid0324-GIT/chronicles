from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.narrative import NarrativeKnowledge
from src.domain.entities import now
from src.domain.exceptions import NotFoundError
from src.infrastructure.persistence.models import ContinuityModel, NodeModel, RelationshipModel
from src.infrastructure.persistence.models.knowledge import (
    PromotionEvidenceModel,
    PromotionRecordModel,
)
from src.infrastructure.persistence.models.research import (
    ResearchClaimModel,
    SourceDocumentModel,
    SourcePassageModel,
)
from src.infrastructure.persistence.models.source_intelligence import NarrativeProjectionModel
from src.infrastructure.persistence.repositories import edge_entity, node_entity


class SqlNarrativeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def knowledge(self, universe: UUID, continuity: UUID) -> NarrativeKnowledge:
        scope = await self.session.get(ContinuityModel, continuity)
        if not scope or scope.universe_id != universe:
            raise NotFoundError("Narrative continuity does not belong to this universe")
        nodes = [
            node_entity(n)
            for n in await self.session.scalars(
                select(NodeModel).where(
                    NodeModel.universe_id == universe, NodeModel.continuity_id == continuity
                )
            )
        ]
        edges = [
            edge_entity(e)
            for e in await self.session.scalars(
                select(RelationshipModel).where(
                    RelationshipModel.universe_id == universe,
                    RelationshipModel.continuity_id == continuity,
                )
            )
        ]
        rows = await self.session.execute(
            select(
                PromotionRecordModel, ResearchClaimModel, SourcePassageModel, SourceDocumentModel
            )
            .join(ResearchClaimModel, ResearchClaimModel.id == PromotionRecordModel.claim_id)
            .join(
                PromotionEvidenceModel,
                PromotionEvidenceModel.promotion_id == PromotionRecordModel.id,
            )
            .join(SourcePassageModel, SourcePassageModel.id == PromotionEvidenceModel.passage_id)
            .join(SourceDocumentModel, SourceDocumentModel.id == SourcePassageModel.source_id)
            .where(
                PromotionRecordModel.universe_id == universe,
                PromotionRecordModel.continuity_id == continuity,
                PromotionRecordModel.reversed.is_(False),
            )
        )
        facts: dict[UUID, dict[str, Any]] = {}
        for promotion, claim, passage, source in rows:
            if promotion.data.get("resolution", {}).get("hidden_identity"):
                continue  # Ordinary narrative reads must not become a sensitive-alias side channel.
            fact = facts.setdefault(
                promotion.id,
                {
                    "target_id": str(promotion.target_id),
                    "kind": promotion.kind,
                    "payload": claim.payload,
                    "sources": [],
                },
            )
            fact["sources"].append(
                {
                    "id": str(source.id),
                    "url": (source.provenance or {}).get("attribution_url") or source.url,
                    "title": source.title + " — " + source.publisher,
                    "provenance": source.provenance or {},
                    "locator": (
                        f"passage {passage.id}; normalized offsets {passage.start}:{passage.end}"
                    ),
                }
            )
        return NarrativeKnowledge(nodes, edges, list(facts.values()))

    async def save(
        self,
        universe: UUID,
        continuity: UUID,
        boundary_key: str,
        revision: str,
        catalog: dict[str, Any],
    ) -> None:
        identifier = uuid5(continuity, "narrative:" + boundary_key)
        if self.session.bind and self.session.bind.dialect.name == "postgresql":
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": identifier.int % (2**63 - 1)}
            )
        row = await self.session.get(NarrativeProjectionModel, identifier)
        if row:
            if row.revision != revision:
                row.revision, row.catalog, row.updated_at = revision, catalog, now()
        else:
            self.session.add(
                NarrativeProjectionModel(
                    id=identifier,
                    universe_id=universe,
                    continuity_id=continuity,
                    boundary_key=boundary_key,
                    revision=revision,
                    catalog=catalog,
                    updated_at=now(),
                )
            )
        await self.session.flush()
