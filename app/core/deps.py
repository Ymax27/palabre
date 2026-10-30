from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.user import User

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    request: Request,
    session: SessionDep,
) -> User | None:
    raw = request.session.get("uid")
    if not isinstance(raw, int):
        return None
    return await session.get(User, raw)


CurrentUser = Annotated[User | None, Depends(get_current_user)]


async def require_login(user: CurrentUser) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/connexion"},
        )
    return user


LoginUser = Annotated[User, Depends(require_login)]


def is_onboarded(user: User) -> bool:
    return bool(user.handle and user.country and user.stack)
