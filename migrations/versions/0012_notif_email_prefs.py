"""Préférences email par type de notification.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLS = (
    "email_answer",
    "email_accepted",
    "email_worked",
    "email_reminder",
    "email_weekly",
)


def upgrade() -> None:
    for name in _COLS:
        op.add_column(
            "notification_prefs",
            sa.Column(name, sa.Boolean(), server_default=sa.text("true"), nullable=False),
        )


def downgrade() -> None:
    for name in reversed(_COLS):
        op.drop_column("notification_prefs", name)
