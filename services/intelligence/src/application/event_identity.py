from typing import Any

from src.domain.knowledge import name_key, same_event_context


def same_scoped_occurrence(
    left: dict[str, Any], right: dict[str, Any], catalog: list[dict[str, Any]]
) -> bool:
    """Compare source spans with uniquely resolved existing aliases, never fuzzy names."""
    for event in [left, right]:
        if not isinstance(event.get("participants", []), list) or not all(
            isinstance(n, str) for n in event.get("participants", [])
        ):
            return False
        if event.get("location") is not None and not isinstance(event["location"], str):
            return False
    aliases: dict[str, set[str]] = {}
    for node in catalog:
        if node["type"] not in {"CHARACTER", "LOCATION"}:
            continue
        for name in [node["name"], *node.get("aliases", [])]:
            aliases.setdefault(name_key(name), set()).add(node["id"])

    def key(name: str) -> str:
        choices = aliases.get(name_key(name), set())
        return next(iter(choices)) if len(choices) == 1 else name_key(name)

    def normalized(event: dict[str, Any]) -> dict[str, Any]:
        return {
            **event,
            "participants": [key(n) for n in event.get("participants", [])],
            "location": key(event["location"]) if event.get("location") else None,
        }

    return same_event_context(normalized(left), normalized(right))
