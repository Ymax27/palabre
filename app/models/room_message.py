from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.room import Room
    from app.models.user import User


class RoomMessage(Base):
    __tablename__ = "room_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"),
        index=True,
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("room_messages.id", ondelete="SET NULL"),
    )
    body: Mapped[str] = mapped_column(Text)
    needs_help: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    converted_post_id: Mapped[int | None] = mapped_column(
        ForeignKey("posts.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    room: Mapped["Room"] = relationship(back_populates="messages")
    author: Mapped["User"] = relationship()
    parent: Mapped["RoomMessage | None"] = relationship(
        remote_side="RoomMessage.id",
        foreign_keys=[parent_id],
        back_populates="replies",
    )
    replies: Mapped[list["RoomMessage"]] = relationship(
        foreign_keys=[parent_id],
        back_populates="parent",
    )
    converted_post: Mapped["Post | None"] = relationship(
        foreign_keys=[converted_post_id],
        post_update=True,
    )
