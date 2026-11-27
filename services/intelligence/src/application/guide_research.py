"""Find the Wikipedia passages a guide needs and put them into English.

A model only chooses among numbered titles and labels taken from the pages themselves.
"""

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pydantic import Field

from src.application.guide import LANGUAGES, Article, Block, Encyclopedia, GuideSource, Kind
from src.application.knowledge_presentation import Infer
from src.application.research import SourceRejected
from src.application.research_contracts import StructuredModel

Report = Callable[[str], None]
# Source characters read per language, which bounds the free model calls a guide costs.
BUDGET = {"en": 24_000, "ja": 7_000, "zh": 9_000}
BATCH = 2_200
PAGES = 4
CANDIDATES = 90
LABELS = 600
PLOT = ("premise", "plot", "synopsis", "story", "あらすじ", "ストーリー", "物語", "故事", "劇情")
PLOT_MORE = ("剧情", "情节", "情節", "内容", "內容", "overview", "summary")
CAST = ("character", "登場人物", "キャラクター", "角色", "人物")


class Picks(StructuredModel):
    numbers: list[int] = Field(default_factory=list, max_length=200)


class Translation(StructuredModel):
    number: int
    english: str = Field(max_length=8000)


class Translations(StructuredModel):
    items: list[Translation] = Field(default_factory=list, max_length=60)


@dataclass(frozen=True)
class Passage:
    article: Article
    block: Block


def plain(value: str) -> str:
    return "".join(c for c in value.casefold() if c.isalnum())


def _under(block: Block, words: Sequence[str]) -> bool:
    return any(word in part.casefold() for part in block.path for word in words)


def _short_title(title: str) -> str:
    """A title without its subtitle or bracketed note, as related pages repeat it."""
    return re.split(r"\s+[(\-−–—]", title)[0].strip()


async def main_page(encyclopedia: Encyclopedia, story: str, title: str, link: str) -> Article:
    """The story's own page, refused unless it names the story."""
    if link:
        article = await encyclopedia.read(link)
        if article.language != "en" and "en" in article.languages:
            article = await encyclopedia.read(article.languages["en"])
        return article
    for name in dict.fromkeys(n.strip() for n in (title, story) if n.strip()):
        try:
            article = await encyclopedia.read(encyclopedia.address("en", name))
        except SourceRejected:
            continue
        opening = plain(article.title + " ".join(b.text for b in article.blocks[:3]))
        words = [plain(w) for w in re.split(r"\W+", story) if len(plain(w)) > 2]
        if plain(story) in opening or (words and all(w in opening for w in words)):
            return article
    raise ValueError(f"No Wikipedia page was found for '{story}'; paste its link instead")


async def _choose(question: str, options: list[str], infer: Infer, limit: int) -> list[int]:
    """Positions of the options a model picked, ignoring numbers that were not offered."""
    if not options:
        return []
    picks = Picks.model_validate(
        await infer(
            question
            + '\nReturn only JSON: {"numbers":[1]}. Use only the numbers listed; return an '
            "empty list when none fit.\n"
            + json.dumps({str(n): o for n, o in enumerate(options, 1)}, ensure_ascii=False),
            Picks,
            "presentation",
        )
    )
    chosen = [n - 1 for n in dict.fromkeys(picks.numbers) if 0 < n <= len(options)]
    return chosen[:limit]


