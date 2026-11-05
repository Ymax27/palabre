from collections.abc import Awaitable, Callable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import XpReason
from app.models.room import Room
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.leagues import (
    SEASON_START,
    create_league,
    join_league,
    league_standings,
)

MakeUser = Callable[..., Awaitable[User]]


async def test_create_join_and_season_order(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    owner = await make_user(email="a@test.tld", handle="askia", country="SN")
    member = await make_user(email="b@test.tld", handle="bakary", country="CI")
    extra = await make_user(email="c@test.tld", handle="amina", country="KE")
    actor = await make_user(email="d@test.tld", handle="yaw", country="GH")

    league = await create_league(session, owner=owner, name="Baobab")
    assert league.invite_code
    room = await session.scalar(select(Room).where(Room.league_id == league.id))
    assert room is not None
    assert room.kind == "ligue"
    ledger = await session.scalar(select(func.count()).select_from(XpLedger))
    assert int(ledger or 0) == 0
    joined = await join_league(session, user=member, code=league.invite_code)
    assert joined.id == league.id
    await join_league(session, user=extra, code=league.invite_code)

    session.add(
        XpLedger(
            user_id=member.id,
            delta=30,
            reason=XpReason.ANSWER_ACCEPTED,
            source_user_id=actor.id,
            created_at=SEASON_START,
        )
    )
    session.add(
        XpLedger(
            user_id=owner.id,
            delta=10,
            reason=XpReason.ANSWER_ACCEPTED,
            source_user_id=actor.id,
            created_at=SEASON_START,
        )
    )
    await session.commit()

    standings = await league_standings(session, league)
    handles = [row.user.handle for row in standings]
    assert handles[0] == "bakary"
    assert standings[0].xp == 30
    assert handles[1] == "askia"
    assert standings[1].xp == 10
    assert handles[2] == "amina"
    assert standings[2].xp == 0
