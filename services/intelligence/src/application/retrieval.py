import re
from uuid import UUID

from src.application.ports.retrieval import EmbeddingProvider, EvidenceHit, EvidenceIndexTransaction


class EvidenceRetrieval:
    def __init__(
        self, transactions: EvidenceIndexTransaction, embeddings: EmbeddingProvider
    ) -> None:
        self.transactions, self.embeddings = transactions, embeddings

    async def index(
        self, universe: UUID, continuity: UUID, source_ids: list[UUID] | None = None
    ) -> dict[str, int | str]:
        model = await self.embeddings.identity()
        async with self.transactions() as repo:
            passages = await repo.passages(universe, continuity, source_ids)
            pending = [
                h
                for h in passages
                if not await repo.indexed(h.passage.id, model, h.passage.content_hash)
            ]
        # No held transaction during embedding; small sequential batches unload after use.
        for offset in range(0, len(pending), 4):
            batch = pending[offset : offset + 4]
            vectors = await self.embeddings.embed([h.passage.text for h in batch])
            if await self.embeddings.identity() != model:
                raise ValueError(
                    "Embedding model changed during indexing; retry under its new identity"
                )
            if len(vectors) != len(batch):
                raise ValueError("Embedding batch count mismatch")
            async with self.transactions() as repo:
                for h, vector in zip(batch, vectors, strict=True):
                    await repo.store(h, model, vector)
        return {
            "indexed": len(pending),
            "reused": len(passages) - len(pending),
            "model_key": model.key,
            "dimensions": model.dimensions,
        }

    async def retrieve(
        self,
        universe: UUID,
        continuity: UUID,
        query: str,
        *,
        names: list[str] | None = None,
        allowed_sources: list[UUID] | None = None,
        authorities: list[str] | None = None,
        limit: int = 8,
        spoiler_position: int | None = None,
    ) -> list[EvidenceHit]:
        limit = min(max(limit, 1), 16)
        model = await self.embeddings.identity()
        vector = (await self.embeddings.embed([query[:2000]]))[0]
        async with self.transactions() as repo:
            if spoiler_position is not None:
                permitted = await repo.passages(universe, continuity, allowed_sources)
                allowed_sources = list(
                    {
                        h.source.id
                        for h in permitted
                        if isinstance(h.source.provenance.get("presentation_position"), int)
                        and h.source.provenance["presentation_position"] <= spoiler_position
                    }
                )
            semantic = await repo.nearest(
                universe, continuity, model, vector, 40, allowed_sources, authorities or []
            )
            lexical = await repo.passages(universe, continuity, allowed_sources)
        words = set(re.findall(r"\w+", query.casefold()))

        def lexical_score(h: EvidenceHit) -> int:
            text = h.passage.text.casefold()
            return 5 * sum(n.casefold() in text for n in (names or [])) + sum(
                w in text for w in words
            )

        lexical = sorted(
            [
                h
                for h in lexical
                if lexical_score(h)
                and (
                    not authorities
                    or h.source.provenance.get("authority", "unverified") in authorities
                )
            ],
            key=lambda h: (-lexical_score(h), str(h.passage.id)),
        )[:40]
        # Reciprocal rank fusion gives exact names their own route into the evidence set.
        scores: dict[UUID, float] = {}
        values = {}
        for ranking in (semantic, lexical):
            for rank, h in enumerate(ranking):
                scores[h.passage.id] = scores.get(h.passage.id, 0) + 1 / (20 + rank)
                values[h.passage.id] = h
        ordered = sorted(values.values(), key=lambda h: (-scores[h.passage.id], str(h.passage.id)))
        chosen: list[EvidenceHit] = []
        hashes: set[str] = set()
        counts: dict[UUID, int] = {}
        for h in ordered:
            if h.passage.content_hash in hashes or counts.get(h.source.id, 0) >= 3:
                continue
            chosen.append(h)
            hashes.add(h.passage.content_hash)
            counts[h.source.id] = counts.get(h.source.id, 0) + 1
            if len(chosen) == limit:
                break
        return chosen
