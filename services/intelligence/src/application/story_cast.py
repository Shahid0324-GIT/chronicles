"""Who and what gets an entry: which names are one subject, and how each is introduced.

A model judges small groups of names beside the sentences that first mention them. Code
decides what it may do: spellings merge only when they are variants of one name, an
introduction needs a cited sentence, and a name the story keeps using is never dropped.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field

from src.application.knowledge_presentation import Infer
from src.application.research_contracts import StructuredModel

NameKind = Literal["CHARACTER", "LOCATION", "OBJECT", "MYSTERY"]
BATCH = 16
# Sentences shown for each name, taken from where the story first mentions it.
EXCERPTS = 3
# A name this many sentences use matters to the story, whatever the model says.
ALWAYS_KEPT = 8
ARTICLES = {"the", "a", "an"}


class CastEntry(StructuredModel):
    name: str
    kind: NameKind
    keep: bool = True
    same_as: list[str] = Field(default_factory=list)
    introduction: str = ""
    sentences: list[int] = Field(default_factory=list)


class CastList(StructuredModel):
    entries: list[CastEntry] = Field(max_length=40)


@dataclass
class Cast:
    """Subjects by their main spelling, and the main spelling for every spelling kept."""

    subjects: dict[str, dict[str, Any]]
    alias_of: dict[str, str]
    notes: list[str]


def name_key(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold()))


# "[4]" or "(1, 2, 3)": a single number in round brackets may be part of the story.
CITATION_MARKS = re.compile(r"\s*(?:\[\d+(?:\s*,\s*\d+)*\]|\(\d+(?:\s*,\s*\d+)+\))")


def clip(value: str, limit: int) -> str:
    # Models sometimes leave sentence numbers in their prose.
    value = " ".join(CITATION_MARKS.sub("", value).split())
    if len(value) <= limit:
        return value
    cut = value[: limit - 3]
    return cut[: cut.rfind(" ")] + "..." if " " in cut else cut + "..."


def same_name(first: str, second: str, kind: str) -> bool:
    """Whether two spellings are one name, such as "Coliseum" and "Olympus Coliseum".

    Related things are not one subject, so a wider match is left to the reviewer.
    """
    a, b = ([w for w in name_key(n).split() if w not in ARTICLES] for n in (first, second))
    short, long = sorted((a, b), key=len)
    if not short:
        return False
    if short == long:
        return True
    ends = long[-len(short) :] == short
    if kind == "CHARACTER":
        return ends or long[: len(short)] == short
    return kind == "LOCATION" and ends


def mention_sentences(spelling: str, keyed: dict[int, str]) -> list[int]:
    return [n for n, text in keyed.items() if f" {spelling} " in f" {text} "]


async def name_cast(
    title: str,
    mentions: dict[str, dict[str, Any]],
    texts: dict[int, str],
    position: dict[int, int],
    infer: Infer,
) -> Cast:
    keyed = {n: name_key(text) for n, text in texts.items()}
    used = {
        spelling: sorted(
            {*mention_sentences(spelling, keyed), *mention["ids"]},
            key=lambda n: (position[n], n),
        )
        for spelling, mention in mentions.items()
    }
    # Open questions are their own description; related names sit in the same request.
    asked = sorted(
        (s for s, m in mentions.items() if m["kind"] != "MYSTERY"),
        key=lambda s: (mentions[s]["kind"], s.split()[::-1]),
    )
    entries: dict[str, tuple[CastEntry, str]] = {}

    async def judge(group: list[str], reminder: str) -> None:
        first = {
            # Only the earliest part, so an introduction never tells later events.
            s: [n for n in used[s] if position[n] == position[used[s][0]]][:EXCERPTS]
            for s in group
        }
        shown = sorted({n for ids in first.values() for n in ids})
        local = {n: i for i, n in enumerate(shown, 1)}
        reply = CastList.model_validate(
            await infer(
                reminder + "These names appear in one story arc. Return one entry for each "
                "subject. keep is true for a named person, creature, group, place or object "
                "that matters to the story, and false for generic things such as a desert, a "
                "bedroom or a book, and for stray phrases. Correct the kind if needed. In "
                "same_as list only other spellings of that very same subject from "
                "all_names, never a related person, a place inside it or a thing it owns. "
                "In introduction say in one or two original sentences who or what it is, "
                "using only its own excerpts, and give those excerpt numbers in sentences.\n"
                'Return only JSON: {"entries":[{"name":"","kind":"CHARACTER","keep":true,'
                '"same_as":[],"introduction":"","sentences":[1]}]}\n'
                + json.dumps(
                    {
                        "arc": title,
                        "all_names": [mentions[s]["name"] for s in asked],
                        "subjects": [
                            {
                                "name": mentions[s]["name"],
                                "kind": mentions[s]["kind"],
                                "excerpts": [local[n] for n in first[s]],
                            }
                            for s in group
                        ],
                        "excerpts": {str(local[n]): texts[n] for n in shown},
                    },
                    ensure_ascii=False,
                ),
                CastList,
                "presentation",
            )
        )
        for entry in reply.entries:
            spelling = name_key(entry.name)
            if spelling not in group:
                continue
            own = {local[n] for n in first[spelling]}
            appears = position[used[spelling][0]]
            cited = [shown[i - 1] for i in entry.sentences if 0 < i <= len(shown)]
            introduction = clip(entry.introduction, 350)
            # Its own sentence must support it, and nothing cited may come from later.
            if (
                not own & set(entry.sentences)
                or any(position[n] > appears for n in cited)
                or len(introduction) < 12
            ):
                introduction = ""
            earlier = entries.get(spelling)
            # A second answer only fills in what the first one left empty.
            entries[spelling] = (earlier[0] if earlier else entry, introduction)

    for start in range(0, len(asked), BATCH):
        await judge(asked[start : start + BATCH], "")
    missing = [
        s
        for s in asked
        if not (s in entries and entries[s][1])
        and (s not in entries or entries[s][0].keep or len(used[s]) >= ALWAYS_KEPT)
    ]
    for start in range(0, len(missing), BATCH):
        await judge(
            missing[start : start + BATCH],
            "Each subject below still needs an introduction: write one for every subject "
            "and cite its excerpt numbers. ",
        )

    subjects: dict[str, dict[str, Any]] = {}
    alias_of: dict[str, str] = {}
    notes: list[str] = []
    left_out: list[str] = []
    # The names the story uses most claim their other spellings first.
    for spelling in sorted(mentions, key=lambda s: (-len(used[s]), s)):
        if spelling in alias_of:
            continue
        mention = mentions[spelling]
        judged, introduction = entries.get(spelling, (None, ""))
        kind = judged.kind if judged else mention["kind"]
        if judged and not judged.keep and len(used[spelling]) < ALWAYS_KEPT:
            left_out.append(mention["name"])
            continue
        members = [spelling]
        for other in map(name_key, judged.same_as if judged else []):
            if other not in mentions or other in alias_of or other == spelling:
                continue
            if mentions[other]["kind"] == mention["kind"] and same_name(
                mention["name"], mentions[other]["name"], kind
            ):
                members.append(other)
            else:
                notes.append(
                    f"Kept '{mentions[other]['name']}' apart from '{mention['name']}'; merge "
                    "them in edits if they are the same"
                )
        if kind == "MYSTERY":
            introduction = clip(f"An open question in this arc: {mention['name']}.", 350)
        subjects[spelling] = {
            "name": clip(mention["name"], 100),
            "kind": kind,
            "introduction": introduction
            or next((entries[m][1] for m in members if m in entries and entries[m][1]), ""),
            "aliases": [mentions[m]["name"] for m in members[1:]],
            "ids": [n for m in members for n in used[m]],
            "context": [n for m in members for n in mentions[m]["context"]],
        }
        alias_of.update(dict.fromkeys(members, spelling))
    if left_out:
        notes.append(f"Left out as minor ({len(left_out)}): {', '.join(sorted(left_out))}")
    return Cast(subjects, alias_of, notes)
