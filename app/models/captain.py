from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import User


class CaptainPick(Base):
    __tablename__ = "captain_picks"
    __table_args__ = (
        UniqueConstraint("week_start", "country", name="uq_captain_week_country"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    country: Mapped[str] = mapped_column(String(2))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    user: Mapped[User] = relationship()
