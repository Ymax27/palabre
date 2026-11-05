"""Colonnes rep, saison, multiplicateur sur xp_ledger.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "xp_ledger",
        sa.Column("rep", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "xp_ledger",
        sa.Column("saison", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "xp_ledger",
        sa.Column("multiplicateur", sa.SmallInteger(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("xp_ledger", "multiplicateur")
    op.drop_column("xp_ledger", "saison")
    op.drop_column("xp_ledger", "rep")
