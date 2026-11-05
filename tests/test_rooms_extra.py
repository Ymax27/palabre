from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message_reaction import MessageReaction
from app.models.post_helper import PostHelper
from app.models.report import Report
from app.models.room import Room
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.qa import create_question
from app.services.rooms import post_message
from tests.helpers import context_tag_ids, csrf_from, login_client

MakeUser = Callable[..., Awaitable[User]]
MakeRoom = Callable[..., Awaitable[Room]]


async def test_chat_writes_no_ledger(
    session: AsyncSession,
    make_user: MakeUser,
    make_room: MakeRoom,
) -> None:
    user = await make_user(email="a@test.tld", handle="askia")
    room = await make_room()
    await post_message(session, room=room, author=user, body="Salut sans XP")
    count = await session.scalar(select(func.count()).select_from(XpLedger))
    assert int(count or 0) == 0


async def test_new_account_cannot_post_links(
    session: AsyncSession,
    make_user: MakeUser,
    make_room: MakeRoom,
) -> None:
    user = await make_user(email="a@test.tld", handle="askia")
    room = await make_room()
    try:
        await post_message(
            session,
            room=room,
            author=user,
            body="Voir https://example.com",
        )
        raise AssertionError("links allowed")
    except Exception as exc:
        assert getattr(exc, "code", "") == "no_links"


async def test_old_account_can_post_links(
    session: AsyncSession,
    make_user: MakeUser,
    make_room: MakeRoom,
) -> None:
    old = datetime.now(UTC) - timedelta(hours=25)
    user = await make_user(email="a@test.tld", handle="askia", created_at=old)
    room = await make_room()
    message = await post_message(
        session,
        room=room,
        author=user,
        body="Voir https://example.com",
    )
    assert message.id is not None


async def test_react_and_report(
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
        data={"csrf": csrf, "body": "Timeout Wave hors 2G."},
    )
    assert posted.status_code == 200
    from re import search

    match = search(r'id="message-(\d+)"', posted.text)
    assert match is not None
    message_id = match.group(1)
    reacted = await client.post(
        f"/salons/{room.slug}/messages/{message_id}/react",
        data={"csrf": csrf, "kind": "✅"},
    )
    assert reacted.status_code == 200
    count = await session.scalar(select(func.count()).select_from(MessageReaction))
    assert int(count or 0) == 1
    reported = await client.post(
        f"/salons/{room.slug}/messages/{message_id}/signaler",
        data={"csrf": csrf, "reason": "spam"},
        follow_redirects=False,
    )
    assert reported.status_code == 303
    reports = await session.scalar(select(func.count()).select_from(Report))
    assert int(reports or 0) == 1


async def test_convert_writes_helpers(
    session: AsyncSession,
    make_user: MakeUser,
    make_room: MakeRoom,
) -> None:
    asker = await make_user(email="a@test.tld", handle="askia")
    helper = await make_user(email="b@test.tld", handle="bakary", country="CI")
    room = await make_room()
    root = await post_message(session, room=room, author=asker, body="Wave plante")
    await post_message(
        session,
        room=room,
        author=helper,
        body="Essaie 15 s",
        parent_id=root.id,
    )
    question = await create_question(
        session,
        author=asker,
        title="Wave plante",
        body="Wave plante",
        tag_ids=await context_tag_ids(session),
        source_message_id=root.id,
    )
    helpers = list(
        (
            await session.scalars(
                select(PostHelper).where(PostHelper.post_id == question.id)
            )
        ).all()
    )
    assert {row.user_id for row in helpers} == {helper.id}
