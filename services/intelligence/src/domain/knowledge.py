"""Deterministic publication rules. Model confidence is intentionally absent."""

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import urlsplit

from src.domain.value_objects import NodeType, RelationshipType


def name_key(name: str) -> str:
    value = unicodedata.normalize("NFKC", name).casefold()
    return " ".join(
        "".join(" " if unicodedata.category(c)[0] in {"P", "Z"} else c for c in value).split()
    )


def script(name: str) -> str:
    scripts = set()
    for char in name:
        if char.isalpha():
            label = unicodedata.name(char, "")
            scripts.add(
                "latin"
                if "LATIN" in label
                else "japanese"
                if any(s in label for s in ("CJK", "HIRAGANA", "KATAKANA"))
                else "other"
            )
    return "+".join(sorted(scripts))


def order_key(name: str) -> str:
    value = name_key(name)
    return " ".join(sorted(value.split())) if script(name) == "latin" else value


def explicit_name_bridge(left: str, right: str, text: str) -> bool:
    """An adjacent bilingual/name annotation or explicit alias phrase, not mere co-occurrence."""
    value = name_key(text)
    left_key, right_key = name_key(left), name_key(right)
    if not left_key or not right_key or left_key == right_key:
        return False

    def variants(name: str) -> list[str]:
        key = name_key(name)
        parts = key.split()
        return (
            [key, " ".join(reversed(parts))]
            if script(name) == "latin" and len(parts) == 2
            else [key]
        )

    for a in variants(left):
        for b in variants(right):
            if a == b:
                continue
            for x, y in ((a, b), (b, a)):
                start, end = value.find(x), value.find(y)
                if start < 0 or end < 0:
                    continue
                gap = value[start + len(x) : end]
                if 0 <= len(gap) <= 55 and (
                    any(
                        marker in gap
                        for marker in ("also known as", "aka", "called", "こと", "通称", "本名")
                    )
                    or (not gap.strip() and script(x) != script(y))
                ):
                    return True
    return False


def independent_sources(evidence: list[dict[str, str]]) -> int:
    # Same normalized document and same publisher family never count twice.
    hashes, publishers = set(), set()
    excerpts: list[str] = []
    for item in evidence:
        fingerprint = item["content_hash"]
        if fingerprint in hashes:
            continue
        quotation = name_key(item.get("quote", ""))
        if quotation and any(
            SequenceMatcher(None, quotation, previous).ratio() >= 0.85 for previous in excerpts
        ):
            continue
        if quotation:
            excerpts.append(quotation)
        hashes.add(fingerprint)
        host = (urlsplit(item["url"]).hostname or "local-import").lower()
        parts = host.split(".")
        family = ".".join(
            parts[-3:] if len(parts) > 2 and parts[-2] in {"co", "com", "org"} else parts[-2:]
        )
        publishers.add(family)
    return len(publishers)


def relation_structure(
    kind: RelationshipType, source: NodeType, target: NodeType, texts: list[str]
) -> bool:
    if kind in {RelationshipType.CAUSED, RelationshipType.ENABLED, RelationshipType.PRECEDES}:
        if source != NodeType.EVENT or target != NodeType.EVENT:
            return False
    if kind == RelationshipType.PARTICIPATED_IN and target != NodeType.EVENT:
        return False
    if kind == RelationshipType.OCCURRED_AT and (
        source != NodeType.EVENT or target != NodeType.LOCATION
    ):
        return False
    if kind == RelationshipType.MEMBER_OF and target != NodeType.FACTION:
        return False
    if kind == RelationshipType.CAUSED:
        markers = (
            r"\b(because|caused|therefore|resulted in|led to|as a result)\b"
            r"|ため|ので|によって|原因|結果"
        )
        return any(re.search(markers, text, re.IGNORECASE) for text in texts)
    return True


@dataclass(frozen=True)
class PromotionPolicy:
    minimum_sources: int = 1
    strong_sources: int = 2

    def decide(
        self,
        *,
        supported: bool,
        evidence_count: int,
        independent_count: int,
        identity_accepted: bool,
        structural: bool,
        conflict: bool,
        strong: bool,
        budget_available: bool,
    ) -> tuple[str, str]:
        if conflict:
            reason = "Unresolved material contradiction or continuity ambiguity."
        elif not supported or not evidence_count:
            reason = "Missing supported exact evidence."
        elif not identity_accepted:
            reason = "Identity or endpoint resolution is ambiguous."
        elif not structural:
            reason = "Deterministic identity/relationship structure was not established."
        elif independent_count < (
            max(self.strong_sources, self.minimum_sources) if strong else self.minimum_sources
        ):
            reason = "Insufficient independent publisher families for this claim strength."
        else:
            return (
                "AUTO_PROMOTE",
                "Exact evidence, semantic assessment, identity and domain policy pass.",
            )
        return ("RESEARCH_FURTHER" if budget_available else "KEEP_UNRESOLVED"), reason
