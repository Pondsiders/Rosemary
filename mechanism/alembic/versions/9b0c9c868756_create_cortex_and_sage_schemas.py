"""create cortex and sage schemas

Revision ID: 9b0c9c868756
Revises: 5cf9fe952732
Create Date: 2026-05-29 12:21:01.576757

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b0c9c868756"
down_revision: str | Sequence[str] | None = "5cf9fe952732"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the cortex and sage namespaces."""
    op.execute("CREATE SCHEMA cortex")
    op.execute("CREATE SCHEMA sage")


def downgrade() -> None:
    """Drop the cortex and sage namespaces (empty by this point in the downgrade)."""
    op.execute("DROP SCHEMA sage")
    op.execute("DROP SCHEMA cortex")
