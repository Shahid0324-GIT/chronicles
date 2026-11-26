"""Load a reviewed story pack into its draft world: python -m src.import_story_pack FILE."""

import argparse
import asyncio
import sys
from pathlib import Path

from pydantic import ValidationError

from src.application.story_pack import StoryPack
from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.database import create_database
from src.infrastructure.persistence.story_pack_store import SqlStoryPackStore


async def publish(pack: StoryPack) -> dict[str, int]:
    engine, factory = create_database(get_settings().database_url)
    try:
        async with factory() as session, session.begin():
            return await SqlStoryPackStore(session).publish(pack)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path)
    parser.add_argument("--check", action="store_true", help="validate without writing")
    arguments = parser.parse_args()
    try:
        pack = StoryPack.model_validate_json(arguments.pack.read_text(encoding="utf-8"))
    except ValidationError as error:
        sys.exit(f"The story pack needs fixes:\n{error}")
    if arguments.check:
        sys.stdout.write(f"{pack.slug}: valid\n")
        return
    counts = asyncio.run(publish(pack))
    sys.stdout.write(
        f"Loaded {pack.slug}: {counts['nodes']} entries, "
        f"{counts['relationships']} connections (draft).\n"
    )


if __name__ == "__main__":
    main()
