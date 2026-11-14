"""Retain first observation while revalidating unchanged documents.
Revision ID: 315100000007
Revises: 315100000006
"""

import sqlalchemy as sa
from alembic import op

revision = "315100000007"
down_revision = "315100000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "source_documents", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("UPDATE source_documents SET last_checked_at = retrieved_at")
    op.alter_column("source_documents", "last_checked_at", nullable=False)
    op.create_index(
        "ix_source_documents_checked",
        "source_documents",
        ["universe_id", "continuity_id", "last_checked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_source_documents_checked", table_name="source_documents")
    op.drop_column("source_documents", "last_checked_at")
