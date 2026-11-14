"""Source archive identities are separate from canonical graph identities."""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5


def digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    return " ".join(text.split())


def scope_structure(metadata: dict[str, str], start: int, end: int) -> dict[str, str]:
    """Do not carry unrelated section/link text across an approved excerpt boundary."""
    result = dict(metadata)
    for key in ("sections_json", "links_json"):
        if key not in result:
            continue
        values = []
        for item in json.loads(result[key]):
            if key == "links_json":
                if start <= item["start"] < end:
                    values.append({**item, "start": item["start"] - start})
            elif item["start"] < end and item["end"] > start:
                # A heading outside the selection must not leak its title into inference.
                values.append(
                    {
                        **item,
                        "title": item["title"] if item["start"] >= start else "",
                        "start": max(0, item["start"] - start),
                        "end": min(end, item["end"]) - start,
                    }
                )
        result[key] = json.dumps(values, ensure_ascii=False)
    result["structure_selection_start"] = str(start)
    return result


@dataclass(frozen=True)
class SourceDocument:
    id: UUID
    universe_id: UUID
    continuity_id: UUID
    url: str
    title: str
    publisher: str
    text: str
    content_hash: str
    retrieved_at: datetime
    permission_basis: str
    source_scope: str
    public_web: bool
    truncated: bool
    independence_key: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourcePassage:
    id: UUID
    source_id: UUID
    ordinal: int
    start: int
    end: int
    text: str
    content_hash: str
    section_title: str = ""


def passages_for(source: SourceDocument, size: int = 1400) -> list[SourcePassage]:
    passages: list[SourcePassage] = []
    start = 0
    sections = json.loads(source.provenance.get("sections_json", "[]"))
    section_starts = sorted({s["start"] for s in sections if 0 <= s["start"] < len(source.text)})
    while start < len(source.text):
        end = min(start + size, len(source.text))
        end = next((b for b in section_starts if start < b < end), end)
        if end < len(source.text):
            boundaries = list(re.finditer(r"[.!?。！？](?:\s|$)", source.text[start:end]))
            if boundaries and boundaries[-1].end() >= size // 2:
                end = start + boundaries[-1].end()
        text = source.text[start:end]
        ordinal = len(passages)
        passages.append(
            SourcePassage(
                uuid5(NAMESPACE_URL, f"chronicles:passage:{source.id}:{start}:{digest(text)}"),
                source.id,
                ordinal,
                start,
                start + len(text),
                text,
                digest(text),
                next(
                    (s["title"] for s in reversed(sections) if s["start"] <= start < s["end"]), ""
                ),
            )
        )
        start = end
    return passages


def quotation_exists(quote: str, passage: SourcePassage) -> bool:
    value = normalize(quote)
    return len(value) >= 12 and value in normalize(passage.text)
