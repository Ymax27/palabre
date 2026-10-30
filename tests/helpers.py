import re

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth import request_magic_link


def csrf_from(html: str) -> str:
    match = re.search(r'name="csrf" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


async def login_client(
    client: AsyncClient,
    session: AsyncSession,
    user: User,
) -> None:
    token = await request_magic_link(session, email=user.email, ip="127.0.0.1")
    assert token is not None
    response = await client.get(
        f"/auth/magic?token={token}",
        follow_redirects=True,
    )
    assert response.status_code == 200
