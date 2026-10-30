from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Computed, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.reaction import Reaction
    from app.models.tag import Tag
    from app.models.user import User
    from app.models.worked_report import WorkedReport


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(20))
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20),
        default="open",
        server_default="open",
    )
    accepted_answer_id: Mapped[int | None] = mapped_column(
        ForeignKey("posts.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    # Exception AGENTS.md : generated FTS column, voir migration 0002.
    search_tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(body, ''))",
            persisted=True,
        ),
        nullable=True,
    )

    author: Mapped["User"] = relationship(
        back_populates="posts",
        foreign_keys=[author_id],
    )
    parent: Mapped["Post | None"] = relationship(
        remote_side="Post.id",
        foreign_keys=[parent_id],
        back_populates="answers",
    )
    answers: Mapped[list["Post"]] = relationship(
        foreign_keys=[parent_id],
        back_populates="parent",
    )
    accepted_answer: Mapped["Post | None"] = relationship(
        remote_side="Post.id",
        foreign_keys=[accepted_answer_id],
        post_update=True,
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="post_tags",
        back_populates="posts",
    )
    reactions: Mapped[list["Reaction"]] = relationship(back_populates="post")
    worked_reports: Mapped[list["WorkedReport"]] = relationship(back_populates="post")
