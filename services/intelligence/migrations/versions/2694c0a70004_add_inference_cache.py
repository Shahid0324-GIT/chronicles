"""Persist exact-context validated inference reuse.

Revision ID: 2694c0a70004
Revises: 184914a50063
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "2694c0a70004"
down_revision = "184914a50063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_inference_cache",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inference_cache_created", "research_inference_cache", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_inference_cache_created", table_name="research_inference_cache")
    op.drop_table("research_inference_cache")
