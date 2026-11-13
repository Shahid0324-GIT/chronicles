"""Functional additional roles composed into the existing StateGraph."""

import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel

from src.application.identity import IdentityResolver
from src.application.knowledge_contracts import RelationshipAnalysis
from src.application.ports.knowledge import KnowledgeTransaction
from src.application.promotion import CanonicalGraphPromotionService
from src.application.research_contracts import InferenceFailure, Task
from src.domain.research import SourcePassage, digest

InferRole = Callable[[str, type[BaseModel], Task], Awaitable[BaseModel]]


class KnowledgePipeline:
    def __init__(
        self, transactions: KnowledgeTransaction, promotion: CanonicalGraphPromotionService
    ) -> None:
        self.transactions, self.promotion = transactions, promotion
        self.resolver = IdentityResolver()

    async def resolve(
        self,
        job_id: UUID,
        candidates: list[dict[str, Any]],
        passages: list[SourcePassage],
        infer: InferRole,
    ) -> dict[str, dict[str, Any]]:
        async with self.transactions() as unit:
            job = await unit.archive.get_job(job_id)
            assert job
            continuity = UUID(job["continuity_id"])
            catalog = await unit.graph.catalog(UUID(job["universe_id"]), continuity)
        results = {}
        for claim in candidates:
            if claim["kind"] != "entity":
                continue

            async def compare(prompt: str, schema: type[BaseModel]) -> BaseModel:
                return await infer(prompt, schema, "identity_resolution")

            try:
                decision = await self.resolver.resolve(
                    claim, catalog, passages, compare, continuity
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
        analysis = RelationshipAnalysis.model_validate(
            (await infer(prompt, RelationshipAnalysis, "relationship_analysis")).model_dump()
        )
        result = list(candidates)
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
