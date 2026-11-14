import json
import re
from dataclasses import replace
from uuid import UUID

from src.application.evidence_dossier import token_estimate
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
            rows_added = len(pending)
            generate = []
            groups: dict[str, list[EvidenceHit]] = {}
            for h in pending:
                cached = await repo.cached_vector(
                    universe, continuity, model, h.passage.content_hash
                )
                if cached is not None:
                    await repo.store(h, model, cached)
                else:
                    group = groups.setdefault(h.passage.content_hash, [])
                    group.append(h)
                    if len(group) == 1:
                        generate.append(h)
            pending = generate
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
                    for duplicate in groups[h.passage.content_hash]:
                        await repo.store(duplicate, model, vector)
        return {
            "indexed": len(pending),
            "reused": len(passages) - len(pending),
            "model_key": model.key,
            "dimensions": model.dimensions,
            "rows_added": rows_added,
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
        token_budget: int | None = None,
    ) -> list[EvidenceHit]:
        limit = min(max(limit, 1), 64)
        async with self.transactions() as repo:
            metadata = await repo.source_metadata(universe, continuity, allowed_sources)
        metadata = {
            identifier: value
            for identifier, value in metadata.items()
            if (
                spoiler_position is None
                or (
                    isinstance(value.get("presentation_position"), int)
                    and value["presentation_position"] <= spoiler_position
                )
            )
            and (not authorities or value.get("authority", "unverified") in authorities)
        }
        if not metadata:
            return []
        eligible_sources = list(metadata)
        async with self.transactions() as repo:
            lexical = await repo.passages(
                universe, continuity, eligible_sources, query=" ".join(names or []) + " " + query
            )
        model = await self.embeddings.identity()
        vector = (await self.embeddings.embed([query[:2000]]))[0]
        async with self.transactions() as repo:
            semantic = await repo.nearest(
                universe,
                continuity,
                model,
                vector,
                max(40, limit * 2),
                eligible_sources,
                authorities or [],
            )
        semantic = [
            replace(h, source=replace(h.source, provenance=metadata[h.source.id]))
            for h in semantic
            if h.source.id in metadata
        ]
        words = set(re.findall(r"\w+", query.casefold()))

        def lexical_score(h: EvidenceHit) -> int:
            headings = " ".join(
                s["title"]
                for s in json.loads(h.source.provenance.get("sections_json", "[]"))
                if s["start"] <= h.passage.start < s["end"]
            )
            text = (h.passage.text + " " + headings).casefold()
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
        )[: max(40, limit * 2)]
        # Reciprocal rank fusion gives exact names their own route into the evidence set.
        scores: dict[UUID, float] = {}
        values: dict[UUID, EvidenceHit] = {}
        for ranking in (semantic, lexical):
            for rank, h in enumerate(ranking):
                scores[h.passage.id] = scores.get(h.passage.id, 0) + 1 / (20 + rank)
                values.setdefault(h.passage.id, h)
        for identifier, hit in list(values.items()):
            title = next(
                (
                    s["title"]
                    for s in reversed(json.loads(hit.source.provenance.get("sections_json", "[]")))
                    if s["start"] <= hit.passage.start < s["end"]
                ),
                "",
            )
            values[identifier] = replace(hit, passage=replace(hit.passage, section_title=title))
        ordered = sorted(values.values(), key=lambda h: (-scores[h.passage.id], str(h.passage.id)))
        chosen: list[EvidenceHit] = []
        hashes: set[str] = set()
        counts: dict[UUID, int] = {}
        used_tokens = 0
        seen_families: dict[str, int] = {}
        while ordered:

            def value(hit: EvidenceHit) -> float:
                family = hit.source.independence_key or hit.source.publisher
                return scores[hit.passage.id] / (1 + seen_families.get(family, 0) * 0.25)

            h = max(ordered, key=value)
            ordered.remove(h)
            cost = token_estimate(h.passage.text)
            if (
                h.passage.content_hash in hashes
                or token_budget is None
                and counts.get(h.source.id, 0) >= 3
                or token_budget is not None
                and used_tokens + cost > token_budget
            ):
                continue
            chosen.append(h)
            hashes.add(h.passage.content_hash)
            counts[h.source.id] = counts.get(h.source.id, 0) + 1
            used_tokens += cost
            family = h.source.independence_key or h.source.publisher
            seen_families[family] = seen_families.get(family, 0) + 1
            if len(chosen) == limit:
                break
        return chosen
