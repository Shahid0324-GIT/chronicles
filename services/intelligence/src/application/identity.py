import json
import re
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
        event_anchor = (payload.get("event") or {}).get("identity_anchor")

        def rank(node: dict[str, Any]) -> tuple[int, str]:
            names = [node["name"], *node.get("aliases", [])]
            score = 4 if any(name_key(n) == key for n in names) else 0
            score += 2 if any(order_key(n) == order_key(payload["name"]) for n in names) else 0
            score += len(set(key.split()) & set(name_key(node["name"]).split()))
            if event_anchor and (node.get("event") or {}).get("identity_anchor") == event_anchor:
                score += 100
            return -score, node["id"]

        choices = sorted(eligible, key=rank)[:8]
        if event_anchor:
            choices.sort(
                key=lambda n: (n.get("event") or {}).get("identity_anchor") != event_anchor
            )
        prompt = """Resolve the candidate identity against the supplied scoped records only.
Names, surnames, titles, co-occurrence or similar descriptions alone do not prove identity.
First check entity_type_valid: does the name identify an entity of the asserted type?
EVENT means an action or occurrence, including arrival, disappearance or loss of a resource.
It need not be a formally named event. A person name alone is not an event label.
entity_type_valid checks the source and requested class, NOT whether a canonical match exists.
A genuinely NEW_ENTITY may and should have entity_type_valid=true when its type is grounded.
Return SAME_ENTITY only with source evidence and target_index from the numbered matches.
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
                        "index": index,
                        "description": n.get("description", "")[:240],
                        "aliases": sorted(n.get("aliases", []), key=lambda a: name_key(a) != key)[
                            :4
                        ],
                    }
                    for index, n in enumerate(choices)
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
        if response.target_index is not None and response.target_index < len(choices):
            indexed = choices[response.target_index]
            if response.target_id is not None and str(response.target_id) != indexed["id"]:
                target = None
            else:
                target = indexed
        result: dict[str, Any] = {
            **response.model_dump(mode="json"),
            "accepted": False,
            "canonical_id": None,
            "proof": "unresolved",
            "model_reason": response.reason,
        }
        if not response.entity_type_valid:
            result["reason"] = "Source does not establish the asserted entity type."
            return result
        if len(cited) != len(response.evidence) or not cited:
            result["reason"] = "Identity comparison lacked valid exact evidence."
            return result
        reusable_title = key in {"king", "queen", "lord", "captain", "王", "王様", "女王"}
        if reusable_title and not any(
            re.search(
                r"(?:named|name is)\s+" + re.escape(key) + r"\b|という名",
                name_key(q),
                re.IGNORECASE,
            )
            for q in cited
        ):
            result["reason"] = "A reusable title alone does not establish a permanent identity."
            return result
        if response.decision == "SAME_ENTITY" and target:
            names = [target["name"], *target.get("aliases", [])]
            exact = any(name_key(n) == key for n in names)
            title_only = key in {"king", "queen", "lord", "captain", "王", "王様", "女王"}
            bridge = any(explicit_name_bridge(payload["name"], n, q) for n in names for q in cited)
            same_event = bool(
                event_anchor and event_anchor == (target.get("event") or {}).get("identity_anchor")
            )
            different_event = bool(
                event_anchor
                and (target.get("event") or {}).get("identity_anchor")
                and not same_event
            )
            if not different_event and ((exact and not title_only) or bridge or same_event):
                result.update(
                    accepted=True,
                    canonical_id=target["id"],
                    proof="same_evidence_event_anchor"
                    if same_event
                    else "exact_scoped_name"
                    if exact
                    else "explicit_name_bridge",
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
                and not (
                    event_anchor
                    and (n.get("event") or {}).get("identity_anchor")
                    and (n.get("event") or {}).get("identity_anchor") != event_anchor
                )
            ]
            contradicts_bridge = any(
                explicit_name_bridge(payload["name"], name, quote)
                for node in eligible
                for name in [node["name"], *node.get("aliases", [])]
                for quote in cited
            )
            partial_reference = (
                payload["type"] != "EVENT"
                and len(key.split()) == 1
                and any(
                    key in name_key(n).split() and name_key(n) != key
                    for node in eligible
                    for n in [node["name"], *node.get("aliases", [])]
                )
            )
            if (
                not collisions
                and not contradicts_bridge
                and not partial_reference
                and (len(eligible) <= 8 or event_anchor)
            ):
                result.update(
                    accepted=True,
                    canonical_id=str(
                        uuid5(
                            continuity,
                            "event:" + event_anchor if event_anchor else "entity:" + claim["id"],
                        )
                    ),
                    proof="new_scoped_entity",
                )
            else:
                result.update(
                    decision="AMBIGUOUS",
                    reason="Name collision or candidate retrieval bound requires more research.",
                )
        return result
