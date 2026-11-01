from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.xp import PEER_REASONS


async def current_streak(session: AsyncSession, user: User) -> int:
    stmt = (
        select(XpLedger.created_at)
        .where(
            XpLedger.user_id == user.id,
            XpLedger.reason.in_(PEER_REASONS),
            XpLedger.delta > 0,
        )
        .order_by(XpLedger.created_at.desc())
    )
    stamps = list((await session.scalars(stmt)).all())
    days = {stamp.astimezone(UTC).date() for stamp in stamps}
    if not days:
        return 0
    today = datetime.now(UTC).date()
    cursor: date = today if today in days else today - timedelta(days=1)
    if cursor not in days:
        return 0
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
