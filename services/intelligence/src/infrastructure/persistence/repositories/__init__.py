from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Continuity, GraphNode, GraphRelationship, Universe
from src.domain.value_objects import NodeType, RelationshipType, Slug
from src.infrastructure.persistence.models import (
    ContinuityModel,
    NodeModel,
    RelationshipModel,
    UniverseModel,
)


def universe_entity(row: UniverseModel) -> Universe:
    return Universe(
        id=row.id,
        slug=Slug(row.slug),
        title=row.title,
        description=row.description,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def node_entity(row: NodeModel) -> GraphNode:
    return GraphNode(
        id=row.id,
        universe_id=row.universe_id,
        continuity_id=row.continuity_id,
        type=NodeType(row.type),
        title=row.title,
        summary=row.summary,
        metadata=row.node_metadata,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def edge_entity(row: RelationshipModel) -> GraphRelationship:
    return GraphRelationship(
        id=row.id,
        universe_id=row.universe_id,
        continuity_id=row.continuity_id,
        source_node_id=row.source_node_id,
        target_node_id=row.target_node_id,
        relationship_type=RelationshipType(row.relationship_type),
        description=row.description,
    )


class SqlUniverseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Universe]:
        rows = await self.session.scalars(select(UniverseModel).order_by(UniverseModel.title))
        return [universe_entity(row) for row in rows]

    async def get_by_slug(self, slug: str) -> Universe | None:
        row = await self.session.scalar(select(UniverseModel).where(UniverseModel.slug == slug))
        return universe_entity(row) if row else None


class SqlGraphRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_continuities(self, universe_id: UUID) -> list[Continuity]:
        rows = await self.session.scalars(
            select(ContinuityModel)
            .where(ContinuityModel.universe_id == universe_id)
            .order_by(ContinuityModel.name)
        )
        return [
            Continuity(
                id=r.id,
                universe_id=r.universe_id,
                name=r.name,
                medium=r.medium,
                description=r.description,
            )
            for r in rows
        ]

    async def get_nodes(self, universe_id: UUID) -> list[GraphNode]:
        rows = await self.session.scalars(
            select(NodeModel).where(NodeModel.universe_id == universe_id).order_by(NodeModel.title)
        )
        return [node_entity(r) for r in rows]

    async def get_edges(self, universe_id: UUID) -> list[GraphRelationship]:
        rows = await self.session.scalars(
            select(RelationshipModel)
            .where(RelationshipModel.universe_id == universe_id)
            .order_by(RelationshipModel.id)
        )
        return [edge_entity(r) for r in rows]

    async def get_node(self, node_id: UUID) -> GraphNode | None:
        row = await self.session.get(NodeModel, node_id)
        return node_entity(row) if row else None

    async def get_incident_edges(self, node_id: UUID) -> list[GraphRelationship]:
        rows = await self.session.scalars(
            select(RelationshipModel)
            .where(
                or_(
                    RelationshipModel.source_node_id == node_id,
                    RelationshipModel.target_node_id == node_id,
                )
            )
            .order_by(RelationshipModel.id)
        )
        return [edge_entity(r) for r in rows]
