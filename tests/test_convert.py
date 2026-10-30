import re
from collections.abc import Awaitable, Callable

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room
from app.models.user import User
from tests.helpers import csrf_from, login_client

MakeUser = Callable[..., Awaitable[User]]
MakeRoom = Callable[..., Awaitable[Room]]


async def test_help_converts_to_prefilled_question(
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
    posted = await client.post(
        f"/salons/{room.slug}/messages",
        data={"csrf": csrf, "body": "Le paiement Wave plante hors 2G."},
    )
    assert posted.status_code == 200
    match = re.search(r'id="message-(\d+)"', posted.text)
    assert match is not None
    message_id = match.group(1)
    aide = await client.post(
        f"/salons/{room.slug}/messages/{message_id}/aide",
        data={"csrf": csrf},
    )
    assert aide.status_code == 200
    assert "needs-help" in aide.text
    form = await client.get(
        f"/salons/{room.slug}/messages/{message_id}/convertir?vers=question"
    )
    assert form.status_code == 200
    assert "source_message_id" in form.text
    assert f'value="{message_id}"' in form.text
    assert "Le paiement Wave plante hors 2G." in form.text
