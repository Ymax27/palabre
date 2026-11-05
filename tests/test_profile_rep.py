from collections.abc import Awaitable, Callable

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import XpReason
from app.models.user import User
from app.services.xp import grant_xp
from tests.helpers import login_client

MakeUser = Callable[..., Awaitable[User]]


async def test_profile_shows_level_and_ring(
    session: AsyncSession,
    client: AsyncClient,
    make_user: MakeUser,
) -> None:
    user = await make_user(email="a@test.tld", handle="askia", country="SN")
    actor = await make_user(email="b@test.tld", handle="bakary", country="CI")
    await grant_xp(
        session,
        user=user,
        delta=15,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=actor,
    )
    await session.commit()
    await login_client(client, session, user)
    page = await client.get("/u/askia")
    assert page.status_code == 200
    assert "avatar-ring" in page.text
    assert "Membre" in page.text
    assert "15 rep" in page.text or "15" in page.text
