"""Source-context identity attestations; hashes fence context, never establish identity."""

import json
from typing import Any

from src.domain.research import digest


def sourced_identity_catalog(
    catalog: list[dict[str, Any]],
    records: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    universe: str,
    continuity: str,
    source_revisions: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Bind live canonical name support to exact citations, without interpreting names."""
    quotes = {(c["passage_id"], c["quote"]) for c in citations}
    result = [{**n, "source_identity_context": []} for n in catalog]
    by_id = {n["id"]: n for n in result}
    for record in records:
        if (
            record.get("reversed")
            or record["kind"] != "entity"
            or record["universe_id"] != universe
            or record["continuity_id"] != continuity
        ):
            continue
        node = by_id.get(record["target_id"])
        data = record["data"]
        name = data.get("snapshot", {}).get("name")
        if (
            not node
            or node["type"] != "CHARACTER"
            or not name
            or name not in [node["name"], *node.get("aliases", [])]
            or data.get("resolution", {}).get("hidden_identity")
        ):
            continue
        for evidence in data.get("evidence", []):
            if evidence.get("content_hash") and evidence["content_hash"] != (
                source_revisions or {}
            ).get(evidence["source_id"]):
                continue
            if (evidence["passage_id"], evidence["quote"]) not in quotes:
                continue
            # Source-only inference may expose only a source spelling, never an
            # editable catalog label. This is a disclosure check, not identity matching.
            if name.casefold() not in evidence["quote"].casefold():
                continue
            context = {
                "record_id": record["id"],
                "canonical_target_id": node["id"],
                "canonical_source_name": name,
                "passage_id": evidence["passage_id"],
                "quote": evidence["quote"],
            }
            context["support_key"] = digest(json.dumps(context, sort_keys=True, ensure_ascii=False))
            if len(node["source_identity_context"]) < 3:
                node["source_identity_context"].append(context)
    return result


def identity_catalog_key(catalog: list[dict[str, Any]]) -> str:
    """Fence the available identities and descriptions used by the semantic review."""
    return digest(
        json.dumps(
            sorted(
                (
                    n["id"],
                    n["name"],
                    n.get("description", ""),
                    sorted(
                        {
                            a
                            for a in n.get("aliases", [])
                            if a not in n.get("native_alias_proofs", {})
                        }
                    ),
                )
                for n in catalog
                if n["type"] == "CHARACTER"
            ),
            ensure_ascii=False,
        )
    )


def identity_context_key(
    candidate: str, target: str, title: str, kind: str, continuity: str, quotations: list[str]
) -> str:
    return digest(
        json.dumps(
            [candidate, target, title, kind, continuity, sorted(set(quotations))],
            ensure_ascii=False,
        )
    )


def current_context_identity(
    resolution: dict[str, Any],
    payload: dict[str, Any],
    target: str,
    title: str,
    continuity: str,
    quotations: list[str],
    catalog: list[dict[str, Any]],
) -> bool:
    proof = resolution.get("native_identity") or {}
    review = proof.get("review") or {}
    identity_quotes = [c["quote"] for c in resolution.get("evidence", [])]
    contexts: list[dict[str, Any]] = next(
        (n.get("source_identity_context", []) for n in catalog if n["id"] == target), []
    )
    live_support = {c["support_key"] for c in contexts}
    return bool(
        resolution.get("proof") == "source_context_identity"
        and review.get("decision") == "same"
        and (
            review.get("alternative_status") == "distinguished"
            or (
                review.get("alternative_status") == "none_supplied"
                and proof.get("alternative_count") == 0
                and sum(
                    n["type"] == "CHARACTER"
                    and (
                        not proof.get("source_only")
                        or any(
                            c["quote"] in identity_quotes
                            for c in n.get("source_identity_context", [])
                        )
                    )
                    for n in catalog
                )
                == 1
            )
        )
        and proof.get("catalog_key") == identity_catalog_key(catalog)
        and set(proof.get("canonical_support_keys", [])) <= live_support
        and identity_quotes
        and set(identity_quotes) <= set(quotations)
        and proof.get("context_key")
        == identity_context_key(
            payload["name"], target, title, payload["type"], continuity, identity_quotes
        )
    )
