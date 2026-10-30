from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.xp_ledger import XpLedger


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    handle: Mapped[str | None] = mapped_column(String(40), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    github_id: Mapped[str | None] = mapped_column(String(32), unique=True)
    country: Mapped[str | None] = mapped_column(String(2))
    stack: Mapped[str | None] = mapped_column(String(80))
    niveau: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    posts: Mapped[list["Post"]] = relationship(back_populates="author")
    xp_entries: Mapped[list["XpLedger"]] = relationship(
        back_populates="user",
        foreign_keys="XpLedger.user_id",
    )
