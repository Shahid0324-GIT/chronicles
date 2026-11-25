"""Deterministic shared vocabulary for every arc writer and reviewer.

The bible is assembled from scoped, accepted records only. It carries no story
facts: it fixes how entities are named, how modality is written and what the
spoiler boundary is, so separate model calls cannot drift apart.
"""

import re
from collections.abc import Iterable
from typing import Any

from src.application.arc_contracts import BibleName, StoryBible

TENSE_RULE = (
    "Narrate completed events in the past tense. Keep intended, attempted, reported, "
    "denied and hypothetical actions marked as such; never present them as completed."
)


def build_story_bible(
    nodes: Iterable[Any], facts: list[dict[str, Any]], boundary: int | None
) -> StoryBible:
    """Collect English names only for entities that own accepted, in-scope facts."""
    owned: dict[str, list[dict[str, Any]]] = {}
    for fact in facts:
        owned.setdefault(fact["target_id"], []).append(fact)
    names = []
    for node in nodes:
        eligible = owned.get(str(node.id), [])
        if not eligible or node.type.value == "EVENT":
            continue
        aliases = sorted({f["payload"].get("name", "") for f in eligible} - {""})
        english = [a for a in aliases if a.isascii() and re.search(r"[A-Za-z]", a)]
        if node.title.isascii() and node.title not in english:
            english.append(node.title)
        if english:
            names.append(
                BibleName(
                    id=str(node.id),
                    english=max(english, key=len),
                    aliases=sorted(set(english)),
                )
            )
    fence = (
        f"Only sourced material through presentation position {boundary} is supplied. "
        "Do not allude to later developments."
        if boundary is not None
        else "Full-lore view: every supplied assertion is eligible."
    )
    return StoryBible(
        names=sorted(names, key=lambda n: n.id), tense_rule=TENSE_RULE, spoiler_fence=fence
    )


def prompt_bible(bible: StoryBible | None) -> dict[str, Any]:
    """The compact form included in every prompt; empty when no bible is available."""
    if bible is None:
        return {}
    return {
        "names": [{"name": n.english, "aliases": n.aliases} for n in bible.names],
        "tense": bible.tense_rule,
        "spoiler_fence": bible.spoiler_fence,
    }


def allowed_vocabulary(bible: StoryBible | None, texts: Iterable[str]) -> set[str]:
    """Case-folded words a proper name may use: bible names plus words in cited sources."""
    words = {
        w.casefold()
        for name in (bible.names if bible else [])
        for value in (name.english, *name.aliases)
        for w in re.findall(r"[A-Za-z]+", value)
    }
    for text in texts:
        words.update(w.casefold() for w in re.findall(r"[A-Za-z]+", text))
    return words


def unlicensed_names(text: str, vocabulary: set[str]) -> list[str]:
    """Mid-sentence capitalised words that neither the bible nor cited sources contain.

    Sentence-initial words are ordinary prose capitalisation and are not checked.
    """
    found: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        words = re.findall(r"\b[A-Za-z][A-Za-z'’-]*\b", sentence)
        for word in words[1:]:
            base = word.split("'")[0].split("’")[0]
            if base[:1].isupper() and base.casefold() not in vocabulary and base != "I":
                found.append(base)
    return list(dict.fromkeys(found))
