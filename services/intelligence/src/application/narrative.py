import json
from typing import Any
from uuid import UUID, uuid5

from src.application.ports.narrative import NarrativeKnowledge, NarrativeTransaction
from src.domain.research import digest
from src.domain.value_objects import NodeType, RelationshipType


class NarrativeBuilder:
    def __init__(self, transactions: NarrativeTransaction) -> None:
        self.transactions = transactions

    async def build(
        self,
        universe: UUID,
        continuity: UUID,
        *,
        allowed_sources: list[UUID] | None = None,
        spoiler_position: int | None = None,
        knowledge: NarrativeKnowledge | None = None,
    ) -> dict[str, Any]:
        if knowledge is None:
            async with self.transactions() as repo:
                knowledge = await repo.knowledge(universe, continuity)
        allowed = set(map(str, allowed_sources)) if allowed_sources is not None else None
        source_map: dict[str, dict[str, Any]] = {}
        source_locators: dict[str, set[str]] = {}
        facts: dict[str, list[dict[str, Any]]] = {}
        positions: dict[str, int] = {}
        for f in knowledge.facts:
            sources = f["sources"]
            if not sources or any(
                (allowed is not None and s["id"] not in allowed)
                or (
                    spoiler_position is not None
                    and (
                        s["provenance"].get("presentation_position") is None
                        or s["provenance"]["presentation_position"] > spoiler_position
                    )
                )
                for s in sources
            ):
                continue
            facts.setdefault(f["target_id"], []).append(f)
            for s in sources:
                locators = source_locators.setdefault(s["id"], set())
                locators.add(s["locator"])
                source_map[s["id"]] = {**s, "locator": "; ".join(sorted(locators))}
                if s["provenance"].get("position_basis") == "broadcast-presentation":
                    pos = s["provenance"].get("presentation_position")
                    if isinstance(pos, int):
                        positions[f["target_id"]] = min(positions.get(f["target_id"], pos), pos)
        nodes = {str(n.id): n for n in knowledge.nodes}
        edges = sorted(
            [
                e
                for e in knowledge.edges
                if str(e.id) in facts
                and str(e.source_node_id) in facts
                and str(e.target_node_id) in facts
            ],
            key=lambda e: str(e.id),
        )
        steps: list[dict[str, Any]] = []
        unordered: list[dict[str, Any]] = []
        journey_id = str(uuid5(continuity, "accepted-broadcast-journey"))
        for identifier, node in nodes.items():
            if node.type != NodeType.EVENT or identifier not in facts:
                continue
            adjacent = [e for e in edges if node.id in {e.source_node_id, e.target_node_id}]
            related = sorted(
                {
                    str(e.target_node_id if e.source_node_id == node.id else e.source_node_id)
                    for e in adjacent
                }
            )
            assertion = sorted(
                facts[identifier], key=lambda f: json.dumps(f["payload"], sort_keys=True)
            )[0]["payload"]
            citations = sorted({s["id"] for f in facts[identifier] for s in f["sources"]})
            participant_roles = []
            for edge in adjacent:
                if (
                    edge.relationship_type != RelationshipType.PARTICIPATED_IN
                    or edge.target_node_id != node.id
                ):
                    continue
                names = {
                    f["payload"].get("name", "").casefold()
                    for f in facts.get(str(edge.source_node_id), [])
                }
                roles = {
                    role
                    for fact in facts[identifier]
                    for name, role in (fact["payload"].get("event") or {})
                    .get("participant_roles", {})
                    .items()
                    if name.casefold() in names
                    and role in {"actor", "recipient", "witness", "opponent"}
                }
                if len(roles) == 1:
                    participant_roles.append(
                        {"nodeId": str(edge.source_node_id), "role": next(iter(roles))}
                    )
            step = {
                "id": str(uuid5(node.id, "narrative-milestone")),
                "eventNodeId": identifier,
                "title": assertion.get("name", node.title),
                "body": assertion["description"],
                "episodeLabel": f"By episode {positions[identifier]}"
                if identifier in positions
                else "Order unknown",
                "sourceIds": citations,
                "loreThreadIds": [],
                "participantRoles": participant_roles,
                "presentation": {
                    "relatedNodeIds": related,
                    "relationshipIds": [str(e.id) for e in adjacent],
                },
                "causes": [
                    str(e.source_node_id)
                    for e in adjacent
                    if e.target_node_id == node.id
                    and e.relationship_type in {RelationshipType.CAUSED, RelationshipType.ENABLED}
                ],
                "consequences": [
                    str(e.target_node_id)
                    for e in adjacent
                    if e.source_node_id == node.id
                    and e.relationship_type in {RelationshipType.CAUSED, RelationshipType.ENABLED}
                ],
                "participantIds": [
                    str(e.source_node_id)
                    for e in adjacent
                    if e.target_node_id == node.id
                    and e.relationship_type == RelationshipType.PARTICIPATED_IN
                ],
                "locationIds": [
                    str(e.target_node_id)
                    for e in adjacent
                    if e.source_node_id == node.id
                    and e.relationship_type == RelationshipType.OCCURRED_AT
                ],
            }
            (steps if identifier in positions else unordered).append(step)
        # Within an episode, neither titles nor graph/article order establish narrative order.
        groups: dict[int, list[dict[str, Any]]] = {}
        for step in steps:
            groups.setdefault(positions[step["eventNodeId"]], []).append(step)
        ordered: list[dict[str, Any]] = []
        gaps: list[dict[str, Any]] = []
        for position, group in sorted(groups.items()):
            if len(group) == 1:
                ordered += group
                continue
            ids = {s["eventNodeId"] for s in group}
            before = {
                (str(e.source_node_id), str(e.target_node_id))
                for e in edges
                if e.relationship_type == RelationshipType.PRECEDES
                and str(e.source_node_id) in ids
                and str(e.target_node_id) in ids
            }
            pending = {s["eventNodeId"]: s for s in group}
            while pending:
                ready = [i for i in pending if not any(b == i and a in pending for a, b in before)]
                if len(ready) != 1:
                    gaps.append(
                        {
                            "kind": "ambiguous-within-episode-order",
                            "position": position,
                            "eventNodeIds": sorted(pending),
                        }
                    )
                    # One representative at this source boundary is useful without
                    # pretending to order competing events inside the episode.
                    if len(pending) == len(group):
                        representative = min(
                            pending,
                            key=lambda i: (-len(pending[i]["presentation"]["relationshipIds"]), i),
                        )
                        ordered.append(pending.pop(representative))
                    unordered += list(pending.values())
                    break
                key = ready[0]
                ordered.append(pending.pop(key))
        if unordered:
            gaps.append(
                {
                    "kind": "missing-verified-presentation-order",
                    "eventNodeIds": sorted(s["eventNodeId"] for s in unordered),
                }
            )
        threads, discoveries = [], []
        for identifier, node in sorted(nodes.items()):
            if identifier not in facts or node.type not in {NodeType.LORE, NodeType.MYSTERY}:
                continue
            thread_id, discovery_id = (
                str(uuid5(node.id, "lore-thread")),
                str(uuid5(node.id, "discovery")),
            )
            citations = sorted({s["id"] for f in facts[identifier] for s in f["sources"]})
            assertion = sorted(
                facts[identifier], key=lambda f: json.dumps(f["payload"], sort_keys=True)
            )[0]["payload"]
            presentation: dict[str, Any] = {"relatedNodeIds": [], "relationshipIds": []}
            threads.append(
                {
                    "id": thread_id,
                    "universeId": str(universe),
                    "continuityId": str(continuity),
                    "conceptNodeId": identifier,
                    "title": assertion.get("name", node.title),
                    "introduction": assertion["description"],
                    "spoilerScope": "Accepted source boundary",
                    "discoveryIds": [discovery_id],
                    "initialDiscoveryId": discovery_id,
                    "presentation": presentation,
                }
            )
            discoveries.append(
                {
                    "id": discovery_id,
                    "threadId": thread_id,
                    "nodeId": identifier,
                    "title": assertion.get("name", node.title),
                    "explanation": assertion["description"],
                    "classification": "unresolved"
                    if node.type == NodeType.MYSTERY
                    else "established",
                    "sourceIds": citations,
                    "relatedDiscoveryIds": [],
                    "presentation": presentation,
                }
            )
        catalog: dict[str, Any] = {
            "schemaVersion": 1,
            "identities": [
                {
                    "id": identifier,
                    "type": nodes[identifier].type.value,
                    "names": sorted(
                        {f["payload"]["name"] for f in eligible if f["payload"].get("name")}
                    ),
                }
                for identifier, eligible in sorted(facts.items())
                if identifier in nodes
            ],
            "journeys": [
                {
                    "id": journey_id,
                    "universeId": str(universe),
                    "continuityId": str(continuity),
                    "title": "Accepted story milestones",
                    "introduction": "Partial journey across supporting episode sources.",
                    "spoilerScope": "Accepted source boundary",
                    "ordering": {
                        "basis": "broadcast-presentation",
                        "explanation": (
                            "Earliest supporting episode source in this archive, not proof of "
                            "first reveal or in-world chronology. Synopses may recap earlier "
                            "events. "
                            "Ambiguous episode groups show one representative; other events remain "
                            "unordered. Within-episode order requires accepted PRECEDES evidence."
                        ),
                        "sourceIds": sorted({s for step in ordered for s in step["sourceIds"]}),
                    },
                    "steps": ordered,
                }
            ]
            if ordered
            else [],
            "loreThreads": threads,
            "discoveries": discoveries,
            "sources": [
                {"id": s["id"], "title": s["title"], "url": s["url"], "locator": s["locator"]}
                for s in sorted(source_map.values(), key=lambda s: s["id"])
            ],
            "unorderedMilestones": sorted(unordered, key=lambda s: s["id"]),
            "orderingGaps": gaps,
            "relations": [
                {
                    "id": str(e.id),
                    "source": str(e.source_node_id),
                    "target": str(e.target_node_id),
                    "type": e.relationship_type.value,
                }
                for e in edges
            ],
            "partial": bool(gaps) or not ordered,
        }
        revision = digest(json.dumps(catalog, sort_keys=True, ensure_ascii=False))
        catalog["revision"] = revision
        boundary = digest(
            json.dumps([sorted(allowed) if allowed is not None else None, spoiler_position])
        )
        async with self.transactions() as repo:
            await repo.save(universe, continuity, boundary, revision, catalog)
        return catalog
