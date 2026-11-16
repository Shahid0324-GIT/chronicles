"""Reader state derived from existing artifacts, never a substitute for evidence."""

from typing import Any


def presentation_state(stored: dict[str, Any] | None, revision: str) -> dict[str, str]:
    if not stored:
        return {
            "status": "not_generated",
            "reason": "Verified knowledge is available; its reader account has not been generated.",
        }
    if stored["knowledge_revision"] != revision:
        return {
            "status": "outdated",
            "reason": "Knowledge changed; the reader presentation needs regeneration.",
        }
    status = stored["grounding_status"]
    return {
        "status": status,
        "reason": "Validated source-backed presentation."
        if status == "validated"
        else "Reader prose did not pass validation. Verified evidence remains available.",
    }


def accepted_text(facts: list[dict[str, Any]], target: str | None = None) -> tuple[str, str]:
    """Expose accepted assertions, not raw mutable canonical summaries or unverified drafts."""
    eligible = [
        f for f in facts if f["kind"] == "entity" and (target is None or f["target_id"] == target)
    ]
    eligible.sort(key=lambda f: (f["payload"].get("name", ""), f["id"]))
    if not eligible:
        return (
            "Verified source evidence",
            "Open the cited evidence to inspect the accepted knowledge.",
        )
    payload = eligible[0]["payload"]
    return payload.get("name", "Verified source evidence"), payload.get("description", "")
