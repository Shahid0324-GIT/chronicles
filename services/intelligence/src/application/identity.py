import json
import re
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID, uuid5

from pydantic import BaseModel

from src.application.event_identity import same_scoped_occurrence
from src.application.knowledge_contracts import (
    EmptyCatalogIdentityComparison,
    EventIdentityComparison,
    IdentityComparison,
    IndexedIdentityComparison,
)
from src.domain.knowledge import (
    name_key,
    order_key,
    same_full_name_order,
    short_name_bridge,
    source_name_bridge,
)
from src.domain.research import SourcePassage, digest, normalize, quotation_exists

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
        indexed_evidence: bool = False,
        participant_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = claim["payload"]
        if (payload.get("event") or {}).get("occurrence_status", "actual") != "actual":
            return {
                "accepted": False,
                "decision": "AMBIGUOUS",
                "canonical_id": None,
                "entity_type_valid": True,
                "proof": "nonactual_event",
                "reason": "Nonactual or unconfirmed reported event needs actual evidence.",
            }
        key = name_key(payload["name"])
        eligible = [n for n in catalog if n["type"] == payload["type"]]
        event_anchor = (payload.get("event") or {}).get("identity_anchor")
        participant_ids = participant_ids or []
        citations = payload.get("evidence", [])
        valid = all(
            any(str(p.id) == c["passage_id"] and quotation_exists(c["quote"], p) for p in passages)
            for c in citations
        ) and bool(citations)
        reusable = key in {"king", "queen", "lord", "captain", "王", "王様", "女王"}
        exact_matches = [
            n for n in eligible if key in {name_key(a) for a in [n["name"], *n.get("aliases", [])]}
        ]
        event = payload.get("event") or {}
        anchored = [
            n
            for n in eligible
            if event_anchor
            and (
                (n.get("event") or {}).get("identity_anchor") == event_anchor
                or (
                    bool(event.get("participants"))
                    and same_scoped_occurrence(event, n.get("event") or {}, catalog)
                )
            )
        ]
        anchor_valid = (
            any(
                p.source_id
                and str(p.id) == c["passage_id"]
                and event.get("trigger") in c["quote"]
                and event_anchor
                == digest(
                    f"{p.source_id}:"
                    f"{p.start + p.text.find(c['quote']) + c['quote'].find(event['trigger'])}:"
                    f"{event['trigger']}"
                )
                for p in passages
                for c in citations
            )
            if event.get("trigger")
            else False
        )
        match = (
            anchored[0]
            if len(anchored) == 1 and anchor_valid
            else exact_matches[0]
            if len(exact_matches) == 1
            and payload["type"] != "EVENT"
            and not reusable
            and any(key in name_key(c["quote"]) for c in citations)
            else None
        )
        if indexed_evidence and valid and match:
            return {
                "decision": "SAME_ENTITY",
                "accepted": True,
                "canonical_id": match["id"],
                "entity_type_valid": True,
                "proof": "same_evidence_event_anchor" if event_anchor else "exact_scoped_name",
                "evidence": citations,
                "hidden_identity": False,
                "reason": "Unique existing scoped identity and exact source evidence reused.",
            }

        def participants(node: dict[str, Any]) -> set[str]:
            return {
                r["source"]
                for r in node.get("relationships", [])
                if r["type"] == "PARTICIPATED_IN" and r["target"] == node["id"]
            }

        def rank(node: dict[str, Any]) -> tuple[int, str]:
            names = [node["name"], *node.get("aliases", [])]
            score = 4 if any(name_key(n) == key for n in names) else 0
            score += 2 if any(order_key(n) == order_key(payload["name"]) for n in names) else 0
            score += len(set(key.split()) & set(name_key(node["name"]).split()))
            if event_anchor and (node.get("event") or {}).get("identity_anchor") == event_anchor:
                score += 100
            score += 3 * len(set(participant_ids) & participants(node))
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
Give a single short reason, at most 160 characters. Do not repeat the source or every record.
Copy citations from candidate.evidence; do not cite unrelated passages.
""" + json.dumps(
            {
                "candidate": (
                    {
                        **payload,
                        "evidence": [{**e, "index": i} for i, e in enumerate(payload["evidence"])],
                    }
                    if indexed_evidence
                    else payload
                ),
                "matches": [
                    {
                        **n,
                        "index": index,
                        "description": n.get("description", "")[:240],
                        "aliases": sorted(n.get("aliases", []), key=lambda a: name_key(a) != key)[
                            :4
                        ],
                        "participant_names": [
                            node["name"] for node in catalog if node["id"] in participants(n)
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
        if indexed_evidence:
            prompt = prompt.replace(
                "Copy citations from candidate.evidence; do not cite unrelated passages.",
                "Choose evidence_indices (zero-based indices in candidate.evidence); "
                "do not copy quotations.",
            )
            schema: type[IndexedIdentityComparison] = (
                EmptyCatalogIdentityComparison
                if not choices
                else EventIdentityComparison
                if payload["type"] == "EVENT"
                else IndexedIdentityComparison
            )
            if not choices:
                prompt = (
                    "There are no existing matching records. Classify this as NEW_ENTITY only "
                    "if its identity and type are grounded, otherwise AMBIGUOUS. A source alias "
                    "is not an existing catalog record. Do not invent target indices.\n" + prompt
                )
            if payload["type"] == "EVENT":
                prompt = (
                    "For EVENT compare the precise occurrence, NOT a proper-name alias. "
                    "Return SAME_ENTITY only if same_occurrence, same_granularity and "
                    "repeated_occurrence_excluded are all true. A broad arc/search task is not "
                    "the same as a more specific occurrence inside it. Separate time-loop "
                    "attempts and repeated encounters. Resolved participants are context anchors, "
                    "not sufficient proof by themselves. Compare actual action and description. "
                    "Choose NEW_ENTITY for a distinct source-grounded occurrence, AMBIGUOUS "
                    "when uncertain. Event labels need not be literal aliases of each other.\n"
                    + prompt
                )
            indexed_response = schema.model_validate((await infer(prompt, schema)).model_dump())
            indices = indexed_response.evidence_indices
            if any(i < 0 or i >= len(payload["evidence"]) for i in indices) or (
                indexed_response.decision in {"SAME_ENTITY", "DIFFERENT_ENTITY"}
                and indexed_response.target_index is None
            ):
                return {
                    "accepted": False,
                    "decision": "AMBIGUOUS",
                    "canonical_id": None,
                    "proof": "unresolved",
                    "reason": "Invalid identity evidence or target index.",
                    "model_response": indexed_response.model_dump(mode="json"),
                }
            response = IdentityComparison.model_validate(
                {
                    **indexed_response.model_dump(
                        exclude={
                            "evidence_indices",
                            "same_occurrence",
                            "same_granularity",
                            "repeated_occurrence_excluded",
                        }
                    ),
                    # Keep the complete grounded candidate context, including both halves of
                    # a bilingual bridge; model-selected indices remain separately inspectable.
                    "evidence": payload["evidence"],
                }
            )
        else:
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
        if indexed_evidence:
            result["model_evidence_indices"] = indices
        if not response.entity_type_valid:
            result["reason"] = "Source does not establish the asserted entity type."
            return result
        if len(cited) != len(response.evidence) or not cited:
            result["reason"] = "Identity comparison lacked valid exact evidence."
            return result
        if (
            indexed_evidence
            and isinstance(indexed_response, EventIdentityComparison)
            and response.decision == "SAME_ENTITY"
            and not (
                indexed_response.same_occurrence
                and indexed_response.same_granularity
                and indexed_response.repeated_occurrence_excluded
            )
        ):
            result.update(
                decision="AMBIGUOUS", reason="Event occurrence or granularity remains ambiguous."
            )
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
            bridge = any(source_name_bridge(payload["name"], n, cited) for n in names)
            order_match = any(same_full_name_order(payload["name"], n) for n in names)
            short_match = any(short_name_bridge(payload["name"], n, cited) for n in names)
            possible = [
                n
                for n in eligible
                if any(
                    same_full_name_order(payload["name"], a)
                    or name_key(payload["name"]) in name_key(a).split()
                    for a in [n["name"], *n.get("aliases", [])]
                )
            ]
            contextual_name = (
                payload["type"] == "CHARACTER"
                and (order_match or short_match)
                and len(possible) == 1
            )
            event_context = (
                indexed_evidence
                and isinstance(indexed_response, EventIdentityComparison)
                and indexed_response.same_occurrence
                and indexed_response.same_granularity
                and indexed_response.repeated_occurrence_excluded
                and bool(set(participant_ids) & participants(target))
                and bool(event_anchor)
            )
            same_event = bool(
                event_anchor and event_anchor == (target.get("event") or {}).get("identity_anchor")
            ) or same_scoped_occurrence(
                payload.get("event") or {}, target.get("event") or {}, catalog
            )
            different_event = bool(
                event_anchor
                and (target.get("event") or {}).get("identity_anchor")
                and not same_event
            )
            old_event = target.get("event") or {}
            new_event = payload.get("event") or {}
            if (
                event_context
                and old_event.get("source_id") != new_event.get("source_id")
                and new_event.get("source_position") is not None
                and new_event.get("source_position") == old_event.get("source_position")
            ):
                different_event = False
            if not different_event and (
                (exact and not title_only)
                or bridge
                or same_event
                or contextual_name
                or event_context
            ):
                result.update(
                    accepted=True,
                    canonical_id=target["id"],
                    proof="same_evidence_event_anchor"
                    if same_event
                    else "exact_scoped_name"
                    if exact
                    else "scoped_name_order_or_short_reference"
                    if contextual_name
                    else "verified_event_context"
                    if event_context
                    else "explicit_name_bridge",
                )
                if event_context:
                    result["event_context"] = {
                        "participant_ids": participant_ids,
                        "same_occurrence": True,
                        "same_granularity": True,
                        "repeated_occurrence_excluded": True,
                    }
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
                if any(
                    name_key(a) == key
                    or (payload["type"] == "CHARACTER" and same_full_name_order(payload["name"], a))
                    for a in [n["name"], *n.get("aliases", [])]
                )
                and not (
                    event_anchor
                    and (n.get("event") or {}).get("identity_anchor")
                    and (n.get("event") or {}).get("identity_anchor") != event_anchor
                )
            ]
            contradicts_bridge = any(
                source_name_bridge(payload["name"], name, cited)
                for node in eligible
                for name in [node["name"], *node.get("aliases", [])]
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
                and not any(
                    same_scoped_occurrence(
                        payload.get("event") or {}, n.get("event") or {}, catalog
                    )
                    for n in eligible
                )
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
