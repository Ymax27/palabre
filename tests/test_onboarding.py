from collections.abc import Awaitable, Callable

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.models.user import User
from app.models.user_stack import UserStack
from tests.helpers import csrf_from, login_client

MakeUser = Callable[..., Awaitable[User]]


async def test_onboarding_three_posts(
    session: AsyncSession,
    client: AsyncClient,
    make_user: MakeUser,
) -> None:
    user = await make_user(
        email="new@test.tld",
        handle="",
        country="",
        stack="",
    )
    user.handle = None
    user.country = None
    user.stack = None
    await session.commit()
    await login_client(client, session, user)
    page = await client.get("/onboarding")
    assert page.status_code == 200
    csrf = csrf_from(page.text)
    step1 = await client.post(
        "/onboarding",
        data={"csrf": csrf, "step": "1", "handle": "newbie", "country": "SN"},
        follow_redirects=True,
    )
    assert step1.status_code == 200
    assert "stack_id" in step1.text or "Tes stacks" in step1.text
    stack = await session.scalar(select(Tag).where(Tag.category == "stack"))
    assert stack is not None
    csrf2 = csrf_from(step1.text)
    step2 = await client.post(
        "/onboarding",
        data={"csrf": csrf2, "step": "2", "stack_id": str(stack.id)},
        follow_redirects=True,
    )
    assert step2.status_code == 200
    csrf3 = csrf_from(step2.text)
    step3 = await client.post(
        "/onboarding",
        data={"csrf": csrf3, "step": "3", "locale": "en"},
        follow_redirects=True,
    )
    assert step3.status_code == 200
    await session.refresh(user)
    assert user.handle == "newbie"
    assert user.country == "SN"
    assert user.locale == "en"
    assert user.stack
    stacked = await session.scalar(
        select(UserStack).where(UserStack.user_id == user.id)
    )
    assert stacked is not None
