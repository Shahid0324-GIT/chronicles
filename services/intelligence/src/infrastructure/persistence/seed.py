"""Illustrative, hand-curated anime episode 1–3 sample. No AI-generated research."""

import asyncio
from dataclasses import asdict
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Continuity, GraphNode, GraphRelationship, Universe
from src.domain.value_objects import NodeType, RelationshipType, Slug
from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.database import create_database
from src.infrastructure.persistence.models import (
    ContinuityModel,
    NodeModel,
    RelationshipModel,
    UniverseModel,
)


def identity(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"universe-atlas:illustrative:re-zero:{key}")


def sample_graph() -> tuple[Universe, Continuity, list[GraphNode], list[GraphRelationship]]:
    universe = Universe(
        id=identity("universe"),
        slug=Slug("re-zero"),
        title="Re:Zero — Starting Life in Another World",
        description="A stranger in a royal capital. A stolen insignia. Paths that cross again. "
        "An illustrative atlas of the anime’s opening three episodes; early-story spoilers.",
    )
    continuity = Continuity(
        id=identity("anime"),
        universe_id=universe.id,
        name="TV anime · opening episodes",
        medium="ANIME",
        description=(
            "Season 1, episodes 1–3 only. No equivalence with novel or manga events is implied."
        ),
    )
    entries = [
        (
            "subaru",
            "CHARACTER",
            "Subaru Natsuki",
            "A young man unexpectedly transported to another world.",
        ),
        (
            "emilia",
            "CHARACTER",
            "Emilia",
            "A silver-haired half-elf searching for her stolen insignia.",
        ),
        ("puck", "CHARACTER", "Puck", "A catlike spirit who accompanies Emilia."),
        ("felt", "CHARACTER", "Felt", "A young thief involved in the stolen insignia incident."),
        (
            "rom",
            "CHARACTER",
            "Old Man Rom",
            "The proprietor of a loot house in the capital’s slums.",
        ),
        (
            "reinhard",
            "CHARACTER",
            "Reinhard van Astrea",
            "A knight whom Subaru encounters in the capital.",
        ),
        (
            "capital",
            "LOCATION",
            "Royal Capital of Lugunica",
            "The city in which Subaru’s journey begins.",
        ),
        (
            "loot-house",
            "LOCATION",
            "Loot House",
            "A meeting place for a deal involving the stolen insignia.",
        ),
        ("insignia", "OBJECT", "Emilia’s insignia", "The stolen insignia Emilia is searching for."),
        (
            "search",
            "EVENT",
            "Search for the stolen insignia",
            "Subaru helps Emilia seek her missing insignia.",
        ),
    ]
    # Phase 2.5A: curated additions for the original broadcast's introductory presentation.
    # These are persisted graph facts, not frontend-generated research or inferred chronology.
    entries.extend(
        [
            (
                "arrival",
                "EVENT",
                "Arrival in the royal capital",
                "Subaru finds himself in another world and encounters its royal capital.",
            ),
            (
                "first-return",
                "EVENT",
                "The first return",
                "After a fatal encounter at the loot house, "
                "Subaru finds himself back in the capital.",
            ),
            (
                "recognition",
                "EVENT",
                "Recognizing Return by Death",
                "After repeated deaths and returns, Subaru recognizes the pattern "
                "and names it Return by Death.",
            ),
            (
                "return-by-death",
                "LORE",
                "Return by Death",
                "Subaru experiences a return to an earlier point after dying. "
                "This entry covers only its introductory presentation.",
            ),
            (
                "return-origin",
                "MYSTERY",
                "The unexplained cause of the return",
                "The cause of Subaru's returns remains unexplained "
                "within this introductory episode scope.",
            ),
        ]
    )
    nodes = [
        GraphNode(
            id=identity(key),
            universe_id=universe.id,
            continuity_id=continuity.id,
            type=NodeType(kind),
            title=title,
            summary=summary,
            metadata={
                "illustrative": True,
                "spoiler_scope": "TV anime S1 episodes 1–3",
                "source": "https://re-zero-anime.jp/tv/story/tv1r.html",
            },
        )
        for key, kind, title, summary in entries
    ]
    connections = [
        ("subaru", "search", "PARTICIPATED_IN", "Subaru helps search for the stolen insignia."),
        ("emilia", "search", "PARTICIPATED_IN", "Emilia seeks her stolen insignia."),
        ("search", "capital", "OCCURRED_AT", "The search takes place in the royal capital."),
        ("insignia", "emilia", "BELONGS_TO", "The insignia belongs to Emilia."),
        ("felt", "insignia", "CONNECTED_TO", "Felt steals the insignia at the start of the story."),
        ("rom", "loot-house", "CONNECTED_TO", "Rom runs the loot house."),
        ("loot-house", "capital", "CONNECTED_TO", "The loot house is in the capital’s slums."),
        ("puck", "emilia", "ALLIED_WITH", "Puck accompanies and protects Emilia."),
        ("subaru", "emilia", "ALLIED_WITH", "Subaru offers Emilia his help in her search."),
        ("felt", "rom", "CONNECTED_TO", "Felt brings the stolen insignia to Rom’s loot house."),
        ("reinhard", "subaru", "CONNECTED_TO", "Reinhard meets Subaru in the capital."),
        ("search", "insignia", "CONNECTED_TO", "The missing insignia is the object of the search."),
    ]
    connections.extend(
        [
            (
                "arrival",
                "capital",
                "OCCURRED_AT",
                "Subaru's arrival places him in the royal capital.",
            ),
            (
                "subaru",
                "arrival",
                "PARTICIPATED_IN",
                "Subaru is the stranger arriving in this world.",
            ),
            (
                "arrival",
                "search",
                "CONNECTED_TO",
                "The opening presentation moves from Subaru's arrival "
                "to helping search for the insignia.",
            ),
            (
                "search",
                "first-return",
                "CONNECTED_TO",
                "The initial search brings Subaru to the loot house before his first return.",
            ),
            (
                "subaru",
                "first-return",
                "PARTICIPATED_IN",
                "Subaru experiences the first fatal encounter and return.",
            ),
            (
                "first-return",
                "loot-house",
                "CONNECTED_TO",
                "The fatal encounter preceding the first return occurs at the loot house.",
            ),
            (
                "first-return",
                "capital",
                "OCCURRED_AT",
                "Subaru finds himself back in the capital after the first return.",
            ),
            (
                "first-return",
                "recognition",
                "CONNECTED_TO",
                "Repeated returns lead Subaru to recognize what is happening.",
            ),
            ("subaru", "recognition", "PARTICIPATED_IN", "Subaru recognizes the repeated pattern."),
            (
                "recognition",
                "return-by-death",
                "REVEALED",
                "Subaru identifies and names his experience Return by Death.",
            ),
            (
                "first-return",
                "return-by-death",
                "CONNECTED_TO",
                "The first return is an early instance of the phenomenon.",
            ),
            (
                "return-by-death",
                "subaru",
                "CONNECTED_TO",
                "The introductory story presents the phenomenon through Subaru's experience.",
            ),
            (
                "return-by-death",
                "return-origin",
                "CONNECTED_TO",
                "The phenomenon raises a question about its unexplained cause "
                "within the introduction.",
            ),
        ]
    )
    lookup = {n.id: n for n in nodes}
    edges = [
        GraphRelationship(
            id=identity(f"edge:{s}:{t}:{kind}"),
            universe_id=universe.id,
            continuity_id=continuity.id,
            source_node_id=identity(s),
            target_node_id=identity(t),
            relationship_type=RelationshipType(kind),
            description=description,
        )
        for s, t, kind, description in connections
    ]
    for edge in edges:
        edge.validate_endpoints(lookup[edge.source_node_id], lookup[edge.target_node_id])
    return universe, continuity, nodes, edges


