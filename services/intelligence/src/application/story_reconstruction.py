"""Evidence-backed story organization, not another agent or a chronology inference."""

import json
import re
from typing import Any
from uuid import UUID, uuid5

from src.application.event_extraction import evidence_units
from src.application.ports.retrieval import EvidenceHit
from src.application.reader_status import accepted_text
from src.application.story_position import source_position
from src.domain.entities import GraphRelationship
from src.domain.research import digest


def outline_permission(config: dict[str, Any]) -> str:
    return digest(
        json.dumps(
            {
                k: config.get(k)
                for k in (
                    "retrieval_policy",
                    "continuity_ids",
                    "selectors",
                    "eligible_section_terms",
                    "discovery_index",
                )
            },
            sort_keys=True,
        )
    )


def reference_outline(
    hits: list[EvidenceHit], permissions: dict[str, dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Archive explicit reference segmentation; none of this is canonical publication."""
    result = {}
    for hit in hits:
        for unit in evidence_units([hit.passage]):
            if not re.search(
                r"\b(?:first|second|third|fourth|final)(?: and (?:final|last))? "
                r"(?:story|segment|part|phase)\b",
                unit["text"],
                re.I,
            ):
                continue
            key = digest(f"{hit.passage.id}:{unit['start']}:{unit['text']}")
            result[key] = {
                "id": key,
                "status": "reference_description_not_canon",
                "statement": unit["text"],
                "sourceId": str(hit.source.id),
                "sourceRevision": hit.source.content_hash,
                "passageId": str(hit.passage.id),
                "passageHash": hit.passage.content_hash,
                "quoteStart": unit["start"],
                "quoteEnd": unit["start"] + len(unit["text"]),
                "position": hit.source.provenance.get("presentation_position"),
                "positionBasis": hit.source.provenance.get("position_basis"),
                "permissionFingerprint": outline_permission(
                    (permissions or {}).get(hit.source.provenance.get("registry_id", ""), {})
                ),
            }
    return list(result.values())[:30]


def reconstruct_story(
    continuity: UUID,
    facts: dict[str, list[dict[str, Any]]],
    edges: list[GraphRelationship],
    steps: list[dict[str, Any]],
    outline: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Project actual events, explicit edges, state assertions and absent transitions.

    Exact event groups come from the existing organizer. A shared participant is
    a connective thread, never evidence that one event caused or preceded another.
    """
    eligible_edges = [
        e
        for e in edges
        if str(e.id) in facts and str(e.source_node_id) in facts and str(e.target_node_id) in facts
    ]
    groups: dict[str, dict[str, Any]] = {}
    event_to_group = {}
    for step in steps:
        ids = step.get("underlyingEventIds") or [step["eventNodeId"]]
        own = [
            f
            for identifier in ids
            for f in facts.get(identifier, [])
            if f["kind"] == "entity" and f["payload"].get("type") == "EVENT"
        ]
        if not own:
            continue
        _, statement = accepted_text(own)
        participants: list[dict[str, Any]] = []
        for edge in eligible_edges:
            if (
                edge.relationship_type.value != "PARTICIPATED_IN"
                or str(edge.target_node_id) not in ids
            ):
                continue
            person = str(edge.source_node_id)
            names = {f["payload"].get("name", "").casefold() for f in facts[person]}
            roles = sorted(
                {
                    role
                    for f in own
                    for name, role in (f["payload"].get("event") or {})
                    .get("participant_roles", {})
                    .items()
                    if name.casefold() in names
                    and role in {"actor", "recipient", "witness", "opponent"}
                }
            )
            if roles:
                participants.append(
                    {
                        "nodeId": person,
                        "name": accepted_text(facts[person])[0],
                        "roles": roles,
                        "relationshipId": str(edge.id),
                    }
                )
        locations = [
            str(e.target_node_id)
            for e in eligible_edges
            if e.relationship_type.value == "OCCURRED_AT" and str(e.source_node_id) in ids
        ]
        source_positions = {
            (s["id"], s.get("passage_id")): {
                "sourceId": s["id"],
                "passageId": s.get("passage_id"),
                "position": source_position(s),
                "basis": s.get("provenance", {}).get("position_basis"),
                "revision": s.get("content_hash"),
                "locator": s.get("locator"),
            }
            for f in own
            for s in f["sources"]
        }
        group = {
            "id": step["id"],
            "eventNodeIds": ids,
            "title": accepted_text(own)[0],
            "statement": statement,
            "factIds": sorted({f["id"] for f in own}),
            "participants": participants,
            "locationIds": sorted(set(locations)),
            "sourcePositions": list(source_positions.values()),
            "changes": [],
            "outcomes": [],
        }
        confirmed_names = {p["name"].casefold() for p in participants}
        group["unresolvedParticipantNames"] = sorted(
            {
                name
                for f in own
                for name, role in (f["payload"].get("event") or {})
                .get("participant_roles", {})
                .items()
                if role in {"actor", "recipient", "witness", "opponent"}
                and name.casefold() not in confirmed_names
            }
        )
        groups[group["id"]] = group
        for identifier in ids:
            event_to_group[identifier] = group["id"]
    bases = {
        p["basis"]
        for g in groups.values()
        for p in g["sourcePositions"]
        if p["position"] is not None
    }
    ordered = sorted(
        groups.values(),
        key=lambda g: (
            (
                min(
                    (p["position"] for p in g["sourcePositions"] if p["position"] is not None),
                    default=100001,
                ),
                g["id"],
            )
            if len(bases) == 1
            else (100001, g["id"])
        ),
    )
    links = []
    for edge in eligible_edges:
        a, b, kind = (
            str(edge.source_node_id),
            str(edge.target_node_id),
            edge.relationship_type.value,
        )
        assertions = facts[str(edge.id)]
        item = {
            "relationshipId": str(edge.id),
            "type": kind,
            "source": a,
            "target": b,
            "statements": [f["payload"]["description"] for f in assertions],
            "factIds": sorted({f["id"] for f in assertions}),
        }
        if (
            kind in {"PRECEDES", "CAUSED", "ENABLED"}
            and a in event_to_group
            and b in event_to_group
        ):
            item.update(fromId=event_to_group[a], toId=event_to_group[b])
            links.append(item)
            if kind in {"CAUSED", "ENABLED"}:
                groups[event_to_group[a]]["outcomes"].append(item)
        elif kind not in {"PARTICIPATED_IN", "OCCURRED_AT"}:
            for group in ordered:
                people = {p["nodeId"] for p in group["participants"]}
                # A relationship belongs to an event only when it shares an exact
                # accepted atomic assertion with that event, not just two names.
                event_atoms = {
                    (f["payload"].get("atomic") or {}).get("id")
                    for i in group["eventNodeIds"]
                    for f in facts[i]
                }
                if {a, b} & people and any(
                    (f["payload"].get("atomic") or {}).get("id") in event_atoms - {None}
                    for f in assertions
                ):
                    matched = [
                        f
                        for f in assertions
                        if (f["payload"].get("atomic") or {}).get("id") in event_atoms - {None}
                    ]
                    group["changes"].append(
                        {
                            **item,
                            "statements": [f["payload"]["description"] for f in matched],
                            "factIds": sorted({f["id"] for f in matched}),
                        }
                    )
    transitions = []
    gaps = []
    for before, after in zip(ordered, ordered[1:], strict=False):
        direct = [
            link for link in links if link["fromId"] == before["id"] and link["toId"] == after["id"]
        ]
        causal = [link for link in direct if link["type"] in {"CAUSED", "ENABLED"}]
        sequence = [link for link in direct if link["type"] == "PRECEDES"]
        shared = sorted(
            {p["nodeId"] for p in before["participants"]}
            & {p["nodeId"] for p in after["participants"]}
        )
        explanation = (
            " ".join(s for link in causal for s in link["statements"])
            if causal
            else "An explicit sequence is supported, but its cause is not established."
            if sequence
            else "A shared participant links these moments; the transition is unexplained."
            if shared
            else "No accepted evidence explains how these story segments connect."
        )
        transition = {
            "fromId": before["id"],
            "toId": after["id"],
            "sourceOrder": "supporting-source-order-only" if len(bases) == 1 else "unresolved",
            "narrativeOrder": "not_established",
            "chronology": "accepted_precedence_assertion" if sequence else "not_established",
            "publicationOrder": "supporting_boundaries_only; first reveal not established",
            "assertedSequence": sequence,
            "causality": causal,
            "sharedParticipantIds": shared,
            "explanation": explanation,
        }
        transitions.append(transition)
        if not causal:
            question = (
                f"What permitted evidence explains the transition between '{before['title']}' "
                f"and '{after['title']}'? Establish narrative order, chronology and any "
                "actual cause separately; do not assume source order proves them."
            )
            gaps.append(
                {
                    "id": str(uuid5(continuity, question)),
                    "kind": "missing_transition",
                    "eventNodeIds": [*before["eventNodeIds"], *after["eventNodeIds"]],
                    "question": question,
                }
            )
    for group in ordered:
        group["relationshipInteractions"] = group["changes"]
        state_atoms = [
            f["payload"].get("atomic") or {}
            for identifier in group["eventNodeIds"]
            for f in facts[identifier]
        ]
        group["stateChangeAssertions"] = [
            {"statement": a["statement"], "status": "accepted_action_only"}
            for a in state_atoms
            if a.get("statement")
            and re.match(
                r"(?:joined|left|became|becomes|recruited|recruits|recruiting)\b",
                a.get("predicate", ""),
                re.I,
            )
        ]
        group["conflicts"] = [link for link in group["changes"] if link["type"] == "OPPOSED"]
        group["loreConnections"] = [
            link
            for link in group["changes"]
            if any(
                f["payload"].get("type") in {"LORE", "OBJECT", "MYSTERY"}
                for endpoint in (link["source"], link["target"])
                for f in facts[endpoint]
            )
        ]
        group["turningPointStatus"] = "narrative_importance_not_established"
        missing = [
            label
            for label, value in (
                ("participants", group["participants"]),
                ("location", group["locationIds"]),
                ("outcomes", group["outcomes"]),
            )
            if not value
        ]
        group["missingCoverage"] = missing
        if missing:
            question = (
                f"What permitted evidence establishes {', '.join(missing)} for '{group['title']}'?"
            )
            gaps.append(
                {
                    "id": str(uuid5(continuity, question)),
                    "kind": "event_coverage",
                    "eventNodeIds": group["eventNodeIds"],
                    "question": question,
                }
            )
        if group["unresolvedParticipantNames"]:
            question = (
                f"Which permitted evidence resolves canonical identities and actual roles "
                f"for {', '.join(group['unresolvedParticipantNames'])} in '{group['title']}'?"
            )
            gaps.append(
                {
                    "id": str(uuid5(continuity, question)),
                    "kind": "unresolved_roles",
                    "eventNodeIds": group["eventNodeIds"],
                    "question": question,
                }
            )
    reference = []
    for item in outline or []:
        covered = sorted(
            {
                identifier
                for g in ordered
                for identifier in g["eventNodeIds"]
                for f in facts[identifier]
                for s in f["sources"]
                if s["id"] == item["sourceId"]
                and s.get("passage_id") == item["passageId"]
                and s.get("quote_start", -1) < item["quoteEnd"]
                and item["quoteStart"] < s.get("quote_end", -1)
            }
        )
        reference.append(
            {
                **item,
                "verifiedEventIds": covered,
                "status": "partially_supported_reference_segment"
                if covered
                else "reference_description_not_canon",
            }
        )
        if not covered:
            question = (
                "Which permitted evidence establishes events and transitions in this "
                "reference-described segment: " + str(item["statement"])
            )
            gaps.append(
                {
                    "id": str(uuid5(continuity, question)),
                    "kind": "reference_segment_unverified",
                    "eventNodeIds": [],
                    "question": question,
                    "sourceId": item["sourceId"],
                }
            )
    threads = []
    for person in sorted({p["nodeId"] for g in ordered for p in g["participants"]}):
        involved = [g for g in ordered if any(p["nodeId"] == person for p in g["participants"])]
        threads.append(
            {
                "characterId": person,
                "name": accepted_text(facts[person])[0],
                "segmentIds": [g["id"] for g in involved],
                "relationshipChanges": [
                    change
                    for g in involved
                    for change in g["changes"]
                    if person in {change["source"], change["target"]}
                ],
                "orderingBasis": (
                    "Supporting source boundaries; state transitions require explicit evidence."
                ),
            }
        )
    return {
        "version": "story-reconstruction-v1",
        "status": "partial" if ordered else "no_verified_segments",
        "outlineBasis": "Accepted event groups only; not an exhaustive arc outline.",
        "segments": ordered,
        "transitions": transitions,
        "explicitEventLinks": links,
        "characterThreads": threads,
        "referenceOutline": reference,
        "gaps": gaps,
        "duplicateHandling": (
            "Canonical event identity and exact anchored groups; similarities never merge events."
        ),
        "coverage": {
            "verifiedSegments": len(ordered),
            "candidateTransitions": len(transitions),
            "causallyExplainedTransitions": sum(bool(t["causality"]) for t in transitions),
            "unexplainedTransitions": sum(not t["causality"] for t in transitions),
            "segmentsWithParticipants": sum(bool(g["participants"]) for g in ordered),
            "segmentsWithLocations": sum(bool(g["locationIds"]) for g in ordered),
            "explicitCausalLinks": sum(link["type"] in {"CAUSED", "ENABLED"} for link in links),
            "explicitPrecedenceLinks": sum(link["type"] == "PRECEDES" for link in links),
        },
        "readingExplanation": "Supporting source boundaries organize this partial account. "
        "They do not establish narrative order, in-world chronology or causation. "
        "Unexplained transitions remain research questions.",
    }
