"""Token-aware evidence selection; no model calls or invented graph context."""

import json
from typing import Any, TypedDict
from urllib.parse import urlsplit

from src.application.research_frontier import terms


def source_families(sources: list[tuple[str, str, str | None]]) -> dict[str, str]:
    """Same publisher or explicit derivative links form one connected source family."""
    components: list[set[str]] = []
    identities = {}
    for identifier, url, derivative in sources:
        keys = {"host:" + (urlsplit(url).hostname or identifier)}
        if derivative:
            keys.add("derived:" + derivative)
        identities[identifier] = keys
        changed = True
        while changed:
            changed = False
            for component in list(components):
                if keys & component:
                    keys |= component
                    components.remove(component)
                    changed = True
        components.append(keys)
    return {
        identifier: min(component)
        for identifier, keys in identities.items()
        for component in components
        if keys & component
    }


def token_estimate(value: Any) -> int:
    # Conservative UTF-8 estimate, not a tokenizer measurement. Include schema separately.
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return (len(text.encode("utf-8")) + 2) // 3


class EvidenceDossier(TypedDict):
    objective: str
    facts: list[dict[str, Any]]
    estimated_tokens: int
    omitted_facts: int
    missing_information: list[str]
    selection: str


class EvidenceDossierBuilder:
    @staticmethod
    def compact_fact(fact: dict[str, Any]) -> dict[str, Any]:
        """Keep inference evidence, not the archive's complete link/section index.

        Eligibility is checked by the scoped caller before selection. Exact quote,
        offsets, passage/source IDs and revisions remain attached; archive rows do
        not change. Models never need a document's entire navigation metadata.
        """
        useful = {
            "category",
            "authority",
            "language",
            "cloud_content_allowed",
            "registry_id",
            "registry_revision",
            "presentation_position",
            "position_basis",
            "extraction_version",
            "attribution_url",
            "derived_from",
        }
        return {
            **fact,
            "payload": {k: v for k, v in fact["payload"].items() if k != "evidence"},
            "sources": [
                {
                    **s,
                    "provenance": {k: v for k, v in s.get("provenance", {}).items() if k in useful},
                }
                for s in fact.get("sources", [])
            ],
        }

    def select(
        self,
        facts: list[dict[str, Any]],
        objective: str,
        token_budget: int,
        priority_ids: set[str] | None = None,
        *,
        require_relevance: bool = False,
    ) -> EvidenceDossier:
        query = terms(objective)

        def relevance(fact: dict[str, Any]) -> int:
            payload = fact["payload"]
            content = [
                payload.get(key, "")
                for key in ("name", "description", "source_name", "target_name", "event")
            ]
            return len(query & terms(json.dumps(content, ensure_ascii=False)))

        ranked = sorted(
            [
                fact
                for fact in facts
                if not require_relevance or relevance(fact) or fact["id"] in (priority_ids or set())
            ],
            key=lambda f: (
                -int(f["id"] in (priority_ids or set())),
                -relevance(f),
                -int(f.get("kind") == "relationship"),
                str(f["id"]),
            ),
        )
        selected = []
        used = 0
        hashes = set()
        for fact in ranked:
            selected_fact = self.compact_fact(fact)
            size = token_estimate(selected_fact)
            identity = json.dumps(
                [fact.get("target_id"), fact["payload"], fact.get("sources")], sort_keys=True
            )
            if identity in hashes or used + size > token_budget:
                continue
            selected.append(selected_fact)
            hashes.add(identity)
            used += size
        return {
            "objective": objective,
            "facts": selected,
            "estimated_tokens": used,
            "omitted_facts": len(facts) - len(selected),
            "missing_information": [] if selected else ["No eligible accepted facts"],
            "selection": "compact-content-relevance-and-relationships-v3",
        }


def expand_queries(
    objective: str, questions: list[str], aliases: list[str], categories: list[str], limit: int
) -> list[str]:
    concise = " ".join(objective.split()[:16])
    queries = [*questions, concise]
    queries += [f"{alias} {question}" for alias in aliases[:2] for question in questions[:2]]
    queries += [f"{objective} {category} references" for category in categories]
    selected: list[str] = []
    fingerprints: list[set[str]] = []
    for query in queries:
        key = terms(query)
        if not key or any(len(key & old) / max(1, len(key | old)) > 0.85 for old in fingerprints):
            continue
        selected.append(query[:1500])
        fingerprints.append(key)
        if len(selected) >= limit:
            break
    return selected if limit > 0 else []
