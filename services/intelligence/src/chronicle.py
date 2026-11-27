"""Build and load story atlases from the file library.

python -m src.chronicle scout <world> <arc>   find and save pages from approved sites
python -m src.chronicle check <world> <arc>   what would be read (no model calls)
python -m src.chronicle build <world> <arc>   draft the arc's pack for review (resumable)
python -m src.chronicle load <world>          merge every drafted arc into the draft world
"""

import argparse
import asyncio
import sys
from pathlib import Path

from src.application.story_library import library_passages
from src.infrastructure.story_builds import default_library
from src.infrastructure.story_library_files import StoryLibraryFiles
from src.infrastructure.story_pipeline import build_arc, fetch_pages, find_pages, load_world


def say(message: str) -> None:
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


async def scout(
    files: StoryLibraryFiles, world: str, arc: str, about: str, start: list[str]
) -> None:
    await find_pages(files, world, arc, about, start, say)
    await fetch_pages(files, world, arc, say)


def main() -> None:
    root = default_library()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["scout", "check", "build", "load"])
    parser.add_argument("world")
    parser.add_argument("arc", nargs="?")
    parser.add_argument("--library", type=Path, default=root)
    parser.add_argument("--about", default="", help="what scout should cover")
    parser.add_argument("--start", action="append", default=[], help="overview page title")
    parser.add_argument("--pages", type=int, default=12, help="deep pages for main names")
    parser.add_argument("--subject", action="append", default=[], help="deep page; repeatable")
    arguments = parser.parse_args()
    files = StoryLibraryFiles(arguments.library)
    try:
        if arguments.command == "load":
            asyncio.run(load_world(files, arguments.world, say))
            return
        if not arguments.arc:
            parser.error("name the arc")
        if arguments.command == "scout":
            asyncio.run(
                scout(files, arguments.world, arguments.arc, arguments.about, arguments.start)
            )
            return
        if arguments.command == "build":
            asyncio.run(
                build_arc(
                    files,
                    arguments.world,
                    arguments.arc,
                    arguments.subject,
                    arguments.pages,
                    say,
                )
            )
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
