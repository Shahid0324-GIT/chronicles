"""Draft a story pack from the local archive for review.

python -m src.build_story_pack --world <world> --arc <arc> --subject "<name>"

Model replies are cached, so an interrupted or rate-limited run resumes where it stopped.
The pack is written to a file; nothing reaches the atlas until you import it.
"""

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select

from src.application.arc_intelligence import ArcIntelligence
from src.application.research_contracts import InferenceFailure, Task
from src.application.story_bible import build_story_bible
from src.application.story_pack import DRAFT_SUFFIX
from src.application.story_pack_builder import (
    PACK_RULES,
    PackDraft,
    build_story_pack,
    render_review,
)
from src.application.story_pack_edits import PackEdits, apply_edits
from src.infrastructure.config.settings import Settings
from src.infrastructure.inference import create_inference
from src.infrastructure.model_runtime import LocalModelLease
from src.infrastructure.persistence.database import create_database
from src.infrastructure.persistence.models import ContinuityModel, UniverseModel
from src.infrastructure.research_runtime import build_atlas, build_retrieval

MAX_ATTEMPTS = 60
MAX_INVALID = 4


def say(message: str) -> None:
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


async def run(arguments: argparse.Namespace) -> None:
    settings = Settings()
    engine, factory = create_database(settings.database_url)
    try:
        async with factory() as session:
            universe = await session.scalar(
                select(UniverseModel).where(UniverseModel.slug == arguments.world)
            )
            if universe is None:
                raise SystemExit(f"Unknown world: {arguments.world}")
            continuities = list(
                await session.scalars(
                    select(ContinuityModel).where(ContinuityModel.universe_id == universe.id)
                )
            )
        retrieval = build_retrieval(settings, factory)
        atlas = build_atlas(factory)
        found: Any = None
        for continuity in continuities:
            scope = await atlas.scope(universe.id, continuity.id)
            definition = next(
                (a for a in scope.knowledge.story_scopes if a.slug == arguments.arc), None
            )
            if definition and definition.continuity_id == continuity.id:
                found = (continuity, definition)
        if found is None:
            raise SystemExit(f"No arc '{arguments.arc}' is configured for {arguments.world}")
        continuity, definition = found
        boundary = definition.last_position
        service = ArcIntelligence(atlas, atlas.presentations, retrieval)
        scope, _, facts = await service.context(
            universe.id, continuity.id, UUID(definition.id), boundary
        )
        passages = await retrieval.arc_passages(
            universe.id,
            continuity.id,
            first_position=definition.first_position,
            last_position=definition.last_position,
            position_basis=definition.position_basis,
            spoiler_position=boundary,
        )
        say(f"{len(passages.sources)} sources, {len(passages.sentences)} sentences")
        router = create_inference(settings, LocalModelLease(factory))
        cache: Path = arguments.cache
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
                        allow_local_fallback=False,
                    )
                    break
                except InferenceFailure as error:
                    invalid += error.code == "structured_output_exhausted"
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
            slug=arguments.world + DRAFT_SUFFIX,
            world_title=f"{universe.title} (draft)",
            arc_key=definition.slug,
            arc_title=definition.title,
            medium=continuity.medium,
            passages=passages,
            story_bible=build_story_bible(scope.knowledge.nodes, facts, boundary),
            infer=infer,
            subjects=arguments.subject,
            progress=say,
        )
        out: Path = arguments.out
        out.mkdir(parents=True, exist_ok=True)
        corrections = out / f"{definition.slug}.edits.json"
        if corrections.exists():
            edits = PackEdits.model_validate_json(corrections.read_text(encoding="utf-8"))
            pack, skipped = apply_edits(draft.pack, edits)
            draft = PackDraft(pack, [*skipped, *draft.notes])
            say("Applied your saved corrections")
        pack_file = out / f"{definition.slug}.json"
        pack_file.write_text(draft.pack.model_dump_json(indent=2), encoding="utf-8")
        (out / f"{definition.slug}.md").write_text(render_review(draft), encoding="utf-8")
        say(f"Draft ready: {pack_file} ({len(draft.notes)} items to check)")
    finally:
        await engine.dispose()


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True)
    parser.add_argument("--arc", required=True)
    parser.add_argument("--subject", action="append", default=[], help="deep page; repeatable")
    parser.add_argument("--out", type=Path, default=root / "story-packs")
    parser.add_argument("--cache", type=Path, default=root / ".tmp" / "story-spike" / "cache")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
