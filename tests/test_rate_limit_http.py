from collections.abc import Awaitable, Callable

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.models.room import Room
from app.models.user import User
from tests.helpers import csrf_from, login_client

MakeUser = Callable[..., Awaitable[User]]
MakeRoom = Callable[..., Awaitable[Room]]


async def test_room_messages_return_429_over_limit(
    session: AsyncSession,
    client: AsyncClient,
    make_user: MakeUser,
    make_room: MakeRoom,
) -> None:
    user = await make_user(email="a@test.tld", handle="askia")
    room = await make_room()
    await login_client(client, session, user)
    page = await client.get(f"/salons/{room.slug}")
    csrf = csrf_from(page.text)
    for index in range(20):
        response = await client.post(
            f"/salons/{room.slug}/messages",
            data={"csrf": csrf, "body": f"Message {index}"},
        )
        assert response.status_code == 200
    blocked = await client.post(
        f"/salons/{room.slug}/messages",
        data={"csrf": csrf, "body": "Encore un"},
    )
    assert blocked.status_code == 429
    assert t("rate_limited") in blocked.text
