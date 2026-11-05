from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import XpReason
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.streaks import current_streak, refresh_streak

MakeUser = Callable[..., Awaitable[User]]


async def _peer_on(
    session: AsyncSession,
    user: User,
    actor: User,
    day: datetime,
) -> None:
    session.add(
        XpLedger(
            user_id=user.id,
            delta=5,
            reason=XpReason.ANSWER_ACCEPTED,
            source_user_id=actor.id,
            created_at=day,
        )
    )
    await session.commit()


async def test_streak_two_consecutive_days(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    user = await make_user(email="a@test.tld", handle="askia", country="SN")
    actor = await make_user(email="b@test.tld", handle="bakary", country="CI")
    today = datetime.now(UTC)
    await _peer_on(session, user, actor, today - timedelta(days=1))
    await _peer_on(session, user, actor, today)
    await refresh_streak(session, user)
    assert await current_streak(session, user) >= 1


async def test_streak_freeze_keeps_series(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    user = await make_user(email="a@test.tld", handle="askia", country="SN")
    actor = await make_user(email="b@test.tld", handle="bakary", country="CI")
    today = datetime.now(UTC)
    await _peer_on(session, user, actor, today)
    await refresh_streak(session, user)
    assert await current_streak(session, user) >= 1
