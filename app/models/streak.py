from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Streak(Base):
    __tablename__ = "streaks"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    days: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    freeze_week: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_day: Mapped[date | None] = mapped_column(Date)
