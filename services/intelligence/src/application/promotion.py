"""Only this application service publishes graph mutations; all checks repeat in its transaction."""

from typing import Any
from uuid import UUID, uuid5

from src.application.ports.knowledge import KnowledgeTransaction
from src.domain.entities import GraphNode, GraphRelationship
from src.domain.exceptions import NotFoundError
from src.domain.knowledge import (
    PromotionPolicy,
    explicit_name_bridge,
    in_world_structure,
    independent_sources,
    name_key,
    relation_structure,
)
from src.domain.research import digest
from src.domain.value_objects import NodeType, RelationshipType


class CanonicalGraphPromotionService:
    def __init__(self, transactions: KnowledgeTransaction, policy: PromotionPolicy) -> None:
        self.transactions, self.policy = transactions, policy

    async def publish(
        self,
        job_id: UUID,
        resolutions: dict[str, dict[str, Any]],
        assessments: dict[str, dict[str, Any]],
        budget_available: bool,
    ) -> dict[str, Any]:
        async with self.transactions() as unit:
            job = await unit.archive.get_job(job_id)
            if not job:
                raise NotFoundError("Research job not found")
            if job["cancel_requested"]:
                return {"promoted": [], "unresolved": [], "cancelled": True}
            universe, continuity = UUID(job["universe_id"]), UUID(job["continuity_id"])
            await unit.graph.lock_scope(universe, continuity)
            job = await unit.archive.lock_job(job_id)
            if not job or job["cancel_requested"]:
                return {"promoted": [], "unresolved": [], "cancelled": True}
            # Locks acquired before re-reading graph, claims and publication history.
            findings = await unit.archive.findings(job_id)
            catalog = await unit.graph.catalog(universe, continuity)
            records = await unit.graph.records()
            by_claim = {r["claim_id"]: r for r in records}
            bound: dict[str, UUID] = {}
            withdrawals: list[dict[str, Any]] = []
            result: dict[str, Any] = {"promoted": [], "unresolved": []}
            ordered = sorted(findings, key=lambda c: (c["kind"] != "entity", c["id"]))
            # New identity groups precede references to those groups.
            ordered.sort(
                key=lambda c: (
                    c["kind"] != "entity",
                    resolutions.get(c["id"], {}).get("decision") == "SAME_ENTITY",
                )
            )
            for claim in ordered:
                payload, cid = claim["payload"], claim["id"]
                resolution = resolutions.get(cid, {})
                assessment = assessments.get(cid, {})
                previous = by_claim.get(cid)
                evidence = claim["evidence"]
                passages = {
                    str(p.id): p
                    for p in await unit.archive.get_passages(
                        list({UUID(e["source_id"]) for e in evidence})
                    )
                }
                exact = bool(evidence) and all(
                    e["passage_id"] in passages
                    and e["quote_start"] >= 0
                    and e["quote_end"] <= len(passages[e["passage_id"]].text)
                    and passages[e["passage_id"]].text[e["quote_start"] : e["quote_end"]]
                    == e["quote"]
                    and digest(passages[e["passage_id"]].text)
                    == passages[e["passage_id"]].content_hash
                    for e in evidence
                )
                if previous and not previous["reversed"]:
                    still_valid = (
                        exact
                        and claim["decision"] == "supported"
                        and not assessment.get("material_conflict")
                        and assessment.get("continuity_matches", True)
                        and assessment.get("in_universe", True)
                        and assessment.get("entity_type_valid", True)
                        and (
                            claim["kind"] == "entity"
                            or payload["source_name"] in bound
                            and payload["target_name"] in bound
                        )
                    )
                    if still_valid:
                        result["promoted"].append(previous)
                        if claim["kind"] == "entity":
                            bound[payload["name"]] = UUID(previous["target_id"])
                        continue
                    withdrawals.append(previous)
                    outcome = "RESEARCH_FURTHER" if budget_available else "KEEP_UNRESOLVED"
                    reason = "Previous publication no longer passes current evidence checks."
                    await unit.graph.decision(
                        UUID(cid),
                        job_id,
                        universe,
                        continuity,
                        resolution=resolution,
                        assessment=assessment,
                        policy={"outcome": outcome, "reason": reason, "version": "2.0"},
                    )
                    result["unresolved"].append(
                        {"claim_id": cid, "outcome": outcome, "reason": reason}
                    )
                    continue
                conflict = (
                    bool(previous)
                    or bool(assessment.get("material_conflict"))
                    or assessment.get("continuity_matches") is False
                    or assessment.get("in_universe") is False
                    or assessment.get("entity_type_valid") is False
                )
                target: UUID | None = None
                source_node: GraphNode | None = None
                target_node: GraphNode | None = None
                structural = exact and in_world_structure(payload, [e["quote"] for e in evidence])
                accepted = (
                    resolution.get("accepted", False)
                    and resolution.get("entity_type_valid") is True
                )
                sensitive_identity = bool(resolution.get("hidden_identity")) or any(
                    marker in e["quote"].casefold()
                    for e in evidence
                    for marker in (
                        "secret identity",
                        "true identity",
                        "real identity",
                        "正体",
                        "本名",
                    )
                )
                strong = sensitive_identity
                created = False
                snapshot: dict[str, Any] = {}
                if claim["kind"] == "entity":
                    strong = strong or (
                        payload["type"] == "CHARACTER"
                        and resolution.get("decision") in {"NEW_ENTITY", "DIFFERENT_ENTITY"}
                    )
                    accepted = accepted and resolution.get("canonical_id") is not None
                    target = UUID(resolution["canonical_id"]) if accepted else None
                    node = await unit.graph.node(target) if target else None
                    own_citations = resolution.get("evidence", [])
                    identity_grounded = bool(own_citations) and all(
                        any(
                            item["passage_id"] == e["passage_id"]
                            and item["quote"].strip() in e["quote"]
                            for e in evidence
                        )
                        for item in own_citations
                    )
                    accepted = accepted and identity_grounded
                    event = payload.get("event") or {}
                    anchor = event.get("identity_anchor")
                    if anchor:
                        trigger = event.get("trigger", "")
                        accepted = (
                            accepted
                            and bool(trigger)
                            and any(
                                trigger in e["quote"]
                                and anchor
                                == digest(
                                    "{}:{}:{}".format(
                                        e["source_id"],
                                        e["passage_start"]
                                        + e["quote_start"]
                                        + e["quote"].find(trigger),
                                        trigger,
                                    )
                                )
                                for e in evidence
                            )
                        )
                    if resolution.get("decision") in {"NEW_ENTITY", "DIFFERENT_ENTITY"}:
                        accepted = accepted and target == uuid5(
                            continuity, "event:" + anchor if anchor else "entity:" + cid
                        )
                    if node and resolution.get("decision") == "SAME_ENTITY":
                        current = next((n for n in catalog if n["id"] == str(node.id)), {})
                        names = [node.title, *current.get("aliases", [])]
                        exact_name = any(name_key(payload["name"]) == name_key(n) for n in names)
                        bridge = any(
                            explicit_name_bridge(payload["name"], n, e["quote"])
                            for n in names
                            for e in evidence
                        )
                        node_event = node.metadata.get("event")
                        node_anchor = (
                            node_event.get("identity_anchor")
                            if isinstance(node_event, dict)
                            else None
                        )
                        same_event = bool(anchor and anchor == node_anchor)
                        accepted = accepted and (exact_name or bridge or same_event)
                        if anchor and node_anchor and not same_event:
                            accepted = False
                    if node and (
                        node.universe_id != universe
                        or node.continuity_id != continuity
                        or node.type.value != payload["type"]
                    ):
                        accepted = False
                    if target and node is None and resolution.get("decision") == "SAME_ENTITY":
                        accepted = False  # Endpoint group was not promoted or state is stale.
                    if target and node is None and resolution.get("decision") != "SAME_ENTITY":
                        if any(
                            name_key(payload["name"]) == name_key(n)
                            for item in catalog
                            if item["type"] == payload["type"]
                            and not (
                                anchor
                                and (item.get("event") or {}).get("identity_anchor")
                                and (item.get("event") or {}).get("identity_anchor") != anchor
                            )
                            for n in [item["name"], *item["aliases"]]
                        ):
                            accepted = (
                                False  # Re-resolve a concurrently published possible homonym.
                            )
                    structural = structural and (
                        payload["type"] == "EVENT"
                        or any(name_key(payload["name"]) in name_key(e["quote"]) for e in evidence)
                    )
                    snapshot = {
                        "name": payload["name"],
                        "type": payload["type"],
                        "description": payload["description"],
                        "metadata": {"research_owned": True, "research_first_job": str(job_id)},
                    }
                    if payload.get("event"):
                        snapshot["metadata"]["event"] = payload["event"]
                else:
                    source, dest = (
                        bound.get(payload["source_name"]),
                        bound.get(payload["target_name"]),
                    )
                    source_node = await unit.graph.node(source) if source else None
                    target_node = await unit.graph.node(dest) if dest else None
                    accepted = bool(source_node and target_node)
                    kind = RelationshipType(payload["type"])
                    strong = kind in {
                        RelationshipType.CAUSED,
                        RelationshipType.ENABLED,
                        RelationshipType.REVEALED,
                    }
                    if source_node and target_node:
                        structural = (
                            structural
                            and source_node.id != target_node.id
                            and relation_structure(
                                kind,
                                source_node.type,
                                target_node.type,
                                [e["quote"] for e in evidence],
                                payload["source_name"],
                                payload["target_name"],
                            )
                        )
                        edge = GraphRelationship(
                            universe_id=universe,
                            continuity_id=continuity,
                            source_node_id=source_node.id,
                            target_node_id=target_node.id,
                            relationship_type=kind,
                            description=payload["description"],
                        )
                        edge.validate_endpoints(source_node, target_node)
                        existing = await unit.graph.edge(
                            source_node.id, target_node.id, kind.value, continuity
                        )
                        target = (
                            existing.id
                            if existing
                            else uuid5(
                                continuity, f"edge:{source_node.id}:{target_node.id}:{kind.value}"
                            )
                        )
                        opposites = {"ALLIED_WITH": "OPPOSED", "OPPOSED": "ALLIED_WITH"}
                        if kind.value in opposites and await unit.graph.edge(
                            source_node.id, target_node.id, opposites[kind.value], continuity
                        ):
                            conflict = True
                    snapshot = {
                        "description": payload["description"],
                        "type": payload["type"],
                        "source": str(source_node.id) if source_node else None,
                        "target": str(target_node.id) if target_node else None,
                    }
                semantic_key = (
                    ("entity:" + payload["type"] + ":" + name_key(payload["name"]))
                    if claim["kind"] == "entity"
                    else ("edge:" + str(target))
                )
                if any(
                    r["reversed"]
                    and r["universe_id"] == str(universe)
                    and r["continuity_id"] == str(continuity)
                    and r["data"].get("semantic_key") == semantic_key
                    and r["data"].get("snapshot", {}).get("description") == payload["description"]
                    and not any(
                        not other["reversed"] and other["target_id"] == r["target_id"]
                        for other in records
                    )
                    for r in records
                ):
                    conflict = True
                if (
                    claim["kind"] == "relationship"
                    and target
                    and any(r["reversed"] and r["target_id"] == str(target) for r in records)
                    and not any(
                        not r["reversed"] and r["target_id"] == str(target) for r in records
                    )
                ):
                    conflict = (
                        True  # Retractions are never silently overridden by replay or a new job.
                    )
                outcome, reason = self.policy.decide(
                    supported=claim["decision"] == "supported",
                    evidence_count=len(evidence) if exact else 0,
                    independent_count=independent_sources(evidence),
                    identity_accepted=bool(accepted),
                    structural=bool(structural),
                    conflict=conflict,
                    strong=strong,
                    budget_available=budget_available,
                )
                await unit.graph.decision(
                    UUID(cid),
                    job_id,
                    universe,
                    continuity,
                    resolution=resolution,
                    assessment=assessment,
                    policy={
                        "outcome": outcome,
                        "reason": reason,
                        "version": "2.0",
                        "independent_sources": independent_sources(evidence),
                    },
                )
                if outcome != "AUTO_PROMOTE" or target is None:
                    result["unresolved"].append(
                        {"claim_id": cid, "outcome": outcome, "reason": reason}
                    )
                    continue
                alias_ids = []
                if claim["kind"] == "entity":
                    node = await unit.graph.node(target)
                    if node is None:
                        node = GraphNode(
                            id=target,
                            universe_id=universe,
                            continuity_id=continuity,
                            type=NodeType(payload["type"]),
                            title=payload["name"],
                            summary=payload["description"],
                            metadata=snapshot["metadata"],
                        )
                        await unit.graph.add_node(node)
                        created = True
                        catalog.append(
                            {
                                "id": str(target),
                                "name": node.title,
                                "type": node.type.value,
                                "aliases": [],
                            }
                        )
                    alias_ids.append(
                        str(
                            await unit.graph.alias(
                                node, payload["name"], UUID(cid), sensitive_identity
                            )
                        )
                    )
                    if name_key(node.title) != name_key(payload["name"]) and any(
                        name_key(node.title) in name_key(e["quote"]) for e in evidence
                    ):
                        alias_ids.append(
                            str(
                                await unit.graph.alias(
                                    node, node.title, UUID(cid), sensitive_identity
                                )
                            )
                        )
                    bound[payload["name"]] = target
                else:
                    assert source_node and target_node
                    kind = RelationshipType(payload["type"])
                    if not await unit.graph.edge(
                        source_node.id, target_node.id, kind.value, continuity
                    ):
                        edge = GraphRelationship(
                            id=target,
                            universe_id=universe,
                            continuity_id=continuity,
                            source_node_id=source_node.id,
                            target_node_id=target_node.id,
                            relationship_type=kind,
                            description=payload["description"],
                        )
                        edge.validate_endpoints(source_node, target_node)
                        await unit.graph.add_edge(edge)
                        created = True
                record = await unit.graph.record(
                    claim,
                    job,
                    target,
                    created,
                    {
                        "policy_version": "2.0",
                        "semantic_key": semantic_key,
                        "snapshot": snapshot,
                        "alias_ids": alias_ids,
                        "evidence": evidence,
                        "resolution": resolution,
                        "assessment": assessment,
                    },
                )
                result["promoted"].append(record)
            for withdrawn in sorted(withdrawals, key=lambda item: item["kind"] != "relationship"):
                await unit.graph.rollback(
                    UUID(withdrawn["id"]),
                    "Automatic withdrawal: current evidence/type/endpoint checks no longer pass.",
                )
            await unit.archive.event(
                job_id,
                "research.promotion",
                {"promoted": len(result["promoted"]), "unresolved": len(result["unresolved"])},
            )
            return result

    async def rollback_promotion(self, record_id: UUID, reason: str) -> dict[str, Any]:
        async with self.transactions() as unit:
            record = await unit.graph.promotion_record(record_id)
            if not record:
                raise NotFoundError("Promotion record not found")
            await unit.graph.lock_scope(UUID(record["universe_id"]), UUID(record["continuity_id"]))
            corrected = await unit.graph.rollback(record_id, reason)
            await unit.archive.event(
                UUID(record["job_id"]),
                "research.corrected",
                {"promotion_id": str(record_id), "reason": reason},
            )
            return corrected

    async def rollback_job(self, job_id: UUID, reason: str) -> list[dict[str, Any]]:
        async with self.transactions() as unit:
            job = await unit.archive.get_job(job_id)
            if not job:
                raise NotFoundError("Research job not found")
            await unit.graph.lock_scope(UUID(job["universe_id"]), UUID(job["continuity_id"]))
            records = await unit.graph.records(job_id)
            results = [
                await unit.graph.rollback(UUID(r["id"]), reason)
                for r in sorted(records, key=lambda r: r["kind"] != "relationship")
            ]
            await unit.archive.event(
                job_id, "research.corrected", {"reason": reason, "records": len(results)}
            )
            return results
