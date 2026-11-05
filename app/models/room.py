from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.room_message import RoomMessage


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))
    slug: Mapped[str] = mapped_column(String(40), unique=True)
    country: Mapped[str | None] = mapped_column(String(2))
    title: Mapped[str] = mapped_column(String(80))
    question_id: Mapped[int | None] = mapped_column(
        ForeignKey("posts.id", ondelete="SET NULL"),
    )
    league_id: Mapped[int | None] = mapped_column(
        ForeignKey("leagues.id", ondelete="SET NULL"),
    )

    messages: Mapped[list["RoomMessage"]] = relationship(back_populates="room")
