from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

SYSTEM_EMAIL = "palabre@system.local"
SYSTEM_HANDLE = "palabre"


async def get_system_user(session: AsyncSession) -> User:
    user = await session.scalar(select(User).where(User.email == SYSTEM_EMAIL))
    if user is not None:
        return user
    user = User(
        email=SYSTEM_EMAIL,
        handle=SYSTEM_HANDLE,
        country=None,
        stack=None,
    )
    session.add(user)
    await session.flush()
    return user
