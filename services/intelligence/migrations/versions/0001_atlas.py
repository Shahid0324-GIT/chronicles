"""Initial media-independent graph. Strings avoid PostgreSQL native-enum migration coupling."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_atlas"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "universes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "continuities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("universe_id", sa.Uuid(), sa.ForeignKey("universes.id"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("medium", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.UniqueConstraint("id", "universe_id"),
    )
    op.create_index("ix_continuities_universe_id", "continuities", ["universe_id"])
    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("universe_id", sa.Uuid(), sa.ForeignKey("universes.id"), nullable=False),
        sa.Column("continuity_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("id", "universe_id"),
        sa.ForeignKeyConstraint(
            ["continuity_id", "universe_id"], ["continuities.id", "continuities.universe_id"]
        ),
    )
    op.create_index("ix_graph_nodes_universe_id", "graph_nodes", ["universe_id"])
    op.create_index("ix_graph_nodes_continuity_id", "graph_nodes", ["continuity_id"])
    op.create_table(
        "graph_relationships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("universe_id", sa.Uuid(), sa.ForeignKey("universes.id"), nullable=False),
        sa.Column("continuity_id", sa.Uuid(), nullable=True),
        sa.Column("source_node_id", sa.Uuid(), nullable=False),
        sa.Column("target_node_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["continuity_id", "universe_id"], ["continuities.id", "continuities.universe_id"]
        ),
        sa.ForeignKeyConstraint(
            ["source_node_id", "universe_id"], ["graph_nodes.id", "graph_nodes.universe_id"]
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id", "universe_id"], ["graph_nodes.id", "graph_nodes.universe_id"]
        ),
    )
    for name, columns in [
        ("ix_graph_relationships_universe_id", ["universe_id"]),
        ("ix_relationship_source", ["source_node_id"]),
        ("ix_relationship_target", ["target_node_id"]),
    ]:
        op.create_index(name, "graph_relationships", columns)


def downgrade() -> None:
    op.drop_table("graph_relationships")
    op.drop_table("graph_nodes")
    op.drop_table("continuities")
    op.drop_table("universes")
