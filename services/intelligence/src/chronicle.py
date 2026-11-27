"""Build and load story atlases from the file library.

python -m src.chronicle check <world> <arc>   what would be read (no model calls)
python -m src.chronicle build <world> <arc>   draft the arc's pack for review (resumable)
python -m src.chronicle load <world>          merge every drafted arc into the draft world
"""

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

from pydantic import BaseModel

from src.application.research_contracts import InferenceFailure, Task
from src.application.story_library import library_passages
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
from src.infrastructure.story_library_files import StoryLibraryFiles

MAX_ATTEMPTS = 60
MAX_INVALID = 4


def say(message: str) -> None:
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


async def build(
    files: StoryLibraryFiles, world_slug: str, arc_key: str, subjects: list[str]
) -> None:
    world = files.world(world_slug)
    arc = files.arc(world, arc_key)
    passages = library_passages(world, files.sources(world, arc.key))
    if not passages.sentences:
        raise ValueError("Add source files for this arc first")
    router = create_inference(Settings())
    cache = files.folder(world.slug) / "cache"
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
                    public_source_content=passages.cloud_eligible,
                    limit_calls=False,
                    # Local-only sources use the local model; otherwise wait for a cloud one.
                    allow_local_fallback=not passages.cloud_eligible,
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

    draft = await build_story_pack(
        slug=world.slug + DRAFT_SUFFIX,
        world_title=f"{world.title} (draft)",
        arc_key=arc.key,
        arc_title=arc.title,
        medium=world.medium,
        passages=passages,
        story_bible=None,
        infer=infer,
        subjects=subjects,
        progress=say,
    )
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


async def load(files: StoryLibraryFiles, world_slug: str) -> None:
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


def main() -> None:
    root = Path(__file__).resolve().parents[3] / "library"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "build", "load"])
    parser.add_argument("world")
    parser.add_argument("arc", nargs="?")
    parser.add_argument("--library", type=Path, default=root)
    parser.add_argument("--subject", action="append", default=[], help="deep page; repeatable")
    arguments = parser.parse_args()
    files = StoryLibraryFiles(arguments.library)
    try:
        if arguments.command == "load":
            asyncio.run(load(files, arguments.world))
            return
        if not arguments.arc:
            parser.error("name the arc")
        if arguments.command == "build":
            asyncio.run(build(files, arguments.world, arguments.arc, arguments.subject))
            return
        world = files.world(arguments.world)
        passages = library_passages(world, files.sources(world, arguments.arc))
        for source in passages.sources:
            say(f"  {world.position_word} {source.position}: {source.label}")
        say(
            f"{len(passages.sources)} sources, {len(passages.sentences)} sentences, "
            f"{'cloud allowed' if passages.cloud_eligible else 'local model only'}"
        )
    except ValueError as error:
        sys.exit(str(error))


if __name__ == "__main__":
    main()
