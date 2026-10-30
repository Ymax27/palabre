from typing import TYPE_CHECKING

from sqlalchemy import String
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

    messages: Mapped[list["RoomMessage"]] = relationship(back_populates="room")
