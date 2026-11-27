"""Write a guide's sections from numbered English sources, then check each one.

Passages are first sorted into sections, so each section is written from its own
material. A second model call points at sentences their sources do not support, and
those are removed and noted. It can be wrong in both directions.
"""

import json
import re
from typing import Literal

from pydantic import Field

from src.application.guide import CastMember, GuideParagraph, GuideSection, GuideSource, Kind
from src.application.guide_research import CAST, Passage, Report, plain
from src.application.knowledge_presentation import Infer
from src.application.research_contracts import StructuredModel

SORT_BATCH = 40
# Source characters given to one writing call, small enough for the free allowances.
WINDOW = 6_000
MAIN_CAST = 8
SUPPORTING_CAST = 16
CAST_ENTRIES = 45

# (key, heading, what belongs in it)
OUTLINES: dict[Kind, tuple[tuple[str, str, str], ...]] = {
    "summary": (
        ("premise", "Premise", "the setting and how the story starts"),
        ("story", "The story so far", "what happens, in order"),
    ),
    "arc": (
        ("setup", "How it begins", "the situation and what starts this arc"),
        ("events", "What happens", "the arc's events, in order"),
        ("outcome", "How it ends", "how the arc is resolved and what it changes"),
    ),
    "character": (
        ("overview", "Overview", "who they are and their part in the story, briefly"),
        ("background", "Background", "origin, family and past"),
        ("personality", "Personality", "temperament, beliefs and appearance"),
        ("abilities", "Abilities and powers", "powers, skills, weapons and their limits"),
        ("arcs", "Role in the story, arc by arc", "what they do, naming the arc when given"),
        (
            "relationships",
            "Relationships",
            "their bonds and conflicts with other characters, one character at a time",
        ),
        ("status", "Latest known status", "their situation at the latest point described"),
    ),
}


class Sorted(StructuredModel):
    key: str
    numbers: list[int] = Field(default_factory=list, max_length=100)


class Sorting(StructuredModel):
    sections: list[Sorted] = Field(default_factory=list, max_length=12)


class DraftParagraph(StructuredModel):
    text: str = Field(max_length=3000)
    sources: list[int] = Field(default_factory=list, max_length=60)


class SectionDraft(StructuredModel):
    paragraphs: list[DraftParagraph] = Field(default_factory=list, max_length=12)


class Doubts(StructuredModel):
    sentences: list[int] = Field(default_factory=list, max_length=80)


class DraftMember(StructuredModel):
    number: int
    name: str = Field(max_length=100)
    role: str = Field(max_length=20)
    description: str = Field(max_length=600)


class CastDraft(StructuredModel):
    members: list[DraftMember] = Field(default_factory=list, max_length=60)


def sentences(text: str) -> list[str]:
    parts: list[str] = []
    # A sentence ends at its punctuation, or at a quote closing just after it.
    ending = r"(?:(?<=[.!?])|(?<=[.!?][\"\u201d])) +(?=[A-Z\"\u201c])"
    for part in re.split(ending, text.strip()):
        # An initial or a title before a name does not end a sentence.
        if parts and re.search(r"\b(?:[A-Z]|Mr|Mrs|Ms|Dr|St|Sir|Lt|Capt)\.$", parts[-1]):
            parts[-1] += " " + part
        elif part:
            parts.append(part)
    return parts


def _listing(sources: list[GuideSource], limit: int = 8000) -> dict[str, str]:
    return {str(s.number): f"[{s.heading[:100]}] {s.text[:limit]}" for s in sources}


