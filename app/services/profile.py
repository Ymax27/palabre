from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.countries import AFRICAN_COUNTRIES
from app.models.badge import UserBadge
from app.models.enums import PostType
from app.models.post import Post
from app.models.user import User
from app.services.badges import list_user_badges
from app.services.captains import is_current_captain
from app.services.streaks import current_streak
from app.services.xp import (
    can_edit,
    can_moderate,
    rep_progress,
    reputation_level,
    total_rep,
    total_xp,
)

_COUNTRY_LABELS = dict(AFRICAN_COUNTRIES)


@dataclass(frozen=True)
class PublicProfile:
    user: User
    xp: int
    rep: int
    level_key: str
    progress: float
    can_edit: bool
    can_moderate: bool
    country_label: str
    questions: list[Post]
    answers: list[Post]
    recipes: list[Post]
    is_captain: bool
    streak: int
    badges: list[UserBadge]


async def get_public_profile(
    session: AsyncSession,
    handle: str,
) -> PublicProfile | None:
    user = await session.scalar(select(User).where(User.handle == handle))
    if user is None:
        return None
    xp = await total_xp(session, user)
    rep = await total_rep(session, user)
    posts = list(
        (
            await session.scalars(
                select(Post)
                .where(Post.author_id == user.id)
                .options(selectinload(Post.tags), selectinload(Post.parent))
                .order_by(Post.created_at.desc())
            )
        ).all()
    )
    questions = [post for post in posts if post.type == PostType.QUESTION]
    answers = [post for post in posts if post.type == PostType.ANSWER]
    recipes = [post for post in posts if post.type == PostType.RECETTE]
    country = user.country or ""
    return PublicProfile(
        user=user,
        xp=xp,
        rep=rep,
        level_key=reputation_level(rep),
        progress=rep_progress(rep),
        can_edit=can_edit(rep),
        can_moderate=can_moderate(rep),
        country_label=_COUNTRY_LABELS.get(country, country),
        questions=questions,
        answers=answers,
        recipes=recipes,
        is_captain=await is_current_captain(session, user),
        streak=await current_streak(session, user),
        badges=await list_user_badges(session, user),
    )
