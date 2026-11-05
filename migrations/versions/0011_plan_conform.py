"""Alignement PLAN : locale, stacks, recettes, salons, séries, badges, capitaine.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("locale", sa.String(length=8), server_default="fr", nullable=False),
    )
    op.create_table(
        "user_stacks",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    for name in ("probleme", "solution", "code", "prerequis", "versions", "limites"):
        op.add_column("posts", sa.Column(name, sa.Text(), nullable=True))
    op.add_column("rooms", sa.Column("question_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="SET NULL"), nullable=True))
    op.add_column("rooms", sa.Column("league_id", sa.Integer(), sa.ForeignKey("leagues.id", ondelete="SET NULL"), nullable=True))
    op.execute("UPDATE rooms SET kind = 'stack' WHERE kind = 'theme' AND slug != 'aide'")
    op.execute("DELETE FROM rooms WHERE slug = 'aide' AND kind = 'theme'")
    op.create_table(
        "message_reactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("room_messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.UniqueConstraint("message_id", "user_id", "kind", name="uq_message_reaction"),
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("room_messages.id", ondelete="CASCADE"), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "post_helpers",
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "streaks",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("freeze_week", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_day", sa.Date(), nullable=True),
    )
    op.create_table(
        "badges",
        sa.Column("slug", sa.String(length=40), primary_key=True),
        sa.Column("label", sa.String(length=80), nullable=False),
    )
    op.execute("INSERT INTO badges (slug, label) VALUES ('teste_en_prod', 'testé en prod')")
    op.add_column("captain_picks", sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=True))
    op.drop_constraint("uq_captain_week_country", "captain_picks", type_="unique")
    op.create_unique_constraint("uq_captain_user_week", "captain_picks", ["user_id", "week_start"])
    op.rename_table("challenges", "defis")


def downgrade() -> None:
    op.rename_table("defis", "challenges")
    op.drop_constraint("uq_captain_user_week", "captain_picks", type_="unique")
    op.create_unique_constraint("uq_captain_week_country", "captain_picks", ["week_start", "country"])
    op.drop_column("captain_picks", "post_id")
    op.drop_table("badges")
    op.drop_table("streaks")
    op.drop_table("post_helpers")
    op.drop_table("reports")
    op.drop_table("message_reactions")
    op.drop_column("rooms", "league_id")
    op.drop_column("rooms", "question_id")
    for name in ("limites", "versions", "prerequis", "code", "solution", "probleme"):
        op.drop_column("posts", name)
    op.drop_table("user_stacks")
    op.drop_column("users", "locale")