async def seed(session: AsyncSession) -> None:
    """Caller owns the transaction. Existing rows are preserved, including user edits.

    Deterministic IDs make sequential reruns idempotent. Run one seed process at a time.
    """
    universe, continuity, nodes, edges = sample_graph()
    existing = await session.scalar(select(UniverseModel).where(UniverseModel.slug == "re-zero"))
    if existing is not None and existing.id != universe.id:
        raise ValueError("Slug re-zero already belongs to a different universe; seed cancelled")
    if await session.get(UniverseModel, universe.id) is None:
        values = asdict(universe)
        values["slug"] = str(universe.slug)
        session.add(UniverseModel(**values))
    await session.flush()
    if await session.get(ContinuityModel, continuity.id) is None:
        session.add(ContinuityModel(**asdict(continuity)))
    await session.flush()
    for node in nodes:
        if await session.get(NodeModel, node.id) is None:
            values = asdict(node)
            values["type"] = node.type.value
            values["node_metadata"] = values.pop("metadata")
            session.add(NodeModel(**values))
    await session.flush()
    for edge in edges:
        if await session.get(RelationshipModel, edge.id) is None:
            source = await session.get(NodeModel, edge.source_node_id)
            target = await session.get(NodeModel, edge.target_node_id)
            assert source is not None and target is not None
            from src.infrastructure.persistence.repositories import node_entity

            edge.validate_endpoints(node_entity(source), node_entity(target))
            values = asdict(edge)
            values["relationship_type"] = edge.relationship_type.value
            session.add(RelationshipModel(**values))
    await session.flush()


async def main() -> None:
    engine, factory = create_database(get_settings().database_url)
    try:
        async with factory() as session, session.begin():
            await seed(session)
        print(
            "Illustrative Re:Zero seed ready: 15 nodes, 25 relationships (existing rows preserved)."
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
