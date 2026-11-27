"""The steps that turn a library arc into a draft world, reporting as they go."""

import asyncio
import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import BaseModel

from src.application.knowledge_presentation import Infer
from src.application.research import SourceRejected
from src.application.research_contracts import InferenceFailure, Task
from src.application.scout import PagePlan, WikiSite, discover, read_page
from src.application.story_library import LibraryWorld, library_passages
from src.application.story_order import order_sources
from src.application.story_pack import DRAFT_SUFFIX, StoryPack
from src.application.story_pack_builder import (
    PACK_RULES,
    PackDraft,
    build_story_pack,
    render_review,
)
from src.application.story_pack_edits import PackEdits, apply_edits
from src.application.story_pack_merge import merge_packs
from src.import_story_pack import publish
from src.infrastructure.config.settings import Settings
from src.infrastructure.inference import create_inference
from src.infrastructure.mediawiki import MediaWikiPages, MediaWikiSite
from src.infrastructure.sources import PublicDocumentFetcher, PublicSourcePolicy
from src.infrastructure.story_library_files import StoryLibraryFiles

Report = Callable[[str], None]
MAX_ATTEMPTS = 60
MAX_INVALID = 4
MAX_PAGE_BYTES = 3_000_000
MIN_SOURCES = 3


def model_calls(cache: Path, cloud_allowed: bool, say: Report) -> Infer:
    """Model calls that reuse saved replies and wait out free-tier limits."""
    router = create_inference(Settings())
    cache.mkdir(parents=True, exist_ok=True)

    async def infer(prompt: str, schema: type[BaseModel], task: Task) -> BaseModel:
        key = hashlib.sha256(
            json.dumps([task, schema.__name__, prompt], ensure_ascii=False).encode()
        ).hexdigest()
        saved = cache / f"{key}.json"
        if saved.exists():
            return schema.model_validate_json(saved.read_text(encoding="utf-8"))
        invalid = 0
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                result = await router.generate(
                    PACK_RULES,
                    prompt,
                    schema,
                    task,
                    public_source_content=cloud_allowed,
                    limit_calls=False,
                    # Local-only sources use the local model; otherwise wait for a cloud one.
                    allow_local_fallback=not cloud_allowed,
                )
                break
            except InferenceFailure as error:
                invalid += error.code == "structured_output_exhausted"
                for use in router.usage[-4:]:
                    if use.validation_errors:
                        say(f"  invalid reply from {use.provider}: {use.validation_errors}")
                permanent = error.code in {"cloud_not_permitted", "request_too_large"}
                if permanent or invalid >= MAX_INVALID or attempt == MAX_ATTEMPTS:
                    raise
                wait = min(600.0, max(30.0, error.retry_after))
                say(f"  waiting {wait:.0f}s ({error.code}, attempt {attempt})")
                await asyncio.sleep(wait)
        saved.write_text(result.value.model_dump_json(), encoding="utf-8")
        say(f"  {schema.__name__} from {result.usage.provider}")
        return result.value

    return infer


def _sites(world: LibraryWorld) -> dict[str, WikiSite]:
    if not world.sites:
        raise ValueError('Approve a site first: add it to "sites" in world.json')
    hosts = [urlsplit(site.address).hostname or "" for site in world.sites]
    fetcher = PublicDocumentFetcher(PublicSourcePolicy(hosts), MAX_PAGE_BYTES, MAX_PAGE_BYTES)
    return {
        site.address: (MediaWikiSite if site.api else MediaWikiPages)(site, fetcher)
        for site in world.sites
    }


async def find_pages(
    files: StoryLibraryFiles,
    world_slug: str,
    arc_key: str,
    about: str,
    start: list[str],
    say: Report,
) -> PagePlan:
    """The pages that tell the arc, chosen once and kept in pages.json."""
    world = files.world(world_slug)
    arc = files.arc(world, arc_key)
    if not world.sites:
        raise ValueError('Approve a site first: add it to "sites" in world.json')
    sites = _sites(world)
    folder = files.folder(world.slug) / arc.key
    saved = folder / "sources"
    saved.mkdir(parents=True, exist_ok=True)
    listed = folder / "pages.json"
    if listed.exists():
        plan = PagePlan.model_validate_json(listed.read_text(encoding="utf-8-sig"))
        say(f"Using your page list: {listed}")
    else:
        pages = []
        for site in sites.values():
            say(f"Searching {urlsplit(site.config.address).hostname}")
            cache = files.folder(world.slug) / "cache"
            infer = model_calls(cache, site.config.cloud_allowed, say)
            pages += await discover(
                world.title, arc.title, about, world.position_word, site, infer, say, start
            )
        plan = PagePlan(pages=pages[:80], focus=start[0] if start else "")
        if not plan.pages:
            raise ValueError("No pages were chosen; describe the arc with --about")
        listed.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        say(f"Chose {len(plan.pages)} pages (edit {listed} to change them)")
    return plan


