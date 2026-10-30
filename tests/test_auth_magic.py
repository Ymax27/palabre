from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.magic_link import MagicLink
from app.models.user import User
from app.services.auth import MagicLinkError, consume_magic_link, request_magic_link

MakeUser = Callable[..., Awaitable[User]]


async def test_expired_token_refused(session: AsyncSession) -> None:
    token = await request_magic_link(session, email="old@test.tld", ip="127.0.0.1")
    assert token is not None
    link = await session.scalar(select(MagicLink))
    assert link is not None
    link.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await session.commit()
    try:
        await consume_magic_link(session, token)
        raise AssertionError("expected MagicLinkError")
    except MagicLinkError as exc:
        assert exc.code == "expired"


async def test_reused_token_refused(session: AsyncSession) -> None:
    token = await request_magic_link(session, email="once@test.tld", ip="127.0.0.1")
    assert token is not None
    user = await consume_magic_link(session, token)
    assert user.email == "once@test.tld"
    try:
        await consume_magic_link(session, token)
        raise AssertionError("expected MagicLinkError")
    except MagicLinkError as exc:
        assert exc.code == "reused"


async def test_request_creates_link_row(
    session: AsyncSession, make_user: MakeUser
) -> None:
    await make_user(email="x@test.tld", handle="xray")
    token = await request_magic_link(session, email="x@test.tld", ip="10.0.0.1")
    assert token is not None
    row = await session.scalar(select(MagicLink).where(MagicLink.email == "x@test.tld"))
    assert row is not None
    assert row.consumed_at is None
