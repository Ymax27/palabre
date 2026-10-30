from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PostType
from app.models.post import Post
from app.models.user import User
from app.seed import SENTINEL_EMAIL, seed
from app.services.ranking import coupe_standings


async def test_seed_fills_feed_and_coupe(session: AsyncSession) -> None:
    created = await seed(session)
    assert created is True
    users = await session.scalar(select(func.count()).select_from(User))
    questions = await session.scalar(
        select(func.count()).select_from(Post).where(Post.type == PostType.QUESTION)
    )
    recipes = await session.scalar(
        select(func.count()).select_from(Post).where(Post.type == PostType.RECETTE)
    )
    assert int(users or 0) >= 4
    assert int(questions or 0) >= 10
    assert int(recipes or 0) >= 5
    sentinel = await session.scalar(select(User).where(User.email == SENTINEL_EMAIL))
    assert sentinel is not None
    standings = await coupe_standings(session)
    assert len(standings) >= 2

    again = await seed(session)
    assert again is False
    users_after = await session.scalar(select(func.count()).select_from(User))
    assert users_after == users
