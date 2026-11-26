"""A reviewer's corrections, kept beside a draft so regenerating it never loses them."""

from typing import Any

from pydantic import Field

from src.application.research_contracts import StructuredModel
from src.application.story_pack import Citation, StoryPack

CAST_FIELDS = ("characters", "places", "objects", "mysteries")


class EventEdit(StructuredModel):
    title: str | None = None
    summary: str | None = None
    label: str | None = None
    sources: list[Citation] | None = None
    after: str | None = None


class PackEdits(StructuredModel):
    events: dict[str, EventEdit] = Field(default_factory=dict)
    chapter_labels: dict[int, str] = Field(default_factory=dict)
    rename: dict[str, str] = Field(default_factory=dict)
    merge: dict[str, str] = Field(default_factory=dict)
    drop: list[str] = Field(default_factory=list)


def apply_edits(pack: StoryPack, edits: PackEdits) -> tuple[StoryPack, list[str]]:
    """Apply corrections by key. Edits that no longer match are reported, not guessed."""
    data = pack.model_dump(mode="json")
    notes: list[str] = []
    entities = {e["key"]: e for e in data["entities"]}
    events = [e for arc in data["arcs"] for e in arc["events"]]

    def replace_entity(old: str, new: str | None) -> None:
        for event in events:
            for field in CAST_FIELDS:
                keys = [new if k == old else k for k in event[field]]
                event[field] = list(dict.fromkeys(k for k in keys if k))
        if new:
            for thread in data["lore"]:
                if thread["concept"] == old:
                    thread["concept"] = new
        else:
            data["lore"] = [t for t in data["lore"] if t["concept"] != old]
        entities.pop(old)

    for old, new in edits.merge.items():
        if old not in entities or new not in entities or old == new:
            notes.append(f"Edit skipped: cannot merge {old} into {new}")
            continue
        source, target = entities[old], entities[new]
        if source["type"] != target["type"]:
            notes.append(f"Edit skipped: {old} and {new} are different kinds")
            continue
        aliases = [*target["aliases"], source["name"], *source["aliases"]]
        target["aliases"] = list(dict.fromkeys(a for a in aliases if a != target["name"]))[:12]
        target["chapter"] = min(target["chapter"], source["chapter"])
        target["sections"] += source["sections"]
        replace_entity(old, new)
    for key in edits.drop:
        if key in entities:
            replace_entity(key, None)
        else:
            notes.append(f"Edit skipped: no entry {key} to drop")
    for key, name in edits.rename.items():
        if key in entities:
            entity = entities[key]
            aliases = [*entity["aliases"], entity["name"]]
            entity["aliases"] = list(dict.fromkeys(a for a in aliases if a != name))[:12]
            entity["name"] = name
        else:
            notes.append(f"Edit skipped: no entry {key} to rename")
    data["entities"] = [e for e in data["entities"] if e["key"] in entities]

    for event in events:
        if event["chapter"] in edits.chapter_labels:
            event["label"] = edits.chapter_labels[event["chapter"]]
    known = {e["key"] for e in events}
    for key, edit in edits.events.items():
        if key not in known:
            notes.append(f"Edit skipped: no event {key}")
            continue
        event = next(e for e in events if e["key"] == key)
        changed: dict[str, Any] = edit.model_dump(mode="json", exclude_none=True, exclude={"after"})
        event.update(changed)
        if edit.after:
            arc = next(a for a in data["arcs"] if event in a["events"])
            target = next((e for e in arc["events"] if e["key"] == edit.after), None)
            if target is None or target is event:
                notes.append(f"Edit skipped: cannot move {key} after {edit.after}")
                continue
            arc["events"].remove(event)
            arc["events"].insert(arc["events"].index(target) + 1, event)
    return StoryPack.model_validate(data), notes
