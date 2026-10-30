"""Salons, messages, lien de conversion depuis un message.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROOMS: list[tuple[str, str, str | None, str]] = [
    ("pays", "sn", "SN", "Sénégal"),
    ("pays", "ci", "CI", "Côte d'Ivoire"),
    ("pays", "ke", "KE", "Kenya"),
    ("pays", "gh", "GH", "Ghana"),
    ("theme", "python", None, "Python"),
    ("theme", "wave", None, "Wave"),
    ("theme", "aide", None, "Aide"),
]


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("slug", sa.String(length=40), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.UniqueConstraint("slug", name="uq_rooms_slug"),
    )
    op.create_table(
        "room_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "room_id",
            sa.Integer(),
            sa.ForeignKey("rooms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.Integer(),
            sa.ForeignKey("room_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "needs_help",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "converted_post_id",
            sa.Integer(),
            sa.ForeignKey("posts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_room_messages_room_id", "room_messages", ["room_id"])
    op.create_index("ix_room_messages_author_id", "room_messages", ["author_id"])
    op.create_index("ix_room_messages_created_at", "room_messages", ["created_at"])
    op.add_column(
        "posts",
        sa.Column(
            "source_message_id",
            sa.Integer(),
            sa.ForeignKey("room_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    rooms = sa.table(
        "rooms",
        sa.column("kind", sa.String),
        sa.column("slug", sa.String),
        sa.column("country", sa.String),
        sa.column("title", sa.String),
    )
    op.bulk_insert(
        rooms,
        [
            {
                "kind": kind,
                "slug": slug,
                "country": country,
                "title": title,
            }
            for kind, slug, country, title in ROOMS
        ],
    )


def downgrade() -> None:
    op.drop_column("posts", "source_message_id")
    op.drop_index("ix_room_messages_created_at", table_name="room_messages")
    op.drop_index("ix_room_messages_author_id", table_name="room_messages")
    op.drop_index("ix_room_messages_room_id", table_name="room_messages")
    op.drop_table("room_messages")
    op.drop_table("rooms")
