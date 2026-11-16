"""Source presentation coordinates; these never establish in-world causality."""

from typing import Any

POSITION_BASES = {"broadcast-presentation": "episode", "manga-chapter": "chapter"}


def source_position(source: dict[str, Any], basis: str | None = None) -> int | None:
    provenance = source.get("provenance", {})
    candidate = provenance.get("position_basis")
    value = provenance.get("presentation_position")
    if candidate not in POSITION_BASES or (basis and candidate != basis):
        return None
    return value if type(value) is int and value >= 1 else None


def position_basis(facts: list[dict[str, Any]]) -> str:
    bases = {
        s.get("provenance", {}).get("position_basis")
        for f in facts
        for s in f["sources"]
        if source_position(s) is not None
    }
    return next(iter(bases)) if len(bases) == 1 else "unresolved"