async def fetch_pages(files: StoryLibraryFiles, world_slug: str, arc_key: str, say: Report) -> None:
    """Save each listed page that is not saved yet."""
    world = files.world(world_slug)
    arc = files.arc(world, arc_key)
    sites = _sites(world)
    folder = files.folder(world.slug) / arc.key
    saved = folder / "sources"
    saved.mkdir(parents=True, exist_ok=True)
    listed = folder / "pages.json"
    plan = PagePlan.model_validate_json(listed.read_text(encoding="utf-8-sig"))
    kept = 0
    for planned in plan.pages:
        chosen = sites.get(planned.site)
        if chosen is None:
            say(f"  skipped {planned.title}: its site is not approved in world.json")
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", planned.title.casefold()).strip("-")[:60] or "page"
        digest = hashlib.sha256(f"{planned.site}|{planned.title}".encode()).hexdigest()[:8]
        path = saved / f"{planned.position:05d}-{slug}-{digest}.json"
        if path.exists():
            kept += 1
            continue
        try:
            source, note = await read_page(planned, chosen, arc.sections, plan.focus)
        except SourceRejected as error:
            say(f"  could not read {planned.title}: {error}")
            continue
        if note:
            say(f"  {note}")
        if source:
            path.write_text(source.model_dump_json(indent=2), encoding="utf-8")
            kept += 1
            words = len(source.text.split())
            say(f"  {world.position_word} {source.position}: {source.title}, {words} words")
    if kept < MIN_SOURCES:
        raise ValueError(f"Only {kept} usable pages; too few to tell the arc")
    say(f"Saved {kept} sources in {saved}")


async def build_arc(
    files: StoryLibraryFiles,
    world_slug: str,
    arc_key: str,
    subjects: list[str],
    pages: int,
    say: Report,
) -> None:
    world = files.world(world_slug)
    arc = files.arc(world, arc_key)
    saved = files.sources(world, arc.key)
    passages = library_passages(world, saved)
    if not passages.sentences:
        raise ValueError("Add source files for this arc first")
    cache = files.folder(world.slug) / "cache"
    infer = model_calls(cache, passages.cloud_eligible, say)
    moved: list[str] = []
    if arc.reorder:
        say("putting the story in order")
        ordering = await order_sources(arc.title, saved, infer)
        passages = library_passages(world, ordering.sources, ordered=True)
        moved = ordering.notes

    draft = await build_story_pack(
        slug=world.slug + DRAFT_SUFFIX,
        world_title=f"{world.title} (draft)",
        arc_key=arc.key,
        arc_title=arc.title,
        medium=world.medium,
        passages=passages,
        story_bible=None,
        position_word=world.position_word,
        deep_pages=pages,
        infer=infer,
        subjects=subjects,
        progress=say,
    )
    draft = PackDraft(draft.pack, [*moved, *draft.notes])
    licences = {s.url: s.licence for s in saved}
    for listed in draft.pack.sources:
        listed.licence = licences.get(listed.url, "")
    folder = files.folder(world.slug) / arc.key
    corrections = folder / "edits.json"
    if corrections.exists():
        edits = PackEdits.model_validate_json(corrections.read_text(encoding="utf-8-sig"))
        pack, skipped = apply_edits(draft.pack, edits)
        draft = PackDraft(pack, [*skipped, *draft.notes])
        say("Applied your saved corrections")
    (folder / "pack.json").write_text(draft.pack.model_dump_json(indent=2), encoding="utf-8")
    (folder / "review.md").write_text(render_review(draft), encoding="utf-8")
    say(f"Draft ready: {folder / 'review.md'} ({len(draft.notes)} items to check)")


async def load_world(files: StoryLibraryFiles, world_slug: str, say: Report) -> None:
    world = files.world(world_slug)
    packs = [
        StoryPack.model_validate_json(path.read_text(encoding="utf-8-sig"))
        for path in files.packs(world)
    ]
    merged = merge_packs(packs)
    counts = await publish(merged)
    say(
        f"Loaded {merged.slug}: {len(merged.arcs)} arcs, {counts['nodes']} entries, "
        f"{counts['relationships']} connections (draft)."
    )
