from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.captain import CaptainPick
from app.models.enums import PostType
from app.models.post import Post
from app.models.user import User
from app.services.weeks import week_start

ELIGIBLE = frozenset({PostType.ANSWER, PostType.RECETTE})


class CaptainError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def is_current_captain(session: AsyncSession, user: User) -> bool:
    pick = await session.scalar(
        select(CaptainPick).where(
            CaptainPick.week_start == week_start(),
            CaptainPick.user_id == user.id,
        )
    )
    return pick is not None


async def is_designated_post(session: AsyncSession, post: Post) -> bool:
    pick = await session.scalar(
        select(CaptainPick).where(
            CaptainPick.week_start == week_start(),
            CaptainPick.user_id == post.author_id,
            CaptainPick.post_id == post.id,
        )
    )
    return pick is not None


async def designate(
    session: AsyncSession,
    *,
    user: User,
    post: Post,
) -> CaptainPick:
    if post.author_id != user.id:
        raise CaptainError("not_author")
    if post.type not in ELIGIBLE:
        raise CaptainError("bad_type")
    start = week_start()
    existing = await session.scalar(
        select(CaptainPick).where(
            CaptainPick.week_start == start,
            CaptainPick.user_id == user.id,
        )
    )
    if existing is not None:
        raise CaptainError("already")
    pick = CaptainPick(
        week_start=start,
        country=user.country or "",
        user_id=user.id,
        post_id=post.id,
    )
    session.add(pick)
    await session.commit()
    return pick


async def pick_weekly_captains(_session: AsyncSession) -> int:
    return 0
