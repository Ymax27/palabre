from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bus import get_redis
from app.models.enums import XpReason
from app.models.user import User
from app.services.ranking import COUPE_ZSET, coupe_standings, refresh_coupe
from app.services.xp import grant_xp

MakeUser = Callable[..., Awaitable[User]]


async def test_refresh_coupe_writes_zset(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    author = await make_user(email="a@test.tld", handle="askia", country="SN")
    actor = await make_user(email="b@test.tld", handle="bakary", country="CI")
    await grant_xp(
        session,
        user=author,
        delta=15,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=actor,
    )
    await session.commit()
    written = await refresh_coupe(session)
    assert written >= 1
    redis = get_redis()
    score = await redis.zscore(COUPE_ZSET, "SN")
    assert score == 15.0
    standings = await coupe_standings(session)
    senegal = next(row for row in standings if row.country == "SN")
    assert senegal.score == 15.0
    assert senegal.rank == 1
    await redis.delete(COUPE_ZSET)
