import json
import re
from dataclasses import replace
from typing import Any
from uuid import UUID

from src.application.arc_contracts import DevelopmentEvidence
from src.application.event_extraction import evidence_units
from src.application.evidence_bundles import EvidenceBundleBuilder
from src.application.evidence_dossier import token_estimate
from src.application.ports.retrieval import (
    ArcPassageSet,
    ArcSource,
    EmbeddingProvider,
    EvidenceHit,
    EvidenceIndexTransaction,
)
from src.application.relationship_contracts import EvidenceBundle, InvestigationSubject
from src.domain.research import digest


def sentence_evidence(
    hit: EvidenceHit, sentence: dict[str, Any], meta: dict[str, Any]
) -> DevelopmentEvidence | None:
    """Stable, exact-offset sentence evidence; None if the archive coordinates drifted."""
    start = hit.passage.start + sentence["start"]
    text = sentence["text"]
    if hit.source.text[start : start + len(text)] != text:
        return None
    return DevelopmentEvidence(
        id=digest(f"{hit.source.id}:{hit.source.content_hash}:{start}:{text}"),
        source_id=hit.source.id,
        source_hash=hit.source.content_hash,
        passage_id=hit.passage.id,
        passage_hash=hit.passage.content_hash,
        passage_start=hit.passage.start,
        start=start,
        end=start + len(text),
        text=text,
        eligibility_boundary=meta.get("presentation_position"),
        position_basis=meta.get("position_basis"),
        authority=meta.get("authority"),
        source_group=str(
            meta.get("derived_from") or hit.source.independence_key or hit.source.publisher
        ),
    )