async def related_pages(
    encyclopedia: Encyclopedia,
    main: Article,
    kind: Kind,
    story: str,
    subject: str,
    infer: Infer,
    say: Report,
) -> list[Article]:
    """The main page, the pages it links that fit the request, and other languages."""
    short = plain(_short_title(main.title))
    wanted = [plain(w) for w in subject.split() if len(plain(w)) > 2]
    candidates = [
        (title, text)
        for title, text in main.links
        if title != main.title
        and (short in plain(title) or any(w in plain(title + text) for w in wanted))
    ][:CANDIDATES]
    purpose = {
        "summary": "its list of characters and the pages that summarise its plot",
        "character": f"the character {subject}: their own page and the list of characters",
        "arc": f"the arc '{subject}': season, episode-list or plot pages that cover it",
    }[kind]
    chosen = await _choose(
        f"Pick up to {PAGES} Wikipedia pages about the story '{story}' needed for {purpose}. "
        "Leave out games, music, merchandise and pages about other stories.",
        [title for title, _text in candidates],
        infer,
        PAGES,
    )
    found = [main]

    async def add(url: str) -> Article | None:
        try:
            article = await encyclopedia.read(url)
        except SourceRejected as error:
            say(f"  could not read a page: {error}")
            return None
        if article.url not in {a.url for a in found}:
            found.append(article)
            say(f"  read {LANGUAGES[article.language]} page: {article.title}")
        return article

    say(f"  read English page: {main.title}")
    for index in chosen:
        await add(encyclopedia.address(main.language, candidates[index][0]))
    # A list page may link the language that the main page does not, and the reverse.
    languages: dict[str, str] = {}
    for article in found:
        for code, url in article.languages.items():
            if code != "en" and _short_title(article.title) == _short_title(main.title):
                languages.setdefault(code, url)
    for url in languages.values():
        other = await add(url)
        if other is None or kind == "arc":
            continue
        base = plain(_short_title(other.title))
        lists = [
            title
            for title, _text in other.links
            if plain(title).startswith(base) and any(word in title.casefold() for word in CAST)
        ]
        if lists:
            await add(encyclopedia.address(other.language, lists[0]))
    return found


def _within_budget(passages: list[Passage], say: Report) -> list[Passage]:
    used: dict[str, int] = {}
    kept: list[Passage] = []
    for passage in passages:
        language = passage.article.language
        size = len(passage.block.text)
        if used.get(language, 0) + size <= BUDGET[language]:
            used[language] = used.get(language, 0) + size
            kept.append(passage)
    if len(kept) < len(passages):
        say(f"  left out {len(passages) - len(kept)} passages to stay within free limits")
    return kept


async def select_character(
    pages: list[Article], story: str, subject: str, infer: Infer, say: Report
) -> list[Passage]:
    wanted = [plain(w) for w in subject.split() if len(plain(w)) > 2] or [plain(subject)]
    own = [a for a in pages if any(w in plain(a.title) for w in wanted)]
    labels: dict[tuple[int, str], str] = {}
    for number, article in enumerate(pages):
        for block in article.blocks:
            if block.path:
                above = block.path[-2] if len(block.path) > 1 else ""
                labels.setdefault(
                    (number, block.path[-1]),
                    f"{block.path[-1][:80]} | under {above[:30]} | {article.language}",
                )
    keys = list(labels)[:LABELS]
    chosen = await _choose(
        f"These are headings and entry names from Wikipedia pages about '{story}'. Pick "
        f"every one that is the entry of the character '{subject}', in any language. Do not "
        "pick other characters, even relatives or namesakes.",
        [labels[k] for k in keys],
        infer,
        12,
    )
    names = {keys[i] for i in chosen}
    entries = [
        Passage(article, block)
        for number, article in enumerate(pages)
        for block in article.blocks
        if any((number, part) in names for part in block.path)
    ]
    # Their own page follows the concentrated list entries, so both fit the budget.
    taken = {(p.article.url, p.block) for p in entries}
    entries += [Passage(a, b) for a in own for b in a.blocks if (a.url, b) not in taken]
    if not entries:
        raise ValueError(f"Wikipedia has no entry for '{subject}' on the pages that were read")
    return _within_budget(entries, say)


def select_summary(pages: list[Article], say: Report) -> list[Passage]:
    main = {a.url for a in pages if _short_title(a.title) == a.title}
    found = [
        Passage(article, block)
        for article in pages
        for block in article.blocks
        if _under(block, PLOT + PLOT_MORE) or (not block.path and article.url in main)
    ]
    if not found:
        raise ValueError("The pages that were read hold no story summary")
    return _within_budget(found, say)


