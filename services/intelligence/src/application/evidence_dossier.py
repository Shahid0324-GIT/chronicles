"""Token-aware evidence selection; no model calls or invented graph context."""

import json
from typing import Any, TypedDict

from src.application.research_frontier import terms


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
    def select(
        self, facts: list[dict[str, Any]], objective: str, token_budget: int
    ) -> EvidenceDossier:
        query = terms(objective)
        ranked = sorted(
            facts,
            key=lambda f: (
                -len(query & terms(json.dumps(f["payload"], ensure_ascii=False))),
                -int(f.get("kind") == "relationship"),
                str(f["id"]),
            ),
        )
        selected = []
        used = 0
        hashes = set()
        for fact in ranked:
            size = token_estimate(fact)
            identity = json.dumps(
                [fact.get("target_id"), fact["payload"], fact.get("sources")], sort_keys=True
            )
            if identity in hashes or used + size > token_budget:
                continue
            selected.append(fact)
            hashes.add(identity)
            used += size
        return {
            "objective": objective,
            "facts": selected,
            "estimated_tokens": used,
            "omitted_facts": len(facts) - len(selected),
            "missing_information": [] if selected else ["No eligible accepted facts"],
            "selection": "relevance-and-relationships-v1",
        }


def expand_queries(
    objective: str, questions: list[str], aliases: list[str], categories: list[str], limit: int
) -> list[str]:
    queries = [objective, *questions]
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