class EvidenceRetrieval:
    def __init__(
        self, transactions: EvidenceIndexTransaction, embeddings: EmbeddingProvider
    ) -> None:
        self.transactions, self.embeddings = transactions, embeddings

    async def development_evidence(
        self,
        universe: UUID,
        continuity: UUID,
        facts: list[dict[str, Any]],
        spoiler_position: int | None,
        token_budget: int = 3200,
    ) -> tuple[list[DevelopmentEvidence], list[str]]:
        """Exact archived support plus neighboring context; no embedding/model call."""
        identifiers = list({UUID(s["id"]) for f in facts for s in f.get("sources", [])})
        async with self.transactions() as repo:
            metadata = await repo.source_metadata(universe, continuity, identifiers)
            hits = await repo.passages(universe, continuity, identifiers)
        eligible = {
            str(h.passage.id): h
            for h in hits
            if h.source.id in metadata
            and h.source.universe_id == universe
            and h.source.continuity_id == continuity
            and metadata[h.source.id].get("content_hash") == h.source.content_hash
            and (
                spoiler_position is None
                or (
                    type(metadata[h.source.id].get("presentation_position")) is int
                    and metadata[h.source.id]["presentation_position"] <= spoiler_position
                )
            )
        }
        citations = [s for f in facts for s in f.get("sources", [])]
        issues = []
        anchors: dict[str, list[tuple[int, int]]] = {}
        for citation in citations:
            hit = eligible.get(citation.get("passage_id"))
            if not hit or str(hit.source.id) != citation["id"]:
                issues.append("missing_or_ineligible_archived_evidence")
                continue
            start, end = citation.get("quote_start"), citation.get("quote_end")
            if (
                type(start) is not int
                or type(end) is not int
                or not 0 <= start < end <= len(hit.passage.text)
                or hit.passage.text[start:end] != citation.get("quote")
                or hit.source.content_hash != citation.get("content_hash")
            ):
                issues.append("changed_or_inexact_archived_evidence")
                continue
            anchors.setdefault(str(hit.passage.id), []).append((start, end))
        selected = []
        for passage_id, spans in anchors.items():
            hit = eligible[passage_id]
            units = evidence_units([hit.passage])
            direct = {
                i
                for i, u in enumerate(units)
                if any(
                    u["start"] < end and u["start"] + len(u["text"]) > start for start, end in spans
                )
            }
            neighbors = {j for i in direct for j in (i - 1, i, i + 1) if 0 <= j < len(units)}
            for i in neighbors:
                evidence = sentence_evidence(hit, units[i], metadata[hit.source.id])
                if evidence is None:
                    issues.append("archive_coordinates_do_not_match_document")
                    continue
                selected.append((i not in direct, evidence))
        result: list[DevelopmentEvidence] = []
        used = 0
        for context, unit in sorted(
            selected, key=lambda pair: (pair[0], str(pair[1].source_id), pair[1].start)
        ):
            size = token_estimate(unit.text)
            if used + size > token_budget:
                if not context:
                    issues.append("direct_evidence_exceeds_context_budget")
                continue
            used += size
            result.append(unit)
        return sorted(result, key=lambda u: (str(u.source_id), u.start)), sorted(set(issues))

    async def arc_passages(
        self,
        universe: UUID,
        continuity: UUID,
        *,
        first_position: int,
        last_position: int,
        position_basis: str,
        spoiler_position: int | None,
        allowed_sources: list[UUID] | None = None,
    ) -> ArcPassageSet:
        """Every permitted archived sentence of the arc, ordered by source presentation.

        Registry permission, arc bounds and the spoiler boundary are applied here, before
        any text can reach inference. Order is presentation order, not story chronology.
        """
        ceiling = (
            last_position if spoiler_position is None else min(last_position, spoiler_position)
        )
        async with self.transactions() as repo:
            metadata = await repo.source_metadata(universe, continuity, allowed_sources)
            chosen = [
                identifier
                for identifier, meta in metadata.items()
                if meta.get("position_basis") == position_basis
                and type(meta.get("presentation_position")) is int
                and first_position <= meta["presentation_position"] <= ceiling
            ]
            hits = await repo.passages(universe, continuity, chosen) if chosen else []
        issues: list[str] = []
        by_source: dict[UUID, list[EvidenceHit]] = {}
        for hit in hits:
            meta = metadata.get(hit.source.id)
            if (
                meta is None
                or hit.source.id not in chosen
                or hit.source.universe_id != universe
                or hit.source.continuity_id != continuity
                or meta.get("content_hash") != hit.source.content_hash
            ):
                continue
            by_source.setdefault(hit.source.id, []).append(hit)
        sources: list[ArcSource] = []
        sentences: list[DevelopmentEvidence] = []
        ordered = sorted(
            by_source.values(),
            key=lambda group: (
                metadata[group[0].source.id]["presentation_position"],
                group[0].source.title,
                str(group[0].source.id),
            ),
        )
        for group in ordered:
            source = group[0].source
            meta = metadata[source.id]
            sources.append(
                ArcSource(
                    id=source.id,
                    label=source.title,
                    position=meta["presentation_position"],
                    position_basis=position_basis,
                    authority=meta.get("authority"),
                    source_group=str(
                        meta.get("derived_from") or source.independence_key or source.publisher
                    ),
                    cloud_eligible=bool(
                        (meta.get("public_web") and meta.get("cloud_content_allowed"))
                        or meta.get("import_cloud_allowed")
                    ),
                )
            )
            for hit in sorted(group, key=lambda h: h.passage.ordinal):
                for unit in evidence_units([hit.passage]):
                    evidence = sentence_evidence(hit, unit, meta)
                    if evidence is None:
                        issues.append("archive_coordinates_do_not_match_document")
                    else:
                        sentences.append(evidence)
        if not sources:
            issues.append("no_permitted_archived_sources_in_arc_range")
        return ArcPassageSet(sentences, sources, sorted(set(issues)))

    async def bundles(
        self,
        universe: UUID,
        continuity: UUID,
        objective: str,
        subjects: list[InvestigationSubject],
        *,
        spoiler_position: int | None,
        token_budget: int,
    ) -> tuple[list[EvidenceBundle], list[EvidenceHit]]:
        names = list(dict.fromkeys(n for s in subjects for n in [s.name, *s.aliases]))
        anchors = await self.retrieve(
            universe,
            continuity,
            objective,
            names=names,
            limit=64,
            spoiler_position=spoiler_position,
            token_budget=token_budget * 3,
        )
        async with self.transactions() as repo:
            neighbors = await repo.neighbors([h.passage.id for h in anchors])
            metadata = await repo.source_metadata(universe, continuity)
        eligible = {h.passage.id: h for h in [*anchors, *neighbors] if h.source.id in metadata}
        hits = []
        for h in eligible.values():
            provenance = metadata[h.source.id]
            title = next(
                (
                    s["title"]
                    for s in reversed(json.loads(provenance.get("sections_json", "[]")))
                    if s["start"] <= h.passage.start < s["end"]
                ),
                "",
            )
            hits.append(
                replace(
                    h,
                    source=replace(h.source, provenance=provenance),
                    passage=replace(h.passage, section_title=title),
                )
            )
        bundles = EvidenceBundleBuilder().build(
            hits, subjects, objective, continuity, spoiler_position, token_budget
        )
        selected = {p.passage_id for b in bundles for p in b.passages}
        return bundles, [h for h in hits if h.passage.id in selected]

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
        lexical = [
            replace(h, source=replace(h.source, provenance=metadata[h.source.id]))
            for h in lexical
            if h.source.id in metadata
        ]
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
                authority = {"primary": 1.6, "secondary": 1.0, "unverified": 0.7}.get(
                    hit.source.provenance.get("authority", "unverified"), 0.7
                )
                return (
                    scores[hit.passage.id] * authority / (1 + seen_families.get(family, 0) * 0.15)
                )

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
