"""Défis de la semaine, participation des posts, flag admin.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        "challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("podium_awarded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_challenges_starts_at", "challenges", ["starts_at"])
    op.create_index("ix_challenges_ends_at", "challenges", ["ends_at"])
    op.create_table(
        "challenge_tags",
        sa.Column(
            "challenge_id",
            sa.Integer(),
            sa.ForeignKey("challenges.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.add_column(
        "posts",
        sa.Column(
            "challenge_id",
            sa.Integer(),
            sa.ForeignKey("challenges.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_posts_challenge_id", "posts", ["challenge_id"])


def downgrade() -> None:
    op.drop_index("ix_posts_challenge_id", table_name="posts")
    op.drop_column("posts", "challenge_id")
    op.drop_table("challenge_tags")
    op.drop_index("ix_challenges_ends_at", table_name="challenges")
    op.drop_index("ix_challenges_starts_at", table_name="challenges")
    op.drop_table("challenges")
    op.drop_column("users", "is_admin")
