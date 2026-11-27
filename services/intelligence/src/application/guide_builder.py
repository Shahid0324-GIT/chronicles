"""From a classified request to a finished guide: read, translate, write, check."""

from src.application.guide import Encyclopedia, Guide, GuideSource, Kind
from src.application.guide_research import (
    Passage,
    Report,
    glossary,
    main_page,
    related_pages,
    select_arc,
    select_character,
    select_summary,
    translate,
)
from src.application.guide_writer import cast_entries, write_cast, write_sections
from src.application.knowledge_presentation import Infer


def title_for(kind: Kind, story: str, subject: str) -> str:
    return f"{story}: summary and cast" if kind == "summary" else f"{subject} · {story}"


async def build_guide(
    kind: Kind,
    story: str,
    subject: str,
    wikipedia_title: str,
    link: str,
    encyclopedia: Encyclopedia,
    infer: Infer,
    translator: Infer,
    say: Report,
) -> Guide:
    say("Finding the Wikipedia pages")
    main = await main_page(encyclopedia, story, wikipedia_title, link)
    pages = await related_pages(encyclopedia, main, kind, story, subject, infer, say)

    say("Choosing the passages")
    passages: list[Passage]
    if kind == "character":
        passages = await select_character(pages, story, subject, infer, say)
    elif kind == "arc":
        passages = await select_arc(pages, story, subject, infer, say)
    else:
        passages = select_summary(pages, say)
    names = glossary(pages)
    sources, notes = await translate(passages, names, translator, say)

    about = {
        "summary": f"the story '{story}'",
        "arc": f"the arc '{subject}' of '{story}'",
        "character": f"the character {subject} from '{story}'",
    }[kind]
    say("Writing the page")
    sections, more = await write_sections(about, kind, sources, infer, say)
    notes += more

    cast = []
    if kind == "summary":
        everyone = [Passage(a, b) for a in pages for b in a.blocks]
        listed, cast_notes = await translate(cast_entries(everyone), names, translator, say)
        offset = len(sources)
        entries: list[GuideSource] = [
            s.model_copy(update={"number": s.number + offset}) for s in listed
        ]
        say("  choosing the cast")
        cast = await write_cast(story, entries, infer)
        sources += entries
        notes += cast_notes

    if not any(s.paragraphs for s in sections) and not cast:
        raise ValueError("Nothing could be written from the pages that were read")
    cited = {n for s in sections for p in s.paragraphs for n in p.cites}
    cited |= {n for member in cast for n in member.cites}
    return Guide(
        kind=kind,
        story=story,
        subject=subject,
        title=title_for(kind, story, subject),
        sections=sections,
        cast=cast,
        sources=[s for s in sources if s.number in cited],
        notes=list(dict.fromkeys(n[:400] for n in notes))[:200],
    )
