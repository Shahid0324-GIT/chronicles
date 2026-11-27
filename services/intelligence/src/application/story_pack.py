"""Story packs: one reviewable draft file per arc, projected onto the atlas screens.

A pack is AI-drafted content that a person reviews. It lives in its own "-draft"
universe, is never canonical knowledge, and is never presented as verified.
"""

from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import Field, model_validator

from src.application.research_contracts import StructuredModel
from src.domain.entities import Continuity, GraphNode, GraphRelationship, Universe
from src.domain.value_objects import NodeType, RelationshipType, Slug

DRAFT_SUFFIX = "-draft"
EntityType = Literal["CHARACTER", "LOCATION", "OBJECT", "MYSTERY", "LORE", "FACTION"]
CATEGORY = {
    "CHARACTER": "character",
    "LOCATION": "place",
    "OBJECT": "object",
    "MYSTERY": "mystery",
    "LORE": "lore",
    "FACTION": "faction",
    "EVENT": "event",
}
Key = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)


class PackSource(StructuredModel):
    key: str = Key
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(pattern=r"^https?://", max_length=1000)


class Citation(StructuredModel):
    source: str = Key
    quote: str = Field(default="", max_length=1000)


class PackStatement(StructuredModel):
    text: str = Field(min_length=8, max_length=500)
    chapter: int = Field(ge=1)
    sources: list[Citation] = Field(min_length=1, max_length=6)


class PackSection(StructuredModel):
    name: str = Field(min_length=2, max_length=60)
    statements: list[PackStatement] = Field(min_length=1, max_length=20)


class PackEntity(StructuredModel):
    key: str = Key
    type: EntityType
    name: str = Field(min_length=1, max_length=100)
    aliases: list[str] = Field(default_factory=list, max_length=12)
    introduction: str = Field(min_length=12, max_length=350)
    chapter: int = Field(ge=1)
    sources: list[Citation] = Field(min_length=1, max_length=8)
    sections: list[PackSection] = Field(default_factory=list, max_length=12)


class PackEvent(StructuredModel):
    key: str = Key
    title: str = Field(min_length=3, max_length=100)
    summary: str = Field(min_length=20, max_length=1200)
    chapter: int = Field(ge=1)
    label: str = Field(default="", max_length=60)
    characters: list[str] = Field(default_factory=list, max_length=16)
    places: list[str] = Field(default_factory=list, max_length=8)
    objects: list[str] = Field(default_factory=list, max_length=8)
    mysteries: list[str] = Field(default_factory=list, max_length=6)
    lore: list[str] = Field(default_factory=list, max_length=6)
    sources: list[Citation] = Field(min_length=1, max_length=12)


class PackLink(StructuredModel):
    cause: str = Key
    effect: str = Key
    kind: Literal["CAUSED", "ENABLED"]
    reason: str = Field(min_length=8, max_length=400)
    sources: list[Citation] = Field(min_length=1, max_length=4)


class PackParagraph(StructuredModel):
    """One paragraph of the arc told as a story, tied to its events and sources."""

    text: str = Field(min_length=40, max_length=2600)
    chapter: int = Field(ge=1)
    events: list[str] = Field(default_factory=list, max_length=20)
    sources: list[Citation] = Field(min_length=1, max_length=12)


class PackStorySection(StructuredModel):
    heading: str = Field(min_length=3, max_length=150)
    paragraphs: list[PackParagraph] = Field(min_length=1, max_length=12)


class PackArc(StructuredModel):
    key: str = Key
    title: str = Field(min_length=1, max_length=100)
    introduction: str = Field(min_length=12, max_length=1200)
    events: list[PackEvent] = Field(min_length=1, max_length=80)
    links: list[PackLink] = Field(default_factory=list, max_length=200)
    story: list[PackStorySection] = Field(default_factory=list, max_length=60)


