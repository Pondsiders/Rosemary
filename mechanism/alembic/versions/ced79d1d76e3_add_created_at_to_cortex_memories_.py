"""add created_at to cortex.memories backfilled from metadata

Revision ID: ced79d1d76e3
Revises: 1c388babb3a5
Create Date: 2026-05-29 12:21:02.302768

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ced79d1d76e3"
down_revision: str | Sequence[str] | None = "1c388babb3a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add cortex.memories.created_at, backfilled from metadata->>'created_at'.

    Every existing row carries an ISO-8601 timestamp under
    metadata->>'created_at' (verified 100% coverage), so the backfill is
    total and the column can be made NOT NULL. New rows get created_at from
    the store_memory tool, which supplies it explicitly.
    """
    op.execute("ALTER TABLE cortex.memories ADD COLUMN created_at timestamptz")
    op.execute("UPDATE cortex.memories SET created_at = (metadata->>'created_at')::timestamptz")
    op.execute("ALTER TABLE cortex.memories ALTER COLUMN created_at SET NOT NULL")
    op.execute("CREATE INDEX memories_created_at_idx ON cortex.memories (created_at)")


def downgrade() -> None:
    """Drop created_at. The data remains recoverable from metadata->>'created_at'."""
    op.execute("DROP INDEX cortex.memories_created_at_idx")
    op.execute("ALTER TABLE cortex.memories DROP COLUMN created_at")
