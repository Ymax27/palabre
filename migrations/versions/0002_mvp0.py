"""Modèles MVP-0 : users, posts, tags, reactions, ledger, magic links.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30

Index pg_trgm et full-text : exception documentée à AGENTS.md (pas de SQL métier).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COUNTRY_TAGS: list[tuple[str, str]] = [
    ("dz", "Algérie"),
    ("ao", "Angola"),
    ("bj", "Bénin"),
    ("bw", "Botswana"),
    ("bf", "Burkina Faso"),
    ("bi", "Burundi"),
    ("cv", "Cap-Vert"),
    ("cm", "Cameroun"),
    ("cf", "Centrafrique"),
    ("td", "Tchad"),
    ("km", "Comores"),
    ("cg", "Congo"),
    ("cd", "RD Congo"),
    ("ci", "Côte d'Ivoire"),
    ("dj", "Djibouti"),
    ("eg", "Égypte"),
    ("gq", "Guinée équatoriale"),
    ("er", "Érythrée"),
    ("sz", "Eswatini"),
    ("et", "Éthiopie"),
    ("ga", "Gabon"),
    ("gm", "Gambie"),
    ("gh", "Ghana"),
    ("gn", "Guinée"),
    ("gw", "Guinée-Bissau"),
    ("ke", "Kenya"),
    ("ls", "Lesotho"),
    ("lr", "Liberia"),
    ("ly", "Libye"),
    ("mg", "Madagascar"),
    ("mw", "Malawi"),
    ("ml", "Mali"),
    ("mr", "Mauritanie"),
    ("mu", "Maurice"),
    ("ma", "Maroc"),
    ("mz", "Mozambique"),
    ("na", "Namibie"),
    ("ne", "Niger"),
    ("ng", "Nigeria"),
    ("rw", "Rwanda"),
    ("st", "Sao Tomé-et-Principe"),
    ("sn", "Sénégal"),
    ("sc", "Seychelles"),
    ("sl", "Sierra Leone"),
    ("so", "Somalie"),
    ("za", "Afrique du Sud"),
    ("ss", "Soudan du Sud"),
    ("sd", "Soudan"),
    ("tz", "Tanzanie"),
    ("tg", "Togo"),
    ("tn", "Tunisie"),
    ("ug", "Ouganda"),
    ("zm", "Zambie"),
    ("zw", "Zimbabwe"),
]

PAYMENT_TAGS: list[tuple[str, str]] = [
    ("wave", "Wave"),
    ("orange-money", "Orange Money"),
    ("mtn-momo", "MTN MoMo"),
    ("airtel-money", "Airtel Money"),
    ("cash", "Espèces"),
]

NETWORK_TAGS: list[tuple[str, str]] = [
    ("2g", "2G"),
    ("3g", "3G"),
    ("4g", "4G"),
    ("5g", "5G"),
    ("fibre", "Fibre"),
    ("instable", "Réseau instable"),
    ("satellite", "Satellite"),
]

STACK_TAGS: list[tuple[str, str]] = [
    ("python", "Python"),
    ("javascript", "JavaScript"),
    ("typescript", "TypeScript"),
    ("php", "PHP"),
    ("java", "Java"),
    ("kotlin", "Kotlin"),
    ("go", "Go"),
    ("rust", "Rust"),
    ("dart", "Dart"),
    ("flutter", "Flutter"),
    ("react", "React"),
    ("django", "Django"),
    ("fastapi", "FastAPI"),
    ("laravel", "Laravel"),
    ("android", "Android"),
    ("ios", "iOS"),
]


def upgrade() -> None:
    # Exception AGENTS.md : extension et index full-text / trigram, pas du SQL métier.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("handle", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("stack", sa.String(length=80), nullable=True),
        sa.Column("niveau", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("handle"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.UniqueConstraint("category", "slug", name="uq_tags_category_slug"),
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="open",
        ),
        sa.Column("accepted_answer_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["accepted_answer_id"],
            ["posts.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_posts_author_id", "posts", ["author_id"])
    op.create_index("ix_posts_created_at", "posts", ["created_at"])
    op.create_index("ix_posts_type_created", "posts", ["type", "created_at"])

    op.execute(
        """
        ALTER TABLE posts ADD COLUMN search_tsv tsvector
        GENERATED ALWAYS AS (
            to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(body, ''))
        ) STORED
        """
    )
    op.execute("CREATE INDEX ix_posts_search_tsv ON posts USING GIN (search_tsv)")
    op.execute(
        "CREATE INDEX ix_posts_title_trgm ON posts USING GIN (title gin_trgm_ops)"
    )
    op.execute("CREATE INDEX ix_posts_body_trgm ON posts USING GIN (body gin_trgm_ops)")

    op.create_table(
        "post_tags",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id", "tag_id"),
    )

    op.create_table(
        "reactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="utile"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "post_id", name="uq_reactions_user_post"),
    )
    op.create_index("ix_reactions_user_id", "reactions", ["user_id"])
    op.create_index("ix_reactions_post_id", "reactions", ["post_id"])

    op.create_table(
        "worked_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("environment", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "post_id", name="uq_worked_reports_user_post"),
    )
    op.create_index("ix_worked_reports_post_id", "worked_reports", ["post_id"])
    op.create_index("ix_worked_reports_user_id", "worked_reports", ["user_id"])

    op.create_table(
        "xp_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("source_post_id", sa.Integer(), nullable=True),
        sa.Column("source_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_post_id"], ["posts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_xp_ledger_user_id", "xp_ledger", ["user_id"])
    op.create_index("ix_xp_ledger_created_at", "xp_ledger", ["created_at"])

    op.execute(
        """
        CREATE FUNCTION xp_ledger_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'xp_ledger is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER xp_ledger_no_update
        BEFORE UPDATE OR DELETE ON xp_ledger
        FOR EACH ROW EXECUTE FUNCTION xp_ledger_append_only()
        """
    )

    op.create_table(
        "magic_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_magic_links_email", "magic_links", ["email"])

    tags = sa.table(
        "tags",
        sa.column("category", sa.String),
        sa.column("slug", sa.String),
        sa.column("label", sa.String),
    )

    def _rows(category: str, pairs: list[tuple[str, str]]) -> list[dict[str, str]]:
        return [
            {"category": category, "slug": slug, "label": label}
            for slug, label in pairs
        ]

    rows = (
        _rows("pays", COUNTRY_TAGS)
        + _rows("paiement", PAYMENT_TAGS)
        + _rows("reseau", NETWORK_TAGS)
        + _rows("stack", STACK_TAGS)
    )
    op.bulk_insert(tags, rows)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS xp_ledger_no_update ON xp_ledger")
    op.execute("DROP FUNCTION IF EXISTS xp_ledger_append_only()")
    op.drop_table("magic_links")
    op.drop_table("xp_ledger")
    op.drop_table("worked_reports")
    op.drop_table("reactions")
    op.drop_table("post_tags")
    op.execute("DROP INDEX IF EXISTS ix_posts_body_trgm")
    op.execute("DROP INDEX IF EXISTS ix_posts_title_trgm")
    op.execute("DROP INDEX IF EXISTS ix_posts_search_tsv")
    op.drop_table("posts")
    op.drop_table("tags")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
