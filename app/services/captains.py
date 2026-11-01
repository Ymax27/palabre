from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.captain import CaptainPick
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.weeks import week_start
from app.services.xp import PEER_REASONS


async def is_current_captain(session: AsyncSession, user: User) -> bool:
    if user.country is None:
        return False
    start = week_start()
    pick = await session.scalar(
        select(CaptainPick).where(
            CaptainPick.week_start == start,
            CaptainPick.country == user.country,
            CaptainPick.user_id == user.id,
        )
    )
    return pick is not None


async def pick_weekly_captains(session: AsyncSession) -> int:
    next_week = week_start() + timedelta(days=7)
    prev_start = next_week - timedelta(days=7)
    prev_end = next_week - timedelta(microseconds=1)
    existing = await session.scalar(
        select(func.count())
        .select_from(CaptainPick)
        .where(CaptainPick.week_start == next_week)
    )
    if existing:
        return 0
    stmt = (
        select(
            User.country,
            User.id,
            func.sum(XpLedger.delta).label("xp"),
        )
        .join(XpLedger, XpLedger.user_id == User.id)
        .where(
            User.country.is_not(None),
            XpLedger.reason.in_(PEER_REASONS),
            XpLedger.created_at >= prev_start,
            XpLedger.created_at <= prev_end,
        )
        .group_by(User.country, User.id)
    )
    rows = (await session.execute(stmt)).all()
    best: dict[str, tuple[int, int]] = {}
    for country, user_id, xp in rows:
        if country is None:
            continue
        code = str(country)
        score = int(xp or 0)
        current = best.get(code)
        if current is None or score > current[1]:
            best[code] = (int(user_id), score)
    for code, (user_id, _xp) in best.items():
        session.add(CaptainPick(week_start=next_week, country=code, user_id=user_id))
    await session.commit()
    return len(best)
