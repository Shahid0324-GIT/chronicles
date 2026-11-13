"""Separate scoped reader presentations from canonical knowledge.
Revision ID: 30c500000005
Revises: 2694c0a70004
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "30c500000005"
down_revision = "2694c0a70004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_presentations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("universe_id", sa.Uuid(), nullable=False),
        sa.Column("continuity_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("boundary_key", sa.String(64), nullable=False),
        sa.Column("knowledge_revision", sa.String(64), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(64), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("policy_version", sa.String(40), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("grounding_status", sa.String(40), nullable=False),
        sa.Column("provider_metadata", postgresql.JSONB(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["continuity_id", "universe_id"], ["continuities.id", "continuities.universe_id"]
        ),
    )
    op.create_index(
        "ix_knowledge_presentation_scope",
        "knowledge_presentations",
        ["universe_id", "continuity_id", "kind", "boundary_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_presentation_scope", table_name="knowledge_presentations")
    op.drop_table("knowledge_presentations")
