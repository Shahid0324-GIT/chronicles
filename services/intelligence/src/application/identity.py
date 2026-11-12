import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel

from src.application.knowledge_contracts import IdentityComparison
from src.domain.knowledge import explicit_name_bridge, name_key, order_key
from src.domain.research import SourcePassage, normalize, quotation_exists

InferIdentity = Callable[[str, type[BaseModel]], Awaitable[BaseModel]]


class IdentityResolver:
    """Retrieve proposals deterministically; evidence and semantic comparison decide identity."""

    async def resolve(
        self,
        claim: dict[str, Any],
        catalog: list[dict[str, Any]],
        passages: list[SourcePassage],
        infer: InferIdentity,
        continuity: UUID,
    ) -> dict[str, Any]:
        payload = claim["payload"]
        key = name_key(payload["name"])
        eligible = [n for n in catalog if n["type"] == payload["type"]]

        def rank(node: dict[str, Any]) -> tuple[int, str]:
            names = [node["name"], *node.get("aliases", [])]
            score = 4 if any(name_key(n) == key for n in names) else 0
            score += 2 if any(order_key(n) == order_key(payload["name"]) for n in names) else 0
            score += len(set(key.split()) & set(name_key(node["name"]).split()))
            return -score, node["id"]

        choices = sorted(eligible, key=rank)[:8]
        prompt = """Resolve the candidate identity against the supplied scoped records only.
Names, surnames, titles, co-occurrence or similar descriptions alone do not prove identity.
Return SAME_ENTITY only with source evidence and a specific target_id from matches.
For different scripts or translations, cite an explicit bilingual/alias annotation where possible.
NEW_ENTITY means none of the proposed records matches.
DIFFERENT_ENTITY must name the compared target.
AMBIGUOUS means preserve uncertainty. Hidden identities require hidden_identity=true.
Never use remembered fictional lore or a confidence score.
Copy citations from candidate.evidence; do not cite unrelated passages.
""" + json.dumps(
            {
                "candidate": payload,
                "matches": [
                    {
                        **n,
                        "description": n.get("description", "")[:240],
                        "aliases": sorted(n.get("aliases", []), key=lambda a: name_key(a) != key)[
                            :4
                        ],
                    }
                    for n in choices
                ],
                "passages": [
                    {"id": c["passage_id"], "text": c["quote"]} for c in payload["evidence"]
                ],
            },
            ensure_ascii=False,
        )
        response = IdentityComparison.model_validate(
            (await infer(prompt, IdentityComparison)).model_dump()
        )
        cited = []
        for citation in response.evidence:
            passage = next((p for p in passages if p.id == citation.passage_id), None)
            if passage and quotation_exists(citation.quote, passage):
                cited.append(normalize(citation.quote))
        target = next((n for n in choices if str(response.target_id) == n["id"]), None)
        result: dict[str, Any] = {
            **response.model_dump(mode="json"),
            "accepted": False,
            "canonical_id": None,
            "proof": "unresolved",
        }
        if len(cited) != len(response.evidence) or not cited:
            result["reason"] = "Identity comparison lacked valid exact evidence."
            return result
        if response.decision == "SAME_ENTITY" and target:
            names = [target["name"], *target.get("aliases", [])]
            exact = any(name_key(n) == key for n in names)
            title_only = key in {"king", "queen", "lord", "captain", "王", "王様", "女王"}
            bridge = any(explicit_name_bridge(payload["name"], n, q) for n in names for q in cited)
            if (exact and not title_only) or bridge:
                result.update(
                    accepted=True,
                    canonical_id=target["id"],
                    proof="exact_scoped_name" if exact else "explicit_name_bridge",
                )
            else:
                result.update(
                    decision="AMBIGUOUS",
                    reason="Semantic match lacks a deterministic name/alias bridge.",
                )
        elif response.decision in {"NEW_ENTITY", "DIFFERENT_ENTITY"}:
            if response.decision == "DIFFERENT_ENTITY" and not target:
                return result
            collisions = [
                n
                for n in eligible
                if any(name_key(a) == key for a in [n["name"], *n.get("aliases", [])])
            ]
            contradicts_bridge = any(
                explicit_name_bridge(payload["name"], name, quote)
                for node in eligible
                for name in [node["name"], *node.get("aliases", [])]
                for quote in cited
            )
            if not collisions and not contradicts_bridge and len(eligible) <= 8:
                result.update(
                    accepted=True,
                    canonical_id=str(uuid5(continuity, "entity:" + claim["id"])),
                    proof="new_scoped_entity",
                )
            else:
                result.update(
                    decision="AMBIGUOUS",
                    reason="Name collision or candidate retrieval bound requires more research.",
                )
        return result
