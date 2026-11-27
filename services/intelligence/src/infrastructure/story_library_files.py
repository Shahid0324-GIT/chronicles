"""Reads ``<root>/<world>/world.json`` and ``<root>/<world>/<arc>/sources/*.json``."""

from pathlib import Path

from src.application.story_library import LibraryArc, LibrarySource, LibraryWorld


class StoryLibraryFiles:
    def __init__(self, root: Path) -> None:
        self.root = root

    def folder(self, world: str) -> Path:
        if not world or Path(world).name != world:
            raise ValueError("A world is named by its folder, without path separators")
        return self.root / world

    def world(self, slug: str) -> LibraryWorld:
        path = self.folder(slug) / "world.json"
        if not path.is_file():
            raise ValueError(f"No world.json for '{slug}' in {self.root}")
        world = LibraryWorld.model_validate_json(path.read_text(encoding="utf-8-sig"))
        if world.slug != slug:
            raise ValueError(f"world.json slug '{world.slug}' does not match folder '{slug}'")
        return world

    def arc(self, world: LibraryWorld, key: str) -> LibraryArc:
        found = next((a for a in world.arcs if a.key == key), None)
        if found is None:
            known = ", ".join(a.key for a in world.arcs)
            raise ValueError(f"No arc '{key}' in {world.slug}; known arcs: {known}")
        return found

    def sources(self, world: LibraryWorld, arc: str) -> list[LibrarySource]:
        folder = self.folder(world.slug) / self.arc(world, arc).key / "sources"
        return [
            LibrarySource.model_validate_json(path.read_text(encoding="utf-8-sig"))
            for path in sorted(folder.glob("*.json"))
        ]

    def packs(self, world: LibraryWorld) -> list[Path]:
        """Drafted arc packs, in the order the world lists its arcs."""
        paths = [self.folder(world.slug) / arc.key / "pack.json" for arc in world.arcs]
        return [p for p in paths if p.is_file()]
