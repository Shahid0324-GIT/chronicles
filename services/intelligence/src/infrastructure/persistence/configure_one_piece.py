"""Idempotent research configuration only; inserts no story facts or presentations."""

import asyncio
from dataclasses import asdict
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.research_policy import UniverseResearchProfile
from src.application.story_scope import ArcResearchScope
from src.domain.entities import Continuity, Universe
from src.domain.value_objects import Slug
from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.database import create_database
from src.infrastructure.persistence.models import ContinuityModel, UniverseModel
from src.infrastructure.persistence.research_memory import SqlResearchMemory

UNIVERSE_ID = uuid5(NAMESPACE_URL, "chronicles:one-piece")
MANGA_ID = uuid5(UNIVERSE_ID, "original-manga")
ROMANCE_DAWN = ArcResearchScope(
    slug="romance-dawn",
    title="Romance Dawn",
    continuity_id=MANGA_ID,
    first_position=1,
    last_position=7,
    references=[
        "https://grandlinewiki.net/eastbluearcM.html",
        "https://onepiece.fandom.com/wiki/Romance_Dawn_Arc",
    ],
)


async def configure(session: AsyncSession) -> None:
    existing = await session.scalar(select(UniverseModel).where(UniverseModel.slug == "one-piece"))
    if existing and existing.id != UNIVERSE_ID:
        raise ValueError("An existing One Piece universe needs explicit identity reconciliation")
    if not existing:
        universe = Universe(
            id=UNIVERSE_ID,
            slug=Slug("one-piece"),
            title="One Piece",
            description="Evidence-backed manga research. Partial coverage; separate adaptations.",
        )
        session.add(UniverseModel(**{**asdict(universe), "slug": "one-piece"}))
        await session.flush()
    if not await session.get(ContinuityModel, MANGA_ID):
        continuity = Continuity(
            id=MANGA_ID,
            universe_id=UNIVERSE_ID,
            name="Original manga",
            medium="MANGA",
            description="Eiichiro Oda's manga; no assumed equivalence to anime, films or games.",
        )
        session.add(ContinuityModel(**asdict(continuity)))
        await session.flush()
    memory = SqlResearchMemory(session)
    if not await memory.profile(UNIVERSE_ID):
        await memory.save_profile(
            UniverseResearchProfile(
                universe_id=UNIVERSE_ID,
                original_medium="manga",
                continuity_media={MANGA_ID: "MANGA"},
                story_scopes=[ROMANCE_DAWN],
                aliases=["ONE PIECE", "ワンピース"],
                primary_categories=["official", "chapter-index"],
                publishers=["Shueisha", "VIZ Media"],
                story_structure=(
                    "Romance Dawn research scope: manga chapters 1–7. Arc segmentation is an "
                    "attributed reference convention, not an official volume boundary."
                ),
                boundary_notes=(
                    "Volume 1 includes chapter 8; it is not the chapter 1–7 benchmark. "
                    "Chapter indexes establish no event facts. SBS and cover stories need "
                    "their own provenance."
                ),
            )
        )


async def main() -> None:
    engine, factory = create_database(get_settings().database_url)
    try:
        async with factory() as session, session.begin():
            await configure(session)
        print(f"One Piece manga configured: {UNIVERSE_ID}; {MANGA_ID}. No graph facts inserted.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
