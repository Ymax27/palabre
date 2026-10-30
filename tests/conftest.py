from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal, engine
from app.core.rate_limit import reset as reset_rate_limit
from app.main import app
from app.models.user import User

MakeUser = Callable[..., Awaitable[User]]


@pytest.fixture(autouse=True)
async def clean_db() -> AsyncIterator[None]:
    reset_rate_limit()
    async with SessionLocal() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE magic_links, reactions, worked_reports, "
                "xp_ledger, post_tags, posts, users RESTART IDENTITY CASCADE"
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
