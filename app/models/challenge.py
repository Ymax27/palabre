from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.tag import Tag


class Challenge(Base):
    __tablename__ = "defis"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    podium_awarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    tags: Mapped[list["Tag"]] = relationship(
        secondary="challenge_tags",
        back_populates="challenges",
    )
    posts: Mapped[list["Post"]] = relationship(back_populates="challenge")


class ChallengeTag(Base):
    __tablename__ = "challenge_tags"

    challenge_id: Mapped[int] = mapped_column(
        ForeignKey("defis.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