class PackDiscovery(StructuredModel):
    key: str = Key
    title: str = Field(min_length=3, max_length=100)
    explanation: str = Field(min_length=12, max_length=1200)
    classification: Literal["established", "interpretation", "unresolved"]
    chapter: int = Field(ge=1)
    sources: list[Citation] = Field(min_length=1, max_length=8)


class PackThread(StructuredModel):
    key: str = Key
    title: str = Field(min_length=3, max_length=100)
    concept: str = Key
    introduction: str = Field(min_length=12, max_length=600)
    discoveries: list[PackDiscovery] = Field(min_length=1, max_length=12)


class StoryPack(StructuredModel):
    schema_version: Literal["story-pack-v1"] = "story-pack-v1"
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*-draft$", max_length=100)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=600)
    medium: str = Field(min_length=1, max_length=40)
    sources: list[PackSource] = Field(min_length=1, max_length=100)
    entities: list[PackEntity] = Field(default_factory=list, max_length=300)
    arcs: list[PackArc] = Field(min_length=1, max_length=20)
    lore: list[PackThread] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def references_resolve(self) -> "StoryPack":
        """Report every broken reference at once, so a reviewer can fix them together."""
        problems: list[str] = []

        def unique(label: str, keys: list[str]) -> set[str]:
            duplicated = sorted({k for k in keys if keys.count(k) > 1})
            if duplicated:
                problems.append(f"duplicate {label} keys: {', '.join(duplicated)}")
            return set(keys)

        sources = unique("source", [s.key for s in self.sources])
        events = [e for arc in self.arcs for e in arc.events]
        entities = {e.key: e.type for e in self.entities}
        unique("entity or event", [e.key for e in self.entities] + [e.key for e in events])
        threads = unique("lore thread", [t.key for t in self.lore])
        unique("discovery", [d.key for t in self.lore for d in t.discoveries])
        unique("arc", [a.key for a in self.arcs])

        def cited(owner: str, citations: list[Citation]) -> None:
            for c in citations:
                if c.source not in sources:
                    problems.append(f"{owner} cites unknown source {c.source}")

        for entity in self.entities:
            cited(entity.key, entity.sources)
            for section in entity.sections:
                for statement in section.statements:
                    cited(entity.key, statement.sources)
        for arc in self.arcs:
            order = {e.key: i for i, e in enumerate(arc.events)}
            for event in arc.events:
                cited(event.key, event.sources)
                for expected, keys in (
                    ("CHARACTER", event.characters),
                    ("LOCATION", event.places),
                    ("OBJECT", event.objects),
                    ("MYSTERY", event.mysteries),
                ):
                    for key in keys:
                        if entities.get(key) != expected:
                            problems.append(f"{event.key}: {key} is not a known {expected}")
                for key in event.lore:
                    if key not in threads:
                        problems.append(f"{event.key}: unknown lore thread {key}")
            for told_part in arc.story:
                for told_paragraph in told_part.paragraphs:
                    cited(told_part.heading, told_paragraph.sources)
                    for key in told_paragraph.events:
                        if key not in order:
                            problems.append(f"{told_part.heading}: unknown event {key}")
            for link in arc.links:
                cited(f"{link.cause}->{link.effect}", link.sources)
                if link.cause not in order or link.effect not in order:
                    problems.append(f"link {link.cause}->{link.effect} leaves arc {arc.key}")
                elif order[link.cause] >= order[link.effect]:
                    problems.append(f"link {link.cause}->{link.effect} runs backwards")
        for thread in self.lore:
            if thread.concept not in entities:
                problems.append(f"{thread.key}: unknown concept {thread.concept}")
            for discovery in thread.discoveries:
                cited(discovery.key, discovery.sources)
        if problems:
            raise ValueError("; ".join(problems[:30]))
        return self


def identifier(slug: str, kind: str, key: str = "") -> UUID:
    return uuid5(NAMESPACE_URL, f"chronicles:story-pack:{slug}:{kind}:{key}")


def universe_id(slug: str) -> UUID:
    return identifier(slug, "universe")