async def select_arc(
    pages: list[Article], story: str, subject: str, infer: Infer, say: Report
) -> list[Passage]:
    told = [
        Passage(article, block)
        for article in pages
        for block in article.blocks
        if _under(block, PLOT + PLOT_MORE) or any("Episode" in part for part in block.path)
    ]
    # One option per heading, so a long section is chosen as a whole.
    groups: dict[tuple[str, tuple[str, ...]], list[Passage]] = {}
    for passage in told:
        groups.setdefault((passage.article.url, passage.block.path), []).append(passage)
    keys = list(groups)[:250]
    options = [
        f"{groups[k][0].article.title[:50]} | {' / '.join(k[1])[:90]} | "
        f"{groups[k][0].block.text[:160]}"
        for k in keys
    ]
    chosen = await _choose(
        f"These are plot passages and episode summaries about '{story}'. Pick every one "
        f"that tells part of the arc the reader calls '{subject}', in story order, and "
        "none from other arcs.",
        options,
        infer,
        200,
    )
    found = [passage for i in sorted(chosen) for passage in groups[keys[i]]]
    if not found:
        raise ValueError(f"No passages about '{subject}' were found on the pages that were read")
    return _within_budget(found, say)


def glossary(pages: list[Article]) -> list[str]:
    """English entry names, so translations spell names the way the English pages do."""
    names: dict[str, None] = {}
    for article in pages:
        if article.language == "en":
            for block in article.blocks:
                if len(block.path) > 1 and "Episode" not in block.path[-1]:
                    name = re.split(r"\s*[(（]", block.path[-1])[0].strip()
                    if 1 < len(name) <= 40:
                        names.setdefault(name)
    return list(names)[:90]


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+", text))


async def translate(
    passages: list[Passage], names: list[str], translator: Infer, say: Report
) -> tuple[list[GuideSource], list[str]]:
    """Numbered English sources in the order given, with anything doubtful noted."""
    english: dict[int, str] = {}
    notes: list[str] = []
    for language in ("ja", "zh"):
        waiting = [(i, p) for i, p in enumerate(passages) if p.article.language == language]
        batches: list[list[tuple[int, Passage]]] = []
        size = BATCH
        for index, passage in waiting:
            length = len(passage.block.text)
            if size + length > BATCH:
                batches.append([])
                size = 0
            batches[-1].append((index, passage))
            size += length
        for count, batch in enumerate(batches, 1):
            say(f"  translating {LANGUAGES[language]} {count} of {len(batches)}")
            reply = Translations.model_validate(
                await translator(
                    f"Translate each numbered {LANGUAGES[language]} passage into plain "
                    "English. The heading shows what it is about; translate the passage only. "
                    "Spell names as in this list when they match: "
                    + json.dumps(names, ensure_ascii=False)
                    + '\nReturn only JSON: {"items":[{"number":1,"english":""}]}\n'
                    + json.dumps(
                        {
                            str(n): {
                                "heading": " / ".join(p.block.path)[:200],
                                "passage": p.block.text,
                            }
                            for n, (_i, p) in enumerate(batch, 1)
                        },
                        ensure_ascii=False,
                    ),
                    Translations,
                    "presentation",
                )
            )
            done = {item.number: item.english.strip() for item in reply.items}
            for n, (index, passage) in enumerate(batch, 1):
                text = done.get(n, "")
                original = passage.block.text
                # English runs longer than Japanese or Chinese, so a short reply is a cut one.
                if len(text) < len(original) * 0.8:
                    notes.append(
                        f"Dropped a {LANGUAGES[language]} passage that was not fully "
                        f"translated: {original[:60]}"
                    )
                    continue
                english[index] = text
                if lost := _numbers(original) - _numbers(text):
                    notes.append(f"Check numbers {sorted(lost)} in: {text[:90]}")
    sources: list[GuideSource] = []
    for index, passage in enumerate(passages):
        article = passage.article
        translated = article.language != "en"
        if translated and index not in english:
            continue
        sources.append(
            GuideSource(
                number=len(sources) + 1,
                title=article.title[:300],
                url=article.url,
                language=article.language,
                heading=" / ".join(passage.block.path)[:300],
                text=english[index] if translated else passage.block.text,
                original=passage.block.text if translated else "",
                licence=article.licence[:300],
                revision=article.revision[:60],
            )
        )
    return sources, notes
