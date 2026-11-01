"""Capitaines de la semaine par pays.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "captain_picks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("week_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("week_start", "country", name="uq_captain_week_country"),
    )
    op.create_index("ix_captain_picks_week_start", "captain_picks", ["week_start"])


def downgrade() -> None:
    op.drop_index("ix_captain_picks_week_start", table_name="captain_picks")
    op.drop_table("captain_picks")
