"""Deterministic publication rules. Model confidence is intentionally absent."""

import re
import unicodedata
from collections.abc import Mapping
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


def same_event_context(left: Mapping[str, object], right: Mapping[str, object]) -> bool:
    if not left.get("source_id") or left.get("source_id") != right.get("source_id"):
        return False
    bounds = [
        left.get("trigger_start"),
        left.get("trigger_end"),
        right.get("trigger_start"),
        right.get("trigger_end"),
    ]
    if not all(isinstance(v, int) for v in bounds):
        return False
    a, b, c, d = (int(v) for v in bounds if isinstance(v, int))
    if max(a, c) >= min(b, d):
        return False

    def participants(value: object) -> set[str]:
        return {name_key(str(v)) for v in value} if isinstance(value, list) else set()

    if participants(left.get("participants")) != participants(right.get("participants")):
        return False
    if (
        left.get("location")
        and right.get("location")
        and name_key(str(left["location"])) != name_key(str(right["location"]))
    ):
        return False
    return True


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
                if start < 0 or end < start + len(x):
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


def source_name_bridge(left: str, right: str, texts: list[str]) -> bool:
    if any(explicit_name_bridge(left, right, text) for text in texts):
        return True
    # Preserve parenthetical readings before punctuation normalization, then follow
    # a separately evidenced bilingual annotation. Co-occurrence is not a bridge.
    pattern = re.compile(re.escape(left) + r"\s*[（(]([^）)\s]{1,60})[）)]")
    return any(
        explicit_name_bridge(match.group(1), right, other)
        for text in texts
        for match in pattern.finditer(text)
        for other in texts
    )


def same_full_name_order(left: str, right: str) -> bool:
    return (
        script(left) == script(right) == "latin"
        and len(name_key(left).split()) == 2
        and order_key(left) == order_key(right)
    )


def short_name_bridge(short: str, full: str, texts: list[str]) -> bool:
    key = name_key(short)
    parts = name_key(full).split()
    if script(short) != "latin" or len(key.split()) != 1 or len(parts) != 2 or key not in parts:
        return False
    for text in texts:
        value = name_key(text)
        for fullname in (" ".join(parts), " ".join(reversed(parts))):
            at = value.find(fullname)
            if at < 0:
                continue
            remainder = value[:at] + value[at + len(fullname) :]
            if re.search(r"\b" + re.escape(key) + r"\b", remainder) or any(
                re.search(r"\b" + re.escape(key) + r"\b", name_key(other))
                for other in texts
                if other != text
            ):
                return True
    return False


def independent_sources(evidence: list[dict[str, str]]) -> int:
    # Same normalized document and same publisher family never count twice.
    hashes = set()
    parents: dict[str, str] = {}
    families: list[str] = []

    def root(value: str) -> str:
        parents.setdefault(value, value)
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

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
        families.append(family)
        key = (item.get("independence_key") or family).casefold().strip()
        parents[root(family)] = root(key)
    return len({root(family) for family in families})


def relation_structure(
    kind: RelationshipType,
    source: NodeType,
    target: NodeType,
    texts: list[str],
    source_name: str | None = None,
    target_name: str | None = None,
) -> bool:
    if kind in {RelationshipType.CAUSED, RelationshipType.ENABLED, RelationshipType.PRECEDES}:
        if source != NodeType.EVENT or target != NodeType.EVENT:
            return False
    if kind == RelationshipType.PARTICIPATED_IN and (
        target != NodeType.EVENT or source not in {NodeType.CHARACTER, NodeType.FACTION}
    ):
        return False
    if kind == RelationshipType.OCCURRED_AT and (
        source != NodeType.EVENT or target != NodeType.LOCATION
    ):
        return False
    if kind == RelationshipType.MEMBER_OF and (
        target != NodeType.FACTION or source not in {NodeType.CHARACTER, NodeType.FACTION}
    ):
        return False
    if kind in {RelationshipType.ALLIED_WITH, RelationshipType.OPPOSED} and (
        source not in {NodeType.CHARACTER, NodeType.FACTION}
        or target not in {NodeType.CHARACTER, NodeType.FACTION}
    ):
        return False
    if kind == RelationshipType.PRECEDES and not any(
        re.search(
            r"\b(before|after|earlier|later|preceded|followed)\b|先|前|後", text, re.IGNORECASE
        )
        for text in texts
    ):
        return False
    if kind == RelationshipType.ENABLED and not any(
        re.search(
            r"\b(enabled|allowed|made possible|made it possible)\b|可能に|できるよう|おかげ",
            text,
            re.IGNORECASE,
        )
        for text in texts
    ):
        return False
    if kind == RelationshipType.FORESHADOWS and not any(
        re.search(r"foreshadow|hint|伏線|暗示", text, re.IGNORECASE) for text in texts
    ):
        return False
    if kind in {RelationshipType.RELATED_TO, RelationshipType.CONNECTED_TO} and not any(
        re.search(r"related|connected|linked|関係|関連|繋|つなが", text, re.IGNORECASE)
        for text in texts
    ):
        return False
    if kind == RelationshipType.CAUSED:
        markers = (
            r"\b(because|caused|therefore|resulted in|led to|as a result)\b"
            r"|ため|ので|によって|原因|結果"
        )
        for text in texts:
            if not re.search(markers, text, re.IGNORECASE):
                continue
            if re.search(r"\b(not|never|didn't)\b|ではない|なかった|否定", text, re.IGNORECASE):
                continue
            if source_name is None or target_name is None:
                return True
            value = name_key(text)
            a, b = value.find(name_key(source_name)), value.find(name_key(target_name))
            if a < 0 or b < 0:
                continue  # Strong claims need literal event anchors, not guessed translations.
            forward = re.search(
                r"caused|therefore|resulted in|led to|ため|ので|によって|原因|結果", value
            )
            because = value.find("because")
            if forward and a < forward.start() < b:
                return True
            if because >= 0 and (because < a < b or b < because < a):
                return True
        return False
    return True


def in_world_structure(payload: dict[str, str], quotes: list[str]) -> bool:
    name = payload.get("name", "")
    description = payload.get("description", "")
    if payload.get("type") == "EVENT" and re.fullmatch(
        r"(?:第[0-9０-９一二三四五六七八九十]+話|episode\s*\d+|#\d+)", name.strip(), re.IGNORECASE
    ):
        return False
    # These describe the publication/marketing of a work, not events in its fictional world.
    return not re.search(
        r"コラボカフェ|開催決定|TVアニメ初イベント|放送開始|声優|作画監督|脚本："
        r"|\b(voice actor|collaboration cafe|broadcast date|blu-ray|merchandise)\b",
        description,
        re.IGNORECASE,
    )


@dataclass(frozen=True)
class PromotionPolicy:
    minimum_sources: int = 1
    strong_sources: int = 2

    def __post_init__(self) -> None:
        if self.minimum_sources < 1 or self.strong_sources < 2:
            raise ValueError("Publication needs positive ordinary and at least two strong sources")

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
