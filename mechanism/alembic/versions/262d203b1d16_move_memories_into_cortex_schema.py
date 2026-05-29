"""move memories into cortex schema

Revision ID: 262d203b1d16
Revises: 9b0c9c868756
Create Date: 2026-05-29 12:21:01.825331

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "262d203b1d16"
down_revision: str | Sequence[str] | None = "9b0c9c868756"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Move public.memories into the cortex schema.

    Indexes and the content_tsv trigger travel with the table. The trigger
    function memories_tsv_trigger() stays in public and resolves via the
    connection search_path (public, extensions).
    """
    op.execute("ALTER TABLE public.memories SET SCHEMA cortex")


def downgrade() -> None:
    """Move cortex.memories back into public."""
    op.execute("ALTER TABLE cortex.memories SET SCHEMA public")
