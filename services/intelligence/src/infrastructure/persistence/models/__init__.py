from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UniverseModel(Base):
    __tablename__ = "universes"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ContinuityModel(Base):
    __tablename__ = "continuities"
    __table_args__ = (UniqueConstraint("id", "universe_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID] = mapped_column(ForeignKey("universes.id"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    medium: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)


class NodeModel(Base):
    __tablename__ = "graph_nodes"
    __table_args__ = (
        UniqueConstraint("id", "universe_id"),
        ForeignKeyConstraint(
            ["continuity_id", "universe_id"], ["continuities.id", "continuities.universe_id"]
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID] = mapped_column(ForeignKey("universes.id"), index=True)
    continuity_id: Mapped[UUID | None] = mapped_column(index=True)
    type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    node_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON().with_variant(JSONB, "postgresql")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RelationshipModel(Base):
    __tablename__ = "graph_relationships"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_node_id", "universe_id"], ["graph_nodes.id", "graph_nodes.universe_id"]
        ),
        ForeignKeyConstraint(
            ["target_node_id", "universe_id"], ["graph_nodes.id", "graph_nodes.universe_id"]
        ),
        ForeignKeyConstraint(
            ["continuity_id", "universe_id"], ["continuities.id", "continuities.universe_id"]
        ),
        Index("ix_relationship_source", "source_node_id"),
        Index("ix_relationship_target", "target_node_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    universe_id: Mapped[UUID] = mapped_column(ForeignKey("universes.id"), index=True)
    continuity_id: Mapped[UUID | None] = mapped_column()
    source_node_id: Mapped[UUID] = mapped_column()
    target_node_id: Mapped[UUID] = mapped_column()
    relationship_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
