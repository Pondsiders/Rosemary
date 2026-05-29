"""move sage tables into sage schema

Revision ID: 1c388babb3a5
Revises: 262d203b1d16
Create Date: 2026-05-29 12:21:02.062399

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1c388babb3a5"
down_revision: str | Sequence[str] | None = "262d203b1d16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Move the Sage archive into the sage schema, dropping the sage_ prefix.

    The sage_messages -> sage_conversations foreign key and the HNSW/GIN
    indexes are preserved across SET SCHEMA and RENAME (they track table
    identity, not name).
    """
    op.execute("ALTER TABLE public.sage_conversations SET SCHEMA sage")
    op.execute("ALTER TABLE sage.sage_conversations RENAME TO conversations")
    op.execute("ALTER TABLE public.sage_messages SET SCHEMA sage")
    op.execute("ALTER TABLE sage.sage_messages RENAME TO messages")


def downgrade() -> None:
    """Restore the Sage tables to public with their original sage_ prefix."""
    op.execute("ALTER TABLE sage.messages RENAME TO sage_messages")
    op.execute("ALTER TABLE sage.sage_messages SET SCHEMA public")
    op.execute("ALTER TABLE sage.conversations RENAME TO sage_conversations")
    op.execute("ALTER TABLE sage.sage_conversations SET SCHEMA public")
