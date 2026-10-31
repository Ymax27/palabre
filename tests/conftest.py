import os

os.environ["DEBUG"] = "true"

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal, engine
from app.core.limiter import limiter
from app.core.rate_limit import reset as reset_rate_limit
from app.main import app
from app.models.room import Room
from app.models.user import User

MakeUser = Callable[..., Awaitable[User]]
MakeRoom = Callable[..., Awaitable[Room]]


@pytest.fixture(scope="session", autouse=True)
def _force_debug_mode() -> None:
    from app.core.config import settings

    settings.debug = True


@pytest.fixture(autouse=True)
async def clean_db() -> AsyncIterator[None]:
    reset_rate_limit()
    limiter.reset()
    async with SessionLocal() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE magic_links, reactions, worked_reports, "
                "xp_ledger, post_tags, posts, room_messages, rooms, users "
                "RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
    yield


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as db_session:
        yield db_session


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture(scope="session", autouse=True)
async def _dispose_engine() -> AsyncIterator[None]:
    yield
    await engine.dispose()


@pytest.fixture
def make_user(session: AsyncSession) -> MakeUser:
    async def _make(
        *,
        email: str,
        handle: str,
        country: str = "SN",
        stack: str = "Python",
        created_at: datetime | None = None,
    ) -> User:
        user = User(
            email=email,
            handle=handle,
            country=country,
            stack=stack,
            created_at=created_at or datetime.now(UTC),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    return _make


@pytest.fixture
def make_room(session: AsyncSession) -> MakeRoom:
    async def _make(
        *,
        slug: str = "wave",
        title: str = "Wave",
        kind: str = "theme",
        country: str | None = None,
    ) -> Room:
        room = Room(kind=kind, slug=slug, title=title, country=country)
        session.add(room)
        await session.commit()
        await session.refresh(room)
        return room

    return _make