async def sort_sources(
    about: str, kind: Kind, sources: list[GuideSource], infer: Infer
) -> dict[str, list[GuideSource]]:
    outline = OUTLINES[kind]
    keys = {key for key, _heading, _covers in outline}
    placed: dict[str, dict[int, GuideSource]] = {key: {} for key in keys}
    for start in range(0, len(sources), SORT_BATCH):
        batch = sources[start : start + SORT_BATCH]
        known = {s.number: s for s in batch}
        reply = Sorting.model_validate(
            await infer(
                f"Sort these numbered passages into the sections of a page about {about}. "
                "Put a passage in every section it has material for, or in none. Sections: "
                + "; ".join(f'"{key}" = {covers}' for key, _heading, covers in outline)
                + '.\nReturn only JSON: {"sections":[{"key":"","numbers":[1]}]}\n'
                + json.dumps(_listing(batch, 500), ensure_ascii=False),
                Sorting,
                "presentation",
            )
        )
        for group in reply.sections:
            if group.key in keys:
                for number in group.numbers:
                    if number in known:
                        placed[group.key][number] = known[number]
    return {key: [found[n] for n in sorted(found)] for key, found in placed.items()}


def _windows(sources: list[GuideSource]) -> list[list[GuideSource]]:
    windows: list[list[GuideSource]] = []
    size = WINDOW
    for source in sources:
        if size + len(source.text) > WINDOW:
            windows.append([])
            size = 0
        windows[-1].append(source)
        size += len(source.text)
    return windows


async def _supported(
    paragraphs: list[GuideParagraph],
    sources: dict[int, GuideSource],
    infer: Infer,
) -> tuple[list[GuideParagraph], list[str]]:
    """The paragraphs and the sentences removed from them, found unsupported by a check."""
    numbered: dict[int, tuple[int, str]] = {}
    for index, paragraph in enumerate(paragraphs):
        for sentence in sentences(paragraph.text):
            numbered[len(numbered) + 1] = (index, sentence)
    if not numbered:
        return [], []
    cited = sorted({n for p in paragraphs for n in p.cites})
    doubts = Doubts.model_validate(
        await infer(
            "Check a draft against its sources. List the number of every sentence that "
            "states something the sources do not say or clearly show, or that gets who did "
            "what wrong. Rewording is fine. Return an empty list when all are supported.\n"
            'Return only JSON: {"sentences":[]}\n'
            + json.dumps(
                {
                    "sentences": {str(n): s for n, (_i, s) in numbered.items()},
                    "sources": _listing([sources[n] for n in cited]),
                },
                ensure_ascii=False,
            ),
            Doubts,
            "verification",
        )
    )
    doubted = set(doubts.sentences) & set(numbered)
    kept: list[GuideParagraph] = []
    for index, paragraph in enumerate(paragraphs):
        mine = [(n, s) for n, (i, s) in numbered.items() if i == index]
        text = " ".join(s for n, s in mine if n not in doubted)
        if text:
            kept.append(GuideParagraph(text=text[:3000], cites=paragraph.cites))
    return kept, [s for n, (_i, s) in numbered.items() if n in doubted]


def _length(paragraphs: list[GuideParagraph]) -> int:
    return sum(len(p.text) for p in paragraphs)


