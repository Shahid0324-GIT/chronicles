"""Draft story packs and their graph records. Callers own the transaction."""

from dataclasses import asdict
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.knowledge_presentation import fingerprint
from src.application.story_pack import StoryPack, graph, storage_id
from src.infrastructure.persistence.models import (
    ContinuityModel,
    NodeModel,
    RelationshipModel,
    UniverseModel,
)
from src.infrastructure.persistence.presentation_repository import SqlPresentationRepository

POLICY = "story-pack-v1"


class SqlStoryPackStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.presentations = SqlPresentationRepository(session)

    async def load(self, universe: UUID, continuity: UUID) -> StoryPack | None:
        saved = await self.presentations.get(storage_id(universe, continuity))
        return StoryPack.model_validate(saved["payload"]) if saved else None

    async def publish(self, pack: StoryPack) -> dict[str, int]:
        """Replace the draft world's graph with this pack. Other worlds are never touched."""
        universe, continuity, nodes, edges = graph(pack)
        existing = await self.session.scalar(
            select(UniverseModel).where(UniverseModel.slug == pack.slug)
        )
        if existing is not None and existing.id != universe.id:
            raise ValueError(f"Slug {pack.slug} belongs to a world that is not this draft")
        if existing is None:
            values = asdict(universe)
            values["slug"] = str(universe.slug)
            self.session.add(UniverseModel(**values))
        else:
            existing.title, existing.description = universe.title, universe.description
            existing.updated_at = universe.updated_at
        await self.session.flush()
        saved = await self.session.get(ContinuityModel, continuity.id)
        if saved is None:
            self.session.add(ContinuityModel(**asdict(continuity)))
        else:
            saved.name, saved.medium = continuity.name, continuity.medium
            saved.description = continuity.description
        await self.session.flush()
        # Only rows of this draft world: its id is derived from its "-draft" slug.
        await self.session.execute(
            delete(RelationshipModel).where(RelationshipModel.universe_id == universe.id)
        )
        await self.session.execute(delete(NodeModel).where(NodeModel.universe_id == universe.id))
        for node in nodes:
            row = asdict(node)
            row["type"] = node.type.value
            row["node_metadata"] = row.pop("metadata")
            self.session.add(NodeModel(**row))
        await self.session.flush()
        for edge in edges:
            row = asdict(edge)
            row["relationship_type"] = edge.relationship_type.value
            self.session.add(RelationshipModel(**row))
        await self.session.flush()
        payload = pack.model_dump(mode="json")
        revision = fingerprint(payload)
        await self.presentations.save(
            storage_id(universe.id, continuity.id),
            universe.id,
            continuity.id,
            continuity.id,
            "story_pack",
            "full",
            revision,
            revision,
            "en",
            POLICY,
            payload,
            "draft",
            [],
        )
        return {"nodes": len(nodes), "relationships": len(edges)}
