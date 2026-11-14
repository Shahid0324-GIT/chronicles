"""Persist source strategy and unfinished research leads.
Revision ID: 315100000006
Revises: 30c500000005
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "315100000006"
down_revision = "30c500000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "universe_research_profiles",
        sa.Column("universe_id", sa.Uuid(), sa.ForeignKey("universes.id"), primary_key=True),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "research_leads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("universe_id", sa.Uuid(), nullable=False),
        sa.Column("continuity_id", sa.Uuid(), nullable=False),
        sa.Column("boundary_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["continuity_id", "universe_id"], ["continuities.id", "continuities.universe_id"]
        ),
    )
    op.create_index(
        "ix_research_lead_scope",
        "research_leads",
        ["universe_id", "continuity_id", "boundary_key", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_research_lead_scope", table_name="research_leads")
    op.drop_table("research_leads")
    op.drop_table("universe_research_profiles")
