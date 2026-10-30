import asyncio
import contextlib
import re
from collections.abc import Awaitable, Callable

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bus import subscribe_room
from app.models.room import Room
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.xp import total_xp
from tests.helpers import csrf_from, login_client

MakeUser = Callable[..., Awaitable[User]]
MakeRoom = Callable[..., Awaitable[Room]]


async def test_sse_delivers_message_without_xp(
    session: AsyncSession,
    client: AsyncClient,
    make_user: MakeUser,
    make_room: MakeRoom,
) -> None:
    user_a = await make_user(email="a@test.tld", handle="askia")
    user_b = await make_user(email="b@test.tld", handle="bakary", country="CI")
    room = await make_room()
    await login_client(client, session, user_a)
    page = await client.get(f"/salons/{room.slug}")
    csrf = csrf_from(page.text)
    payloads: list[str] = []

    async def listen() -> None:
        async for payload in subscribe_room(room.id):
            payloads.append(payload)
            break

    task = asyncio.create_task(listen())
    try:
        await asyncio.sleep(0.4)
        posted = await client.post(
            f"/salons/{room.slug}/messages",
            data={"csrf": csrf, "body": "Timeout **Wave** hors 2G."},
        )
        assert posted.status_code == 200
        assert re.search(r'id="message-\d+"', posted.text)
        await asyncio.wait_for(asyncio.shield(task), timeout=5)
        blob = "\n".join(payloads)
        assert "Wave" in blob
        assert "message-" in blob
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    ledger = await session.scalar(select(func.count()).select_from(XpLedger))
    assert ledger == 0
    assert await total_xp(session, user_a) == 0
    assert await total_xp(session, user_b) == 0
