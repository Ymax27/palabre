from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ReactionKind, XpReason
from app.models.reaction import Reaction
from app.models.streak import Streak
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.weeks import week_start


def _today() -> date:
    return datetime.now(UTC).date()


async def _active_day(session: AsyncSession, user: User, day: date) -> bool:
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    end = start + timedelta(days=1)
    ledger = await session.scalar(
        select(XpLedger.id)
        .where(
            XpLedger.user_id == user.id,
            XpLedger.reason.in_(
                {
                    XpReason.ANSWER_ACCEPTED,
                    XpReason.RECIPE_VALIDATED_AUTHOR,
                    XpReason.RECIPE_VALIDATED_VALIDATOR,
                }
            ),
            XpLedger.created_at >= start,
            XpLedger.created_at < end,
        )
        .limit(1)
    )
    if ledger is not None:
        return True
    utile = await session.scalar(
        select(Reaction.id)
        .where(
            Reaction.user_id == user.id,
            Reaction.kind == ReactionKind.UTILE,
            Reaction.created_at >= start,
            Reaction.created_at < end,
        )
        .limit(1)
    )
    return utile is not None


async def _row(session: AsyncSession, user: User) -> Streak:
    row = await session.get(Streak, user.id)
    if row is not None:
        return row
    row = Streak(user_id=user.id, days=0)
    session.add(row)
    await session.flush()
    return row


async def current_streak(session: AsyncSession, user: User) -> int:
    row = await session.get(Streak, user.id)
    return row.days if row is not None else 0


async def refresh_streak(session: AsyncSession, user: User) -> Streak:
    row = await _row(session, user)
    today = _today()
    if await _active_day(session, user, today):
        if row.last_day == today:
            return row
        if row.last_day == today - timedelta(days=1):
            row.days += 1
        elif row.last_day is None:
            row.days = 1
        else:
            gap = (today - row.last_day).days
            freeze_week = week_start()
            if gap == 2 and row.freeze_week != freeze_week:
                row.freeze_week = freeze_week
                row.days += 1
            else:
                row.days = 1
        row.last_day = today
        await session.commit()
        return row
    return row


async def refresh_all_streaks(session: AsyncSession) -> int:
    users = list((await session.scalars(select(User))).all())
    for user in users:
        await refresh_streak(session, user)
    return len(users)
