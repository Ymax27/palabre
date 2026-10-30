from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.countries import AFRICAN_COUNTRIES
from app.models.enums import PostType
from app.models.post import Post
from app.models.user import User
from app.services.xp import reputation_level, total_xp

_COUNTRY_LABELS = dict(AFRICAN_COUNTRIES)

LEVEL_KEYS = ("level_nouveau", "level_membre", "level_pilier", "level_ancien")


@dataclass(frozen=True)
class PublicProfile:
    user: User
    xp: int
    niveau: int
    country_label: str
    questions: list[Post]
    answers: list[Post]
    recipes: list[Post]


async def get_public_profile(
    session: AsyncSession,
    handle: str,
) -> PublicProfile | None:
    user = await session.scalar(select(User).where(User.handle == handle))
    if user is None:
        return None
    xp = await total_xp(session, user)
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
        niveau=reputation_level(xp),
        country_label=_COUNTRY_LABELS.get(country, country),
        questions=questions,
        answers=answers,
        recipes=recipes,
    )
