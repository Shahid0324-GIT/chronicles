"""Put saved paragraphs into story order before they are read.

Pages organised by place or person tell return visits, aftermaths and flashbacks beside
the first events. A model reads a few pages at a time against an outline of all of them
and says which paragraphs happen during another page. A paragraph moves only when the
words quoted from it are really there; everything else keeps page order.
"""

import json
from dataclasses import dataclass

from pydantic import Field

from src.application.knowledge_presentation import Infer
from src.application.research_contracts import StructuredModel
from src.application.story_library import LibrarySource, page_order

# Paragraph text sent per request, and the characters of each page shown in the outline.
REQUEST_CHARS = 7000
OUTLINE_CHARS = 220


class Placement(StructuredModel):
    paragraph: int
    during: int
    clue: str = ""


class Placements(StructuredModel):
    moved: list[Placement] = Field(default_factory=list, max_length=60)


@dataclass(frozen=True)
class _Paragraph:
    page: int
    text: str


@dataclass
class Ordered:
    """Pieces of the saved pages in story order, and what was moved."""

    sources: list[LibrarySource]
    notes: list[str]


def _plain(value: str) -> str:
    return " ".join(value.casefold().split())


def _requests(pages: list[list[int]], paragraphs: dict[int, _Paragraph]) -> list[list[int]]:
    """Pages that could hold a misplaced paragraph, grouped to fit one request each."""
    groups: list[list[int]] = []
    used = 0
    for index, numbers in enumerate(pages):
        # A page of one paragraph has nothing set apart from its own visit.
        if len(numbers) < 2:
            continue
        size = sum(len(paragraphs[n].text) for n in numbers)
        if groups and used + size <= REQUEST_CHARS:
            groups[-1].append(index)
            used += size
        else:
            groups.append([index])
            used = size
    return groups


async def order_sources(title: str, sources: list[LibrarySource], infer: Infer) -> Ordered:
    saved = sorted(sources, key=page_order)
    paragraphs: dict[int, _Paragraph] = {}
    pages: list[list[int]] = []
    for index, page in enumerate(saved):
        pages.append([])
        for text in page.text.split("\n"):
            if text.strip():
                number = len(paragraphs) + 1
                paragraphs[number] = _Paragraph(index, text.strip())
                pages[index].append(number)
    if len(saved) < 2:
        return Ordered(saved, [])
    outline = [
        {"page": i + 1, "title": saved[i].title, "opens": paragraphs[n[0]].text[:OUTLINE_CHARS]}
        for i, n in enumerate(pages)
        if n
    ]
    moves: dict[int, tuple[int, str]] = {}
    skipped = 0
    for group in _requests(pages, paragraphs):
        shown = [n for index in group for n in pages[index]]
        reply = Placements.model_validate(
            await infer(
                "These wiki pages retell one story arc. The outline lists them in the order "
                "the story first reaches each. A page often goes on to tell later return "
                "visits, aftermaths or an ending, or earlier events, after its first visit. "
                "Go through every paragraph below and list each one that does NOT happen "
                "during its page's first visit: give its number, in during the outline page "
                "number whose events it happens during or directly after, and in clue the "
                "exact words from that paragraph showing when (such as 'after saving the "
                "princess' or 'returns for a third visit'). A paragraph that simply continues "
                "the one moved before it gets the same during and an empty clue. Do not list "
                "paragraphs that belong where they are.\n"
                'Return only JSON: {"moved":[{"paragraph":3,"during":9,"clue":""}]}\n'
                + json.dumps(
                    {
                        "arc": title,
                        "outline": outline,
                        "paragraphs": [
                            {
                                "number": n,
                                "page": paragraphs[n].page + 1,
                                "text": paragraphs[n].text,
                            }
                            for n in shown
                        ],
                    },
                    ensure_ascii=False,
                ),
                Placements,
                "presentation",
            )
        )
        for item in sorted(reply.moved, key=lambda m: m.paragraph):
            n, target = item.paragraph, item.during - 1
            if n not in shown or target == paragraphs[n].page:
                skipped += n not in shown
                continue
            clue = _plain(item.clue)
            quoted = len(clue) >= 8 and clue in _plain(paragraphs[n].text)
            previous = moves.get(n - 1)
            continues = (
                not clue
                and previous is not None
                and previous[0] == target
                and paragraphs[n - 1].page == paragraphs[n].page
            )
            # The first paragraph of a page is its first visit, whatever is claimed.
            if (
                0 <= target < len(pages)
                and pages[target]
                and n != pages[paragraphs[n].page][0]
                and (quoted or continues)
            ):
                moves[n] = (target, " ".join(item.clue.split()))
            else:
                skipped += 1
    following: dict[int, list[int]] = {}
    for n, (target, _) in moves.items():
        stay = [p for p in pages[target] if p not in moves]
        # The first paragraph never moves, so every page keeps a place to follow.
        following.setdefault(stay[-1], []).append(n)
    placed: list[tuple[int, int]] = []
    for number, paragraph in paragraphs.items():
        if number in moves:
            continue
        here = saved[paragraph.page].position
        placed.append((number, here))
        # Moved later, it belongs to that later part; moved earlier, it stays hidden
        # until the page that told it.
        placed += [
            (n, max(here, saved[paragraphs[n].page].position))
            for n in sorted(following.get(number, []))
        ]
    pieces: list[LibrarySource] = []
    previous_piece: tuple[int, int] | None = None
    for number, position in placed:
        index = paragraphs[number].page
        if previous_piece == (index, position):
            joined = f"{pieces[-1].text}\n{paragraphs[number].text}"
            pieces[-1] = pieces[-1].model_copy(update={"text": joined})
        else:
            pieces.append(
                saved[index].model_copy(
                    update={"text": paragraphs[number].text, "position": position}
                )
            )
        previous_piece = (index, position)
    notes = [
        f"Moved a paragraph of {saved[paragraphs[n].page].title} to {saved[target].title}: "
        f"'{paragraphs[n].text[:70]}...'" + (f" because it says '{clue}'" if clue else "")
        for n, (target, clue) in sorted(moves.items())
    ]
    if skipped:
        notes.append(f"{skipped} proposed moves were not supported by the text and were ignored")
    return Ordered(pieces, notes)
