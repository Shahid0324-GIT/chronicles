"""Functional additional roles composed into the existing StateGraph."""

import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel

from src.application.event_extraction import evidence_units
from src.application.identity import IdentityResolver
from src.application.knowledge_contracts import IndexedRelationships, RelationshipAnalysis
from src.application.ports.knowledge import KnowledgeTransaction
from src.application.promotion import CanonicalGraphPromotionService
from src.application.research_contracts import Citation, Extraction, InferenceFailure, Task
from src.domain.knowledge import name_key, short_name_bridge, source_name_bridge
from src.domain.research import SourcePassage, digest

InferRole = Callable[[str, type[BaseModel], Task], Awaitable[BaseModel]]


class KnowledgePipeline:
    def __init__(
        self, transactions: KnowledgeTransaction, promotion: CanonicalGraphPromotionService
    ) -> None:
        self.transactions, self.promotion = transactions, promotion
        self.resolver = IdentityResolver()

    async def ground_aliases(
        self, job_id: UUID, extraction: Extraction, passages: list[SourcePassage]
    ) -> Extraction:
        async with self.transactions() as unit:
            job = await unit.archive.get_job(job_id)
            assert job
            catalog = await unit.graph.catalog(UUID(job["universe_id"]), UUID(job["continuity_id"]))
        units = evidence_units(passages)
        entities = []
        for entity in extraction.entities:
            evidence = list(entity.evidence)
            if entity.type.value == "CHARACTER":
                for node in catalog:
                    if node["type"] != "CHARACTER":
                        continue
                    for name in [node["name"], *node.get("aliases", [])]:
                        quotes = [c.quote for c in evidence]
                        if source_name_bridge(entity.name, name, quotes):
                            continue
                        other = next(
                            (
                                u
                                for u in units
                                if name_key(name) in name_key(u["text"])
                                and (
                                    source_name_bridge(entity.name, name, [*quotes, u["text"]])
                                    or short_name_bridge(entity.name, name, [*quotes, u["text"]])
                                )
                            ),
                            None,
                        )
                        if other and len(evidence) < 3:
                            evidence.append(
                                Citation(passage_id=other["passage_id"], quote=other["text"])
                            )
            entities.append(entity.model_copy(update={"evidence": evidence}))
        return extraction.model_copy(update={"entities": entities})

    async def resolve(
        self,
        job_id: UUID,
        candidates: list[dict[str, Any]],
        passages: list[SourcePassage],
        infer: InferRole,
        grounded: bool = False,
    ) -> dict[str, dict[str, Any]]:
        async with self.transactions() as unit:
            job = await unit.archive.get_job(job_id)
            assert job
            continuity = UUID(job["continuity_id"])
            catalog = await unit.graph.catalog(UUID(job["universe_id"]), continuity)
        results: dict[str, dict[str, Any]] = {}
        ordered = sorted(
            candidates, key=lambda c: c["kind"] != "entity" or c["payload"].get("type") == "EVENT"
        )
        for claim in ordered:
            if claim["kind"] != "entity":
                continue

            async def compare(prompt: str, schema: type[BaseModel]) -> BaseModel:
                return await infer(prompt, schema, "identity_resolution")

            try:
                actors = (claim["payload"].get("event") or {}).get("participants", [])
                participant_ids = list(
                    {
                        results[c["id"]]["canonical_id"]
                        for c in candidates
                        if c["kind"] == "entity"
                        and c["payload"]["name"] in actors
                        and results.get(c["id"], {}).get("accepted")
                    }
                )
                decision = await self.resolver.resolve(
                    claim,
                    catalog,
                    passages,
                    compare,
                    continuity,
                    indexed_evidence=grounded,
                    participant_ids=participant_ids,
                )
            except InferenceFailure:
                decision = {
                    "decision": "AMBIGUOUS",
                    "accepted": False,
                    "canonical_id": None,
                    "evidence": [],
                    "proof": "unresolved",
                    "reason": "Identity inference failed bounded validation; no match accepted.",
                }
            results[claim["id"]] = decision
            if decision["accepted"] and decision["decision"] in {"NEW_ENTITY", "DIFFERENT_ENTITY"}:
                catalog.append({"id": decision["canonical_id"], **claim["payload"], "aliases": []})
            elif decision["accepted"]:
                target = next((n for n in catalog if n["id"] == decision["canonical_id"]), None)
                if target is not None:
                    target.setdefault("aliases", []).append(claim["payload"]["name"])
        return results

    async def relationships(
        self,
        job_id: UUID,
        candidates: list[dict[str, Any]],
        resolutions: dict[str, dict[str, Any]],
        passages: list[SourcePassage],
        infer: InferRole,
        grounded: bool = False,
    ) -> list[dict[str, Any]]:
        resolved = [
            {
                "claim_id": c["id"],
                "canonical_id": resolutions[c["id"]]["canonical_id"],
                "name": c["payload"]["name"],
                "type": c["payload"]["type"],
            }
            for c in candidates
            if c["kind"] == "entity" and resolutions.get(c["id"], {}).get("accepted")
        ]
        if len(resolved) < 2:
            return candidates
        if grounded:
            units = evidence_units(passages)
            prompt = (
                "Propose only explicit typed relationships among these indexed identities. "
                "Refer to source_index and target_index exactly; cite supplied sentence_ids, "
                "never invent quotation text or entity IDs. PARTICIPATED_IN must target EVENT; "
                "OCCURRED_AT is EVENT to LOCATION. PRECEDES is chronology only, not causality. "
                "CAUSED/ENABLED require explicit cause/effect and two EVENT endpoints. "
                "Use short literal descriptions in the source language. No inferred alliances "
                "or future revelations. Return empty when evidence is insufficient.\n"
                + json.dumps(
                    {
                        "identities": [{**n, "index": i} for i, n in enumerate(resolved)],
                        "sentences": units,
                    },
                    ensure_ascii=False,
                )
            )
            answer = IndexedRelationships.model_validate(
                (await infer(prompt, IndexedRelationships, "relationship_analysis")).model_dump()
            )
            relationships = []
            for r in answer.relationships:
                if max(r.source_index, r.target_index) >= len(resolved):
                    continue
                cited = [u for u in units if u["id"] in r.sentence_ids]
                if len(cited) != len(set(r.sentence_ids)):
                    continue
                relationships.append(
                    {
                        "source_name": resolved[r.source_index]["name"],
                        "target_name": resolved[r.target_index]["name"],
                        "source_id": resolved[r.source_index]["canonical_id"],
                        "target_id": resolved[r.target_index]["canonical_id"],
                        "type": r.type.value,
                        "description": r.description,
                        "evidence": [
                            {"passage_id": u["passage_id"], "quote": u["text"]} for u in cited
                        ],
                    }
                )
            analysis = RelationshipAnalysis.model_validate({"relationships": relationships})
        else:
            analysis = await self._free_relationships(resolved, passages, infer)
        result = []
        for candidate in candidates:
            if grounded and candidate["kind"] == "relationship":
                payload = dict(candidate["payload"])
                for endpoint in ("source", "target"):
                    matches = [
                        r["canonical_id"]
                        for r in resolved
                        if r["name"] == payload[endpoint + "_name"]
                    ]
                    if len(set(matches)) == 1:
                        payload[endpoint + "_id"] = matches[0]
                key = digest(
                    json.dumps(
                        {"kind": "relationship", "payload": payload},
                        sort_keys=True,
                        ensure_ascii=False,
                    )
                )
                candidate = {
                    **candidate,
                    "id": str(uuid5(job_id, key)),
                    "hash": key,
                    "payload": payload,
                }
            result.append(candidate)
        hashes = {c["hash"] for c in result}
        for value in analysis.relationships:
            payload = value.model_dump(mode="json")
            fingerprint = digest(
                json.dumps(
                    {"kind": "relationship", "payload": payload}, sort_keys=True, ensure_ascii=False
                )
            )
            if fingerprint not in hashes:
                result.append(
                    {
                        "id": str(uuid5(job_id, fingerprint)),
                        "kind": "relationship",
                        "hash": fingerprint,
                        "payload": payload,
                    }
                )
                hashes.add(fingerprint)
        return result[:24]

    async def _free_relationships(
        self, resolved: list[dict[str, Any]], passages: list[SourcePassage], infer: InferRole
    ) -> RelationshipAnalysis:
        prompt = """Analyze explicit typed relationships.
Use only the resolved identities and passages.
Use exact source_name and target_name from identities.
Return at most 6 relationships with exact citations.
PARTICIPATED_IN targets EVENT, OCCURRED_AT connects EVENT to LOCATION, MEMBER_OF targets FACTION.
CAUSED and ENABLED connect EVENT to EVENT; CAUSED requires an explicit causal statement.
PRECEDES is order only. FORESHADOWS is not causation. Omit invented or unsupported connections.
Use source-language descriptions.
Include a candidate causal link only if the source actually asserts it.
Return an empty list when appropriate.
""" + json.dumps(
            {
                "identities": resolved,
                "passages": [{"id": str(p.id), "text": p.text} for p in passages],
            },
            ensure_ascii=False,
        )
        return RelationshipAnalysis.model_validate(
            (await infer(prompt, RelationshipAnalysis, "relationship_analysis")).model_dump()
        )