def continuity_id(slug: str) -> UUID:
    return identifier(slug, "continuity")


def storage_id(universe: UUID, continuity: UUID) -> UUID:
    return uuid5(continuity, f"story-pack:{universe}")


def graph(pack: StoryPack) -> tuple[Universe, Continuity, list[GraphNode], list[GraphRelationship]]:
    """Domain graph records for the draft universe, endpoint rules checked."""
    universe = Universe(
        id=universe_id(pack.slug),
        slug=Slug(pack.slug),
        title=pack.title,
        description=pack.description,
    )
    continuity = Continuity(
        id=continuity_id(pack.slug),
        universe_id=universe.id,
        name=f"{pack.medium.title()} · AI draft, unreviewed",
        medium=pack.medium,
        description="Drafted by AI from the cited sources for review. Not verified canon.",
    )

    def node(key: str, kind: NodeType, title: str, summary: str) -> GraphNode:
        return GraphNode(
            id=identifier(pack.slug, "node", key),
            universe_id=universe.id,
            continuity_id=continuity.id,
            type=kind,
            title=title,
            summary=summary,
            metadata={"draft": True, "pack_key": key},
        )

    nodes = [node(e.key, NodeType(e.type), e.name, e.introduction) for e in pack.entities]
    nodes += [
        node(e.key, NodeType.EVENT, e.title, e.summary) for arc in pack.arcs for e in arc.events
    ]
    lookup = {n.id: n for n in nodes}
    edges: dict[UUID, GraphRelationship] = {}

    def connect(source: str, target: str, kind: RelationshipType, description: str) -> None:
        edge = GraphRelationship(
            id=identifier(pack.slug, "edge", f"{source}:{target}:{kind.value}"),
            universe_id=universe.id,
            continuity_id=continuity.id,
            source_node_id=identifier(pack.slug, "node", source),
            target_node_id=identifier(pack.slug, "node", target),
            relationship_type=kind,
            description=description,
        )
        edge.validate_endpoints(lookup[edge.source_node_id], lookup[edge.target_node_id])
        edges[edge.id] = edge

    for arc in pack.arcs:
        for event in arc.events:
            for key in event.characters:
                connect(key, event.key, RelationshipType.PARTICIPATED_IN, "Takes part.")
            for key in event.places:
                connect(event.key, key, RelationshipType.OCCURRED_AT, "Happens here.")
            for key in (*event.objects, *event.mysteries):
                connect(event.key, key, RelationshipType.CONNECTED_TO, "Appears in this event.")
        for link in arc.links:
            connect(link.cause, link.effect, RelationshipType(link.kind), link.reason)
    return universe, continuity, nodes, list(edges.values())


class _Sources:
    """Citations rendered the way the screens expect them."""

    def __init__(self, pack: StoryPack) -> None:
        self.slug = pack.slug
        self.by_key = {s.key: s for s in pack.sources}

    def uuid(self, key: str) -> str:
        return str(identifier(self.slug, "source", key))

    def ids(self, citations: list[Citation]) -> list[str]:
        return list(dict.fromkeys(self.uuid(c.source) for c in citations))


def _visible(chapter: int, boundary: int | None) -> bool:
    return boundary is None or chapter <= boundary


