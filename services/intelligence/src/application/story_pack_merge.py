"""Join per-arc packs into one world, so a new arc adds to the atlas instead of replacing it."""

from typing import Any

from src.application.story_cast import name_key
from src.application.story_pack import StoryPack

CAST_FIELDS = ("characters", "places", "objects", "mysteries")


def _free(key: str, taken: set[str]) -> str:
    candidate, n = key, 2
    while candidate in taken:
        candidate, n = f"{key[:74]}-{n}", n + 1
    taken.add(candidate)
    return candidate


def _recite(value: Any, sources: dict[str, str]) -> None:
    """Point every citation under ``value`` at the merged source keys."""
    if isinstance(value, list):
        for item in value:
            _recite(item, sources)
    elif isinstance(value, dict):
        if "source" in value and "quote" in value:
            value["source"] = sources[value["source"]]
        else:
            for item in value.values():
                _recite(item, sources)


def merge_packs(packs: list[StoryPack]) -> StoryPack:
    """Entries sharing a kind and a name or alias become one; other clashing keys are renamed."""
    if not packs:
        raise ValueError("There is no drafted arc to load")
    if len({p.slug for p in packs}) != 1:
        raise ValueError("Only arcs of the same draft world can be merged")
    sources: dict[tuple[str, int], dict[str, Any]] = {}
    entities: list[dict[str, Any]] = []
    names: dict[tuple[str, str], dict[str, Any]] = {}
    arcs: list[dict[str, Any]] = []
    lore: list[dict[str, Any]] = []
    source_keys: set[str] = set()
    keys: set[str] = set()
    arc_keys: set[str] = set()
    thread_keys: set[str] = set()
    discovery_keys: set[str] = set()
    for pack in packs:
        data = pack.model_dump(mode="json")
        cited: dict[str, str] = {}
        for source in data["sources"]:
            # One page can come at different points of two arcs, naming a stop in each.
            place = (source["url"], source["position"])
            existing = sources.get(place)
            if existing is None:
                existing = {**source, "key": _free(source["key"], source_keys)}
                sources[place] = existing
            cited[source["key"]] = existing["key"]
        for part in (data["entities"], data["arcs"], data["lore"]):
            _recite(part, cited)
        renamed: dict[str, str] = {}
        for entity in data["entities"]:
            labels = {name_key(n) for n in (entity["name"], *entity["aliases"])} - {""}
            found = next(
                (names[(entity["type"], n)] for n in labels if (entity["type"], n) in names), None
            )
            if found is None:
                found = {**entity, "key": _free(entity["key"], keys)}
                entities.append(found)
            else:
                aliases = [*found["aliases"], entity["name"], *entity["aliases"]]
                found["aliases"] = list(dict.fromkeys(a for a in aliases if a != found["name"]))[
                    :12
                ]
                found["chapter"] = min(found["chapter"], entity["chapter"])
                found["sections"] = [*found["sections"], *entity["sections"]][:12]
                found["sources"] = [*found["sources"], *entity["sources"]][:8]
            renamed[entity["key"]] = found["key"]
            for label in labels:
                names.setdefault((entity["type"], label), found)
        threads: dict[str, str] = {}
        for thread in data["lore"]:
            threads[thread["key"]] = thread["key"] = _free(thread["key"], thread_keys)
            thread["concept"] = renamed[thread["concept"]]
            for discovery in thread["discoveries"]:
                discovery["key"] = _free(discovery["key"], discovery_keys)
            lore.append(thread)
        for arc in data["arcs"]:
            arc["key"] = _free(arc["key"], arc_keys)
            events: dict[str, str] = {}
            for event in arc["events"]:
                events[event["key"]] = event["key"] = _free(event["key"], keys)
                for field in CAST_FIELDS:
                    event[field] = list(dict.fromkeys(renamed[k] for k in event[field]))
                event["lore"] = [threads[k] for k in event["lore"]]
            for link in arc["links"]:
                link["cause"], link["effect"] = events[link["cause"]], events[link["effect"]]
            for section in arc["story"]:
                for paragraph in section["paragraphs"]:
                    paragraph["events"] = [events[k] for k in paragraph["events"]]
            arcs.append(arc)
    return StoryPack.model_validate(
        {
            **packs[0].model_dump(mode="json"),
            "sources": list(sources.values()),
            "entities": entities,
            "arcs": arcs,
            "lore": lore,
        }
    )