async def write_sections(
    about: str,
    kind: Kind,
    sources: list[GuideSource],
    infer: Infer,
    say: Report,
) -> tuple[list[GuideSection], list[str]]:
    say("  sorting passages into sections")
    placed = await sort_sources(about, kind, sources, infer)
    known = {s.number: s for s in sources}
    notes: list[str] = []
    sections: list[GuideSection] = []
    for key, heading, covers in OUTLINES[kind]:
        written: list[GuideParagraph] = []
        windows = _windows(placed[key])
        for count, window in enumerate(windows, 1):
            say(f"  writing '{heading}' {count} of {len(windows)}")
            offered = {s.number for s in window}
            earlier = [p for s in sections for p in s.paragraphs] + written

            async def attempt(
                rejected: list[str],
                heading: str = heading,
                covers: str = covers,
                window: list[GuideSource] = window,
                offered: set[int] = offered,
                earlier: list[GuideParagraph] = earlier,
            ) -> tuple[list[GuideParagraph], list[str], list[str]]:
                request = {
                    "already_written": " ".join(p.text for p in earlier)[-2500:],
                    "sources": _listing(window),
                }
                if rejected:
                    request["rejected"] = " ".join(rejected)[:2000]
                draft = SectionDraft.model_validate(
                    await infer(
                        f"Write the '{heading}' section of a page about {about}. It covers "
                        f"{covers}, and nothing that belongs elsewhere on the page. Write "
                        "clear connected prose in English, in your own words, with as much "
                        "concrete detail as the sources give. Name each person the first "
                        "time. Every paragraph lists the source numbers it uses. Return no "
                        "paragraphs when the sources say nothing on this. Do not retell what "
                        "is already written elsewhere on the page."
                        + (
                            " The rejected sentences were not supported as worded: say only "
                            "the parts the sources do support."
                            if rejected
                            else ""
                        )
                        + '\nReturn only JSON: {"paragraphs":[{"text":"","sources":[1]}]}\n'
                        + json.dumps(request, ensure_ascii=False),
                        SectionDraft,
                        "presentation",
                    )
                )
                drafted, uncited = [], []
                for paragraph in draft.paragraphs:
                    cites = [n for n in dict.fromkeys(paragraph.sources) if n in offered][:20]
                    if cites and paragraph.text.strip():
                        drafted.append(GuideParagraph(text=paragraph.text.strip(), cites=cites))
                    elif paragraph.text.strip():
                        uncited.append(paragraph.text.strip())
                kept, removed = await _supported(drafted, known, infer)
                return kept, removed, uncited

            kept, removed, uncited = await attempt([])
            if removed:
                # One rewrite, used only if it keeps at least as much.
                again = await attempt(removed)
                if _length(again[0]) >= _length(kept):
                    kept, removed, uncited = again
            written += kept
            notes += [f"Removed as unsupported: {s}" for s in removed]
            notes += [f"Left out, no source given: {s[:120]}" for s in uncited]
        sections.append(GuideSection(heading=heading, paragraphs=written[:60]))
    return sections, notes


def cast_entries(pages_passages: list[Passage]) -> list[Passage]:
    """The first paragraph of each entry on the best list of characters, English first."""
    ordered = sorted(pages_passages, key=lambda p: p.article.language != "en")
    entries: dict[tuple[str, ...], Passage] = {}
    chosen = ""
    for passage in ordered:
        title = passage.article.title.casefold()
        if not any(word in title for word in CAST) or len(passage.block.path) < 2:
            continue
        chosen = chosen or passage.article.url
        if passage.article.url == chosen and len(passage.block.text) > 40:
            entries.setdefault(passage.block.path, passage)
    return list(entries.values())[:CAST_ENTRIES]


async def write_cast(story: str, sources: list[GuideSource], infer: Infer) -> list[CastMember]:
    if not sources:
        return []
    known = {s.number: s for s in sources}
    draft = CastDraft.model_validate(
        await infer(
            f"These are entries from a list of the characters of '{story}'. Pick up to "
            f'{MAIN_CAST} "main" and {SUPPORTING_CAST} "supporting" characters. For each, '
            "give the entry's number, the character's English name, and one or two "
            "sentences saying who they are, using only that entry.\n"
            'Return only JSON: {"members":[{"number":1,"name":"","role":"main",'
            '"description":""}]}\n' + json.dumps(_listing(sources, 600), ensure_ascii=False),
            CastDraft,
            "presentation",
        )
    )
    members: dict[str, CastMember] = {}
    for member in draft.members:
        source = known.get(member.number)
        name, text = member.name.strip(), member.description.strip()
        if source is None or not name or not text:
            continue
        # The name must be on the entry it is credited to.
        entry = plain(source.heading + source.text)
        if not any(plain(word) in entry for word in name.split() if len(plain(word)) > 1):
            continue
        role: Literal["main", "supporting"] = (
            "main" if member.role.casefold() == "main" else "supporting"
        )
        members.setdefault(
            plain(name),
            CastMember(name=name, role=role, text=text, cites=[member.number]),
        )
    ranked = sorted(members.values(), key=lambda m: m.role != "main")
    main = [m for m in ranked if m.role == "main"][:MAIN_CAST]
    others = [m for m in ranked if m.role != "main"][:SUPPORTING_CAST]
    return [*main, *others]
