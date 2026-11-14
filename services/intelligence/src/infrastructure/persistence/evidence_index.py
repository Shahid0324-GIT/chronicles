import math
import re
from dataclasses import replace
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import case, literal, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from src.application.ports.retrieval import EmbeddingIdentity, EvidenceHit
from src.domain.research import SourcePassage
from src.infrastructure.persistence.models.research import SourceDocumentModel, SourcePassageModel
from src.infrastructure.persistence.models.source_intelligence import (
    PassageEmbeddingModel,
    SourceRegistryModel,
)
from src.infrastructure.persistence.research_repository import source_entity


def hit(
    p: SourcePassageModel, s: SourceDocumentModel, distance: float | None = None
) -> EvidenceHit:
    return EvidenceHit(
        SourcePassage(p.id, p.source_id, p.ordinal, p.start, p.end, p.text, p.content_hash),
        source_entity(s),
        distance,
    )


class SqlEvidenceIndex:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def source_metadata(
        self, universe: UUID, continuity: UUID, source_ids: list[UUID] | None = None
    ) -> dict[UUID, dict[str, Any]]:
        registry = {
            str(row.id): row.configuration
            for row in await self.session.scalars(
                select(SourceRegistryModel).where(SourceRegistryModel.universe_id == universe)
            )
        }
        query = select(
            SourceDocumentModel.id, SourceDocumentModel.provenance, SourceDocumentModel.public_web
        ).where(
            SourceDocumentModel.universe_id == universe,
            SourceDocumentModel.continuity_id == continuity,
        )
        if source_ids is not None:
            query = query.where(SourceDocumentModel.id.in_(source_ids))
        values = {}
        for identifier, provenance, public in (await self.session.execute(query)).all():
            registration = provenance.get("registry_id")
            policy = registry.get(registration, {})
            if registration and (
                policy.get("retrieval_policy") != "permitted"
                or str(continuity) not in policy.get("continuity_ids", [])
            ):
                continue
            values[identifier] = {
                **provenance,
                "public_web": public,
                "cloud_content_allowed": bool(
                    public and policy.get("cloud_content_allowed", False)
                ),
            }
        return values

    async def cached_vector(
        self, universe: UUID, continuity: UUID, model: EmbeddingIdentity, content_hash: str
    ) -> list[float] | None:
        row = await self.session.scalar(
            select(PassageEmbeddingModel)
            .where(
                PassageEmbeddingModel.universe_id == universe,
                PassageEmbeddingModel.continuity_id == continuity,
                PassageEmbeddingModel.model_key == model.key,
                PassageEmbeddingModel.dimensions == model.dimensions,
                PassageEmbeddingModel.content_hash == content_hash,
            )
            .limit(1)
        )
        return [float(v) for v in row.vector] if row else None

    async def passages(
        self,
        universe: UUID,
        continuity: UUID,
        source_ids: list[UUID] | None = None,
        query: str | None = None,
    ) -> list[EvidenceHit]:
        q = (
            select(SourcePassageModel, SourceDocumentModel)
            .join(SourceDocumentModel, SourceDocumentModel.id == SourcePassageModel.source_id)
            .where(
                SourceDocumentModel.universe_id == universe,
                SourceDocumentModel.continuity_id == continuity,
            )
        )
        if source_ids is not None:
            q = q.where(SourceDocumentModel.id.in_(source_ids))
        score: ColumnElement[int] | None = None
        if query:
            words = list(dict.fromkeys(re.findall(r"\w+", query.casefold())))[:20]
            if words:
                score = sum(
                    (
                        case((SourcePassageModel.text.icontains(word, autoescape=True), 1), else_=0)
                        for word in words
                    ),
                    literal(0),
                )
                q = q.where(score > 0)
        registered = {
            str(r.id): r.configuration
            for r in await self.session.scalars(
                select(SourceRegistryModel).where(SourceRegistryModel.universe_id == universe)
            )
            if r.configuration.get("retrieval_policy") == "permitted"
            and str(continuity) in r.configuration.get("continuity_ids", [])
        }
        return [
            replace(
                hit(p, s),
                source=replace(
                    source_entity(s),
                    provenance={
                        **s.provenance,
                        "cloud_content_allowed": registered.get(
                            s.provenance.get("registry_id"), {}
                        ).get("cloud_content_allowed", False),
                    },
                ),
            )
            for p, s in (
                await self.session.execute(
                    q.order_by(
                        *([score.desc()] if score is not None else []),
                        SourceDocumentModel.retrieved_at.desc(),
                        SourcePassageModel.ordinal,
                    ).limit(600)
                )
            ).all()
            if not s.provenance.get("registry_id") or s.provenance["registry_id"] in registered
        ]

    async def indexed(self, passage: UUID, model: EmbeddingIdentity, content_hash: str) -> bool:
        row = await self.session.scalar(
            select(PassageEmbeddingModel).where(
                PassageEmbeddingModel.passage_id == passage,
                PassageEmbeddingModel.model_key == model.key,
                PassageEmbeddingModel.content_hash == content_hash,
            )
        )
        return row is not None

    async def store(
        self, value: EvidenceHit, model: EmbeddingIdentity, vector: list[float]
    ) -> None:
        if (
            len(vector) != model.dimensions
            or not all(math.isfinite(v) for v in vector)
            or not any(vector)
        ):
            raise ValueError("Invalid vector for model dimensions")
        identifier = uuid5(value.passage.id, model.key)
        row = await self.session.get(PassageEmbeddingModel, identifier)
        if row and row.content_hash == value.passage.content_hash:
            return
        if row:
            row.vector, row.content_hash = vector, value.passage.content_hash
        else:
            self.session.add(
                PassageEmbeddingModel(
                    id=identifier,
                    passage_id=value.passage.id,
                    universe_id=value.source.universe_id,
                    continuity_id=value.source.continuity_id,
                    model_key=model.key,
                    dimensions=model.dimensions,
                    content_hash=value.passage.content_hash,
                    vector=vector,
                )
            )
        await self.session.flush()

    async def nearest(
        self,
        universe: UUID,
        continuity: UUID,
        model: EmbeddingIdentity,
        vector: list[float],
        limit: int,
        allowed_sources: list[UUID] | None,
        authorities: list[str],
    ) -> list[EvidenceHit]:
        if len(vector) != model.dimensions:
            raise ValueError("Query embedding dimension mismatch")
        q = (
            select(PassageEmbeddingModel, SourcePassageModel, SourceDocumentModel)
            .join(SourcePassageModel, SourcePassageModel.id == PassageEmbeddingModel.passage_id)
            .join(SourceDocumentModel, SourceDocumentModel.id == SourcePassageModel.source_id)
            .where(
                PassageEmbeddingModel.universe_id == universe,
                PassageEmbeddingModel.continuity_id == continuity,
                PassageEmbeddingModel.model_key == model.key,
                PassageEmbeddingModel.dimensions == model.dimensions,
                PassageEmbeddingModel.content_hash == SourcePassageModel.content_hash,
            )
        )
        if allowed_sources is not None:
            q = q.where(SourceDocumentModel.id.in_(allowed_sources))
        if authorities:
            q = q.where(SourceDocumentModel.provenance["authority"].as_string().in_(authorities))
        # Actual PostgreSQL cosine distance; SQLite is an explicitly synthetic-test adapter.
        if self.session.bind and self.session.bind.dialect.name == "postgresql":
            distance = PassageEmbeddingModel.vector.cosine_distance(vector)
            q = q.order_by(distance).limit(min(limit * 4, 200))
        rows = (await self.session.execute(q)).all()
        scored = []
        norm = math.sqrt(sum(x * x for x in vector))
        for embedding, passage, source in rows:
            if authorities and source.provenance.get("authority", "unverified") not in authorities:
                continue
            v = embedding.vector
            distance_value = 1 - sum(a * b for a, b in zip(vector, v, strict=True)) / (
                norm * math.sqrt(sum(x * x for x in v))
            )
            scored.append(hit(passage, source, float(distance_value)))
        return sorted(scored, key=lambda h: (h.distance or 0, str(h.passage.id)))[:limit]
