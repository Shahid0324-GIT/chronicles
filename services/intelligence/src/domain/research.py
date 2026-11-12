"""Source archive identities are separate from canonical graph identities."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5


def digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    return " ".join(text.split())


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


@dataclass(frozen=True)
class SourcePassage:
    id: UUID
    source_id: UUID
    ordinal: int
    start: int
    end: int
    text: str
    content_hash: str


def passages_for(source: SourceDocument, size: int = 1400) -> list[SourcePassage]:
    passages = []
    for ordinal, start in enumerate(range(0, len(source.text), size)):
        text = source.text[start : start + size]
        passages.append(
            SourcePassage(
                uuid5(NAMESPACE_URL, f"chronicles:passage:{source.id}:{start}:{digest(text)}"),
                source.id,
                ordinal,
                start,
                start + len(text),
                text,
                digest(text),
            )
        )
    return passages


def quotation_exists(quote: str, passage: SourcePassage) -> bool:
    value = normalize(quote)
    return len(value) >= 12 and value in normalize(passage.text)
