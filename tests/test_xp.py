from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PostType, XpReason
from app.models.post import Post
from app.models.user import User
from app.services.xp import (
    AWARDS,
    grant_answer_accepted,
    grant_recipe_validated,
    grant_xp,
    total_xp,
)

MakeUser = Callable[..., Awaitable[User]]


async def _recipe(session: AsyncSession, author_id: int) -> Post:
    post = Post(
        type=PostType.RECETTE,
        author_id=author_id,
        title="Installer Python",
        body="apt install python3",
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return post


async def test_refuse_auto_credit(session: AsyncSession, make_user: MakeUser) -> None:
    user = await make_user(email="a@test.tld", handle="alpha")
    awarded = await grant_xp(
        session,
        user=user,
        delta=15,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=user,
    )
    assert awarded == 0
    assert await total_xp(session, user) == 0


async def test_daily_cap(session: AsyncSession, make_user: MakeUser) -> None:
    author = await make_user(email="a@test.tld", handle="alpha")
    actor = await make_user(email="b@test.tld", handle="beta")
    first = await grant_xp(
        session,
        user=author,
        delta=80,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=actor,
    )
    second = await grant_xp(
        session,
        user=author,
        delta=30,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=actor,
    )
    assert first == 80
    assert second == 20
    assert await total_xp(session, author) == 100


async def test_reciprocity_limit(session: AsyncSession, make_user: MakeUser) -> None:
    user_a = await make_user(email="a@test.tld", handle="alpha")
    user_b = await make_user(email="b@test.tld", handle="beta")
    for _ in range(3):
        awarded = await grant_xp(
            session,
            user=user_a,
            delta=5,
            reason=XpReason.ANSWER_ACCEPTED,
            source_post=None,
            actor=user_b,
        )
        assert awarded == 5
    fourth = await grant_xp(
        session,
        user=user_a,
        delta=5,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=user_b,
    )
    assert fourth == 0
    assert await total_xp(session, user_a) == 15


async def test_recipe_validator_too_young(
    session: AsyncSession, make_user: MakeUser
) -> None:
    author = await make_user(email="a@test.tld", handle="alpha", country="SN")
    validator = await make_user(email="b@test.tld", handle="beta", country="CI")
    recipe = await _recipe(session, author.id)
    author_xp, validator_xp = await grant_recipe_validated(
        session,
        recipe=recipe,
        validator=validator,
        author=author,
    )
    assert author_xp == 0
    assert validator_xp == 0


async def test_recipe_validator_other_country(
    session: AsyncSession, make_user: MakeUser
) -> None:
    old = datetime.now(UTC) - timedelta(days=4)
    author = await make_user(email="a@test.tld", handle="alpha", country="SN")
    validator = await make_user(
        email="b@test.tld",
        handle="beta",
        country="CI",
        created_at=old,
    )
    recipe = await _recipe(session, author.id)
    author_xp, validator_xp = await grant_recipe_validated(
        session,
        recipe=recipe,
        validator=validator,
        author=author,
    )
    assert author_xp == AWARDS[XpReason.RECIPE_VALIDATED_AUTHOR]
    assert validator_xp == AWARDS[XpReason.RECIPE_VALIDATED_VALIDATOR]


async def test_grant_answer_accepted(
    session: AsyncSession, make_user: MakeUser
) -> None:
    asker = await make_user(email="a@test.tld", handle="alpha")
    reply = await make_user(email="b@test.tld", handle="beta")
    question = Post(
        type=PostType.QUESTION,
        author_id=asker.id,
        title="Wave timeout",
        body="ça coupe",
    )
    session.add(question)
    await session.commit()
    await session.refresh(question)
    answer = Post(
        type=PostType.ANSWER,
        parent_id=question.id,
        author_id=reply.id,
        body="retry",
    )
    session.add(answer)
    await session.commit()
    await session.refresh(answer)
    awarded = await grant_answer_accepted(session, answer=answer, question_author=asker)
    assert awarded == 15
    assert await total_xp(session, reply) == 15