def catalog(pack: StoryPack, boundary: int | None = None) -> dict[str, Any]:
    """The story map response; nothing beyond the reader's chapter boundary is included."""
    _, continuity, _, edges = graph(pack)
    sources = _Sources(pack)
    universe = universe_id(pack.slug)

    def node_id(key: str) -> str:
        return str(identifier(pack.slug, "node", key))

    events = {e.key: e for arc in pack.arcs for e in arc.events if _visible(e.chapter, boundary)}
    entities = [e for e in pack.entities if _visible(e.chapter, boundary)]
    shown = {node_id(k) for k in events} | {node_id(e.key) for e in entities}
    visible_edges = [
        e for e in edges if str(e.source_node_id) in shown and str(e.target_node_id) in shown
    ]
    threads, discoveries = [], []
    for thread in pack.lore:
        found = [d for d in thread.discoveries if _visible(d.chapter, boundary)]
        if not found or node_id(thread.concept) not in shown:
            continue
        thread_id = str(identifier(pack.slug, "thread", thread.key))
        ids = [str(identifier(pack.slug, "discovery", d.key)) for d in found]
        threads.append(
            {
                "id": thread_id,
                "universeId": str(universe),
                "continuityId": str(continuity.id),
                "conceptNodeId": node_id(thread.concept),
                "title": thread.title,
                "introduction": thread.introduction,
                "spoilerScope": "Draft lore thread",
                "discoveryIds": ids,
                "initialDiscoveryId": ids[0],
                "presentation": {
                    "relatedNodeIds": [node_id(thread.concept)],
                    "relationshipIds": [],
                },
            }
        )
        for discovery, discovery_id in zip(found, ids, strict=True):
            discoveries.append(
                {
                    "id": discovery_id,
                    "threadId": thread_id,
                    "nodeId": node_id(thread.concept),
                    "title": discovery.title,
                    "explanation": discovery.explanation,
                    "classification": discovery.classification,
                    "sourceIds": sources.ids(discovery.sources),
                    "relatedDiscoveryIds": [i for i in ids if i != discovery_id],
                    "presentation": {
                        "relatedNodeIds": [node_id(thread.concept)],
                        "relationshipIds": [],
                    },
                }
            )
    available_threads = {t["id"] for t in threads}
    journeys = []
    for arc in pack.arcs:
        steps = []
        for event in arc.events:
            if event.key not in events:
                continue
            own = node_id(event.key)
            direct = [
                e for e in visible_edges if own in (str(e.source_node_id), str(e.target_node_id))
            ]
            related = [
                node_id(k)
                for k in (*event.characters, *event.places, *event.objects, *event.mysteries)
                if node_id(k) in shown
            ]
            steps.append(
                {
                    "id": str(identifier(pack.slug, "step", event.key)),
                    "eventNodeId": own,
                    "title": event.title,
                    "body": event.summary,
                    "episodeLabel": event.label or f"By chapter {event.chapter}",
                    "sourceIds": sources.ids(event.sources),
                    "loreThreadIds": [
                        i
                        for k in event.lore
                        if (i := str(identifier(pack.slug, "thread", k))) in available_threads
                    ],
                    "presentation": {
                        "relatedNodeIds": related,
                        "relationshipIds": [str(e.id) for e in direct],
                    },
                }
            )
        if steps:
            used = list(dict.fromkeys(i for s in steps for i in s["sourceIds"]))
            journeys.append(
                {
                    "id": str(identifier(pack.slug, "arc", arc.key)),
                    "universeId": str(universe),
                    "continuityId": str(continuity.id),
                    "title": arc.title,
                    "introduction": arc.introduction,
                    "spoilerScope": "AI draft awaiting review",
                    "ordering": {
                        "basis": "manga-chapter",
                        "explanation": "Draft story order merged from sources; not verified.",
                        "sourceIds": used,
                    },
                    "steps": steps,
                    "story": [
                        {"heading": section.heading, "paragraphs": told}
                        for section in arc.story
                        if (
                            told := [
                                {
                                    "text": p.text,
                                    "eventNodeIds": [node_id(k) for k in p.events if k in events],
                                    "sourceIds": sources.ids(p.sources),
                                }
                                for p in section.paragraphs
                                if _visible(p.chapter, boundary)
                            ]
                        )
                    ],
                }
            )
    return {
        "schemaVersion": 1,
        "partial": True,
        "orderingGaps": [],
        "revision": str(identifier(pack.slug, "revision", pack.model_dump_json())),
        "journeys": journeys,
        "loreThreads": threads,
        "discoveries": discoveries,
        "sources": [
            {
                "id": sources.uuid(s.key),
                "title": s.title,
                "url": s.url,
                "locator": "Cited by this draft",
            }
            for s in pack.sources
        ],
        "entryIndex": [{"id": node_id(k), "displayTitle": e.title} for k, e in events.items()]
        + [{"id": node_id(e.key), "displayTitle": e.name} for e in entities],
        "relations": [
            {
                "id": str(e.id),
                "source": str(e.source_node_id),
                "target": str(e.target_node_id),
                "type": e.relationship_type.value,
            }
            for e in visible_edges
        ],
    }


