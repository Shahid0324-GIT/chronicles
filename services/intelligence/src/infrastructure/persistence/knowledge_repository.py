from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import GraphNode, GraphRelationship, now
from src.domain.exceptions import NotFoundError
from src.domain.knowledge import name_key
from src.infrastructure.persistence.models import NodeModel, RelationshipModel
from src.infrastructure.persistence.models.knowledge import (
    EntityAliasModel,
    KnowledgeDecisionModel,
    PromotionEvidenceModel,
    PromotionRecordModel,
)
from src.infrastructure.persistence.models.research import (
    ResearchClaimModel,
)
from src.infrastructure.persistence.repositories import edge_entity, node_entity


class SqlKnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_scope(self, universe_id: UUID, continuity_id: UUID) -> None:
        if self.session.bind and self.session.bind.dialect.name == "postgresql":
            key = (universe_id.int ^ continuity_id.int) % (2**63 - 1)
            await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})

    async def catalog(self, universe_id: UUID, continuity_id: UUID) -> list[dict[str, Any]]:
        nodes = await self.session.scalars(
            select(NodeModel)
            .where(NodeModel.universe_id == universe_id, NodeModel.continuity_id == continuity_id)
            .order_by(NodeModel.id)
        )
        aliases = list(
            await self.session.scalars(
                select(EntityAliasModel).where(
                    EntityAliasModel.universe_id == universe_id,
                    EntityAliasModel.continuity_id == continuity_id,
                    EntityAliasModel.sensitive.is_(False),
                )
            )
        )
        edges = list(
            await self.session.scalars(
                select(RelationshipModel).where(
                    RelationshipModel.universe_id == universe_id,
                    RelationshipModel.continuity_id == continuity_id,
                )
            )
        )
        return [
            {
                "id": str(n.id),
                "name": n.title,
                "type": n.type,
                "description": n.summary,
                "event": n.node_metadata.get("event"),
                "aliases": [a.name for a in aliases if a.node_id == n.id],
                "relationships": [
                    {
                        "source": str(e.source_node_id),
                        "target": str(e.target_node_id),
                        "type": e.relationship_type,
                    }
                    for e in edges
                    if n.id in {e.source_node_id, e.target_node_id}
                ][:8],
            }
            for n in nodes
        ]

    async def decision(
        self, claim_id: UUID, job_id: UUID, universe_id: UUID, continuity_id: UUID, **data: Any
    ) -> None:
        row = await self.session.get(KnowledgeDecisionModel, claim_id)
        if row:
            row.data = {**row.data, **data}
            row.updated_at = now()
        else:
            self.session.add(
                KnowledgeDecisionModel(
                    claim_id=claim_id,
                    job_id=job_id,
                    universe_id=universe_id,
                    continuity_id=continuity_id,
                    data=data,
                    updated_at=now(),
                )
            )
        await self.session.flush()

    async def decisions(self, job_id: UUID) -> dict[str, dict[str, Any]]:
        rows = await self.session.scalars(
            select(KnowledgeDecisionModel).where(KnowledgeDecisionModel.job_id == job_id)
        )
        return {str(row.claim_id): row.data for row in rows}

    async def node(self, identifier: UUID) -> GraphNode | None:
        row = await self.session.get(NodeModel, identifier, populate_existing=True)
        return node_entity(row) if row else None

    async def edge(
        self, source: UUID, target: UUID, kind: str, continuity: UUID
    ) -> GraphRelationship | None:
        row = await self.session.scalar(
            select(RelationshipModel)
            .where(
                RelationshipModel.source_node_id == source,
                RelationshipModel.target_node_id == target,
                RelationshipModel.relationship_type == kind,
                RelationshipModel.continuity_id == continuity,
            )
            .order_by(RelationshipModel.id)
            .limit(1)
        )
        return edge_entity(row) if row else None

    async def add_node(self, node: GraphNode) -> None:
        self.session.add(
            NodeModel(
                id=node.id,
                universe_id=node.universe_id,
                continuity_id=node.continuity_id,
                type=node.type.value,
                title=node.title,
                summary=node.summary,
                node_metadata=node.metadata,
                created_at=node.created_at,
                updated_at=node.updated_at,
            )
        )
        await self.session.flush()

    async def add_edge(self, edge: GraphRelationship) -> None:
        # Application service must validate actual endpoints inside this transaction.
        self.session.add(
            RelationshipModel(
                id=edge.id,
                universe_id=edge.universe_id,
                continuity_id=edge.continuity_id,
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                relationship_type=edge.relationship_type.value,
                description=edge.description,
            )
        )
        await self.session.flush()

    async def alias(self, node: GraphNode, name: str, claim_id: UUID, sensitive: bool) -> UUID:
        normalized = name_key(name)
        identifier = uuid5(node.id, normalized)
        existing = await self.session.get(EntityAliasModel, identifier)
        if not existing:
            self.session.add(
                EntityAliasModel(
                    id=identifier,
                    node_id=node.id,
                    universe_id=node.universe_id,
                    continuity_id=node.continuity_id,
                    claim_id=claim_id,
                    name=name,
                    normalized_name=normalized,
                    sensitive=sensitive,
                )
            )
            await self.session.flush()
        return identifier

    @staticmethod
    def record_data(row: PromotionRecordModel) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "claim_id": str(row.claim_id),
            "job_id": str(row.job_id),
            "universe_id": str(row.universe_id),
            "continuity_id": str(row.continuity_id),
            "target_id": str(row.target_id),
            "kind": row.kind,
            "created": row.created,
            "reversed": row.reversed,
            "data": row.data,
            "created_at": row.created_at.isoformat(),
            "reversed_at": row.reversed_at.isoformat() if row.reversed_at else None,
            "correction_reason": row.correction_reason,
        }

    async def records(self, job_id: UUID | None = None) -> list[dict[str, Any]]:
        query = select(PromotionRecordModel).order_by(
            PromotionRecordModel.created_at, PromotionRecordModel.id
        )
        if job_id:
            query = query.where(PromotionRecordModel.job_id == job_id)
        return [self.record_data(row) for row in await self.session.scalars(query)]

    async def record(
        self,
        claim: dict[str, Any],
        job: dict[str, Any],
        target: UUID,
        created: bool,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        identifier = uuid5(UUID(claim["id"]), "promotion-v1")
        existing = await self.session.get(PromotionRecordModel, identifier)
        if existing:
            return self.record_data(existing)
        row = PromotionRecordModel(
            id=identifier,
            claim_id=UUID(claim["id"]),
            job_id=UUID(job["id"]),
            universe_id=UUID(job["universe_id"]),
            continuity_id=UUID(job["continuity_id"]),
            target_id=target,
            kind=claim["kind"],
            created=created,
            reversed=False,
            data=data,
            created_at=now(),
            reversed_at=None,
            correction_reason=None,
        )
        self.session.add(row)
        await self.session.flush()
        for item in claim["evidence"]:
            self.session.add(
                PromotionEvidenceModel(
                    promotion_id=identifier,
                    passage_id=UUID(item["passage_id"]),
                    universe_id=row.universe_id,
                    continuity_id=row.continuity_id,
                    quote_start=item["quote_start"],
                    quote_end=item["quote_end"],
                    quote=item["quote"],
                    source_hash=item["content_hash"],
                )
            )
        await self.session.flush()
        return self.record_data(row)

    async def promotion_record(self, record_id: UUID) -> dict[str, Any] | None:
        row = await self.session.get(PromotionRecordModel, record_id, populate_existing=True)
        return self.record_data(row) if row else None

    async def rollback(self, record_id: UUID, reason: str) -> dict[str, Any]:
        row = await self.session.get(PromotionRecordModel, record_id, populate_existing=True)
        if not row:
            raise NotFoundError("Promotion record not found")
        if row.reversed:
            return self.record_data(row)
        history = list(
            await self.session.scalars(
                select(PromotionRecordModel).where(PromotionRecordModel.target_id == row.target_id)
            )
        )
        owner = next((item for item in history if item.created), None)
        others = list(
            await self.session.scalars(
                select(PromotionRecordModel).where(
                    PromotionRecordModel.reversed.is_(False), PromotionRecordModel.id != row.id
                )
            )
        )
        still_supported = any(p.target_id == row.target_id for p in others)
        removed = False
        if owner is not None and not still_supported:
            if row.kind == "relationship":
                edge = await self.session.get(RelationshipModel, row.target_id)
                snapshot = owner.data.get("snapshot", {})
                endpoints_match = False
                if edge:
                    if "source" in snapshot and "target" in snapshot and "type" in snapshot:
                        endpoints_match = (
                            str(edge.source_node_id) == snapshot["source"]
                            and str(edge.target_node_id) == snapshot["target"]
                            and edge.relationship_type == snapshot["type"]
                        )
                    else:
                        endpoints_match = (
                            uuid5(
                                owner.continuity_id,
                                f"edge:{edge.source_node_id}:{edge.target_node_id}:{edge.relationship_type}",
                            )
                            == owner.target_id
                        )
                if (
                    edge
                    and endpoints_match
                    and edge.universe_id == owner.universe_id
                    and edge.continuity_id == owner.continuity_id
                    and edge.description == snapshot.get("description")
                ):
                    await self.session.delete(edge)
                    removed = True
            else:
                incident = await self.session.scalar(
                    select(RelationshipModel.id)
                    .where(
                        or_(
                            RelationshipModel.source_node_id == row.target_id,
                            RelationshipModel.target_node_id == row.target_id,
                        )
                    )
                    .limit(1)
                )
                node = await self.session.get(NodeModel, row.target_id)
                snapshot = owner.data.get("snapshot", {})
                original_claim = await self.session.get(ResearchClaimModel, owner.claim_id)
                original_type = snapshot.get("type") or (
                    original_claim.payload.get("type") if original_claim else None
                )
                if (
                    node
                    and not incident
                    and node.universe_id == owner.universe_id
                    and node.continuity_id == owner.continuity_id
                    and node.type == original_type
                    and node.title == snapshot.get("name")
                    and node.summary == snapshot.get("description")
                    and node.node_metadata == snapshot.get("metadata", {})
                ):
                    await self.session.execute(
                        delete(EntityAliasModel).where(EntityAliasModel.node_id == node.id)
                    )
                    await self.session.delete(node)
                    removed = True
        # Remove an alias only when no other active publication still supports that binding.
        for alias_id in row.data.get("alias_ids", []):
            if not any(alias_id in p.data.get("alias_ids", []) for p in others):
                await self.session.execute(
                    delete(EntityAliasModel).where(EntityAliasModel.id == UUID(alias_id))
                )
        row.reversed, row.reversed_at, row.correction_reason = True, now(), reason
        row.data = {
            **row.data,
            "rollback_removed_target": removed,
            "rollback_retained_target": not removed,
        }
        await self.session.flush()
        return self.record_data(row)

    async def hidden_targets(self, universe_id: UUID, allowed_sources: list[UUID]) -> set[UUID]:
        records = list(
            await self.session.scalars(
                select(PromotionRecordModel).where(PromotionRecordModel.universe_id == universe_id)
            )
        )
        owned = {r.target_id for r in records if r.created}
        allowed = {str(value) for value in allowed_sources}
        visible = {
            r.target_id
            for r in records
            if not r.reversed
            and bool(r.data.get("evidence"))
            and all(e["source_id"] in allowed for e in r.data["evidence"])
        }
        return owned - visible

    async def aliases(
        self, node_id: UUID, allowed_sources: list[UUID] | None
    ) -> list[dict[str, Any]]:
        rows = list(
            await self.session.scalars(
                select(EntityAliasModel)
                .where(EntityAliasModel.node_id == node_id, EntityAliasModel.sensitive.is_(False))
                .order_by(EntityAliasModel.name)
            )
        )
        records = list(
            await self.session.scalars(
                select(PromotionRecordModel).where(
                    PromotionRecordModel.target_id == node_id,
                    PromotionRecordModel.reversed.is_(False),
                )
            )
        )
        allowed = {str(value) for value in allowed_sources} if allowed_sources is not None else None
        result = []
        for row in rows:
            supporting = [
                r
                for r in records
                if str(row.id) in r.data.get("alias_ids", [])
                and bool(r.data.get("evidence"))
                and (
                    allowed is None
                    or all(e["source_id"] in allowed for e in r.data.get("evidence", []))
                )
            ]
            if not supporting:
                continue
            result.append(
                {
                    "id": str(row.id),
                    "node_id": str(row.node_id),
                    "name": row.name,
                    "normalized_name": row.normalized_name,
                    "claim_id": str(row.claim_id),
                    "supporting_claim_ids": sorted({str(r.claim_id) for r in supporting}),
                    "source_ids": sorted(
                        {e["source_id"] for r in supporting for e in r.data.get("evidence", [])}
                    ),
                }
            )
        return result
