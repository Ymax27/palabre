from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.countries import COUNTRY_CODES
from app.models.enums import PostType, TagCategory
from app.models.post import Post
from app.models.room_message import RoomMessage
from app.models.tag import Tag
from app.models.user import User
from app.models.worked_report import WorkedReport
from app.services.rooms import link_converted_post
from app.services.xp import VALIDATOR_MIN_AGE_DAYS, grant_recipe_validated


class RecipeError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def list_recipes(
    session: AsyncSession,
    *,
    tag_slug: str | None = None,
) -> list[Post]:
    stmt = (
        select(Post)
        .where(Post.type == PostType.RECETTE)
        .options(selectinload(Post.tags), selectinload(Post.author))
        .order_by(Post.created_at.desc())
    )
    if tag_slug:
        stmt = stmt.join(Post.tags).where(Tag.slug == tag_slug)
    result = await session.scalars(stmt)
    return list(result.unique().all())


async def get_recipe(session: AsyncSession, recipe_id: int) -> Post | None:
    stmt = (
        select(Post)
        .where(Post.id == recipe_id, Post.type == PostType.RECETTE)
        .options(
            selectinload(Post.tags),
            selectinload(Post.author),
            selectinload(Post.worked_reports).selectinload(WorkedReport.user),
            selectinload(Post.source_message).selectinload(RoomMessage.room),
        )
    )
    return await session.scalar(stmt)


async def create_recipe(
    session: AsyncSession,
    *,
    author: User,
    title: str,
    body: str,
    tag_ids: list[int],
    source_message_id: int | None = None,
) -> Post:
    title_clean = title.strip()
    body_clean = body.strip()
    if not title_clean or not body_clean:
        raise RecipeError("empty")
    if not tag_ids:
        raise RecipeError("need_country")
    tags = list((await session.scalars(select(Tag).where(Tag.id.in_(tag_ids)))).all())
    if not any(tag.category == TagCategory.PAYS for tag in tags):
        raise RecipeError("need_country")
    post = Post(
        type=PostType.RECETTE,
        author_id=author.id,
        title=title_clean,
        body=body_clean,
        tags=tags,
    )
    session.add(post)
    await session.flush()
    await link_converted_post(
        session,
        message_id=source_message_id,
        post=post,
    )
    await session.commit()
    await session.refresh(post)
    return post


def _account_age(user: User) -> timedelta:
    created = user.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return datetime.now(UTC) - created


def worked_counts(recipe: Post) -> dict[str, int]:
    return dict(Counter(report.country for report in recipe.worked_reports))


async def report_worked(
    session: AsyncSession,
    *,
    recipe: Post,
    user: User,
    country: str,
    environment: str,
) -> WorkedReport:
    if recipe.type != PostType.RECETTE:
        raise RecipeError("not_recipe")
    if recipe.author_id == user.id:
        raise RecipeError("own_post")
    country_clean = country.strip().upper()
    environment_clean = environment.strip()[:200]
    if country_clean not in COUNTRY_CODES:
        raise RecipeError("bad_country")
    if not environment_clean:
        raise RecipeError("empty")
    if _account_age(user) < timedelta(days=VALIDATOR_MIN_AGE_DAYS):
        raise RecipeError("too_young")

    existing = await session.scalar(
        select(WorkedReport).where(
            WorkedReport.user_id == user.id,
            WorkedReport.post_id == recipe.id,
        )
    )
    if existing is not None:
        raise RecipeError("duplicate")

    report = WorkedReport(
        post_id=recipe.id,
        user_id=user.id,
        country=country_clean,
        environment=environment_clean,
    )
    session.add(report)
    author = recipe.author
    if author is None:
        author = await session.get(User, recipe.author_id)
    if author is None:
        raise RecipeError("not_recipe")
    await grant_recipe_validated(
        session,
        recipe=recipe,
        validator=user,
        author=author,
    )
    await session.commit()
    await session.refresh(report)
    return report
