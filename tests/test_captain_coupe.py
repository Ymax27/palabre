from collections.abc import Awaitable, Callable

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.captain import CaptainPick
from app.models.enums import XpReason
from app.models.user import User
from app.services.ranking import coupe_standings
from app.services.weeks import week_start
from app.services.xp import grant_xp, total_xp

MakeUser = Callable[..., Awaitable[User]]


async def test_captain_doubles_coupe_not_total(
    session: AsyncSession,
    client: AsyncClient,
    make_user: MakeUser,
) -> None:
    captain = await make_user(email="c@test.tld", handle="esther", country="CM")
    actor = await make_user(email="a@test.tld", handle="askia", country="SN")
    awarded = await grant_xp(
        session,
        user=captain,
        delta=15,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=actor,
    )
    assert awarded == 15
    session.add(
        CaptainPick(
            week_start=week_start(),
            country="CM",
            user_id=captain.id,
        )
    )
    await session.commit()

    assert await total_xp(session, captain) == 15
    standings = await coupe_standings(session)
    cameroon = next(row for row in standings if row.country == "CM")
    assert cameroon.score == 30.0
    assert cameroon.captain_handle == "esther"
    assert len(cameroon.form) == 5

    page = await client.get("/coupe")
    assert page.status_code == 200
    assert "30.0" in page.text
    assert "esther" in page.text
    assert ">C<" in page.text or "C</span>" in page.text