def entries(pack: StoryPack, boundary: int | None = None) -> list[dict[str, Any]]:
    """One encyclopedia page per visible character, place, item, lore subject and event."""
    sources = _Sources(pack)
    built = catalog(pack, boundary)
    titles = {e["id"]: e["displayTitle"] for e in built["entryIndex"]}
    events = [e for arc in pack.arcs for e in arc.events if _visible(e.chapter, boundary)]

    def references(citations: list[Citation]) -> list[dict[str, str]]:
        seen: dict[tuple[str, str], dict[str, str]] = {}
        for c in citations:
            source = sources.by_key[c.source]
            reference = {
                "id": sources.uuid(c.source),
                "title": source.title,
                "url": source.url,
                "locator": "Cited by this draft",
            }
            if c.quote:
                reference["quote"] = c.quote
            seen[(c.source, c.quote)] = reference
        return list(seen.values())

    def page(
        key: str,
        graph_type: str,
        name: str,
        introduction: str,
        aliases: list[str],
        sections: list[dict[str, Any]],
        citations: list[Citation],
    ) -> dict[str, Any]:
        own = str(identifier(pack.slug, "node", key))
        return {
            "id": own,
            "entry_type": CATEGORY[graph_type],
            "graph_type": graph_type,
            "display_title": titles.get(own, name),
            "short_introduction": introduction,
            "detailed_overview": introduction,
            "aliases": aliases,
            "original_names": [],
            "sections": sections,
            "connections": [
                {k: str(v) for k, v in r.items()}
                for r in built["relations"]
                if own in (r["source"], r["target"])
            ],
            "source_references": references(citations),
            "continuity_id": str(continuity_id(pack.slug)),
            "language": "en",
            "spoiler_position": boundary,
            "knowledge_revision": built["revision"],
            "presentation": {"status": "draft"},
        }

    def statements(owner: str, name: str, texts: list[str]) -> dict[str, Any]:
        return {
            "name": name,
            "statements": [
                {
                    "text": text[:500],
                    "fact_ids": [str(identifier(pack.slug, "statement", f"{owner}:{name}:{i}"))],
                }
                for i, text in enumerate(texts)
            ],
        }

    result = []
    for entity in pack.entities:
        if not _visible(entity.chapter, boundary):
            continue
        sections, citations = [], list(entity.sources)
        for section in entity.sections:
            visible = [s for s in section.statements if _visible(s.chapter, boundary)]
            if visible:
                sections.append(statements(entity.key, section.name, [s.text for s in visible]))
                citations += [c for s in visible for c in s.sources]
        # The subject's events, in story order, are assembled here rather than rewritten.
        own_events = [
            f"Chapter {e.chapter}: {e.title}"
            for e in events
            if entity.key in (*e.characters, *e.places, *e.objects, *e.mysteries)
        ]
        if own_events:
            sections.append(statements(entity.key, "in the story", own_events[:20]))
        result.append(
            page(
                entity.key,
                entity.type,
                entity.name,
                entity.introduction,
                entity.aliases,
                sections,
                citations,
            )
        )
    for event in events:
        introduction = event.summary if len(event.summary) <= 350 else event.summary[:347] + "..."
        result.append(
            page(
                event.key,
                "EVENT",
                event.title,
                introduction,
                [],
                [],
                event.sources,
            )
        )
    return result
