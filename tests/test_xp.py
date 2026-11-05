from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PostType, XpReason
from app.models.post import Post
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.recipes import create_recipe
from app.services.xp import (
    AWARDS,
    can_edit,
    can_moderate,
    grant_answer_accepted,
    grant_recipe_published,
    grant_recipe_validated,
    grant_xp,
    rep_progress,
    reputation_level,
    season_for,
    total_rep,
    total_xp,
)
from tests.helpers import context_tag_ids

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
    actor_a = await make_user(email="b@test.tld", handle="beta")
    actor_b = await make_user(email="c@test.tld", handle="gamma")
    first = await grant_xp(
        session,
        user=author,
        delta=80,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=actor_a,
    )
    second = await grant_xp(
        session,
        user=author,
        delta=30,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=actor_b,
    )
    assert first == 80
    assert second == 20
    assert await total_xp(session, author) == 100


async def test_reciprocity_one_exchange_per_utc_day(
    session: AsyncSession, make_user: MakeUser
) -> None:
    user_a = await make_user(email="a@test.tld", handle="alpha")
    user_b = await make_user(email="b@test.tld", handle="beta")
    first = await grant_xp(
        session,
        user=user_a,
        delta=5,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=user_b,
    )
    second = await grant_xp(
        session,
        user=user_a,
        delta=5,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=user_b,
    )
    reverse = await grant_xp(
        session,
        user=user_b,
        delta=5,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=user_a,
    )
    assert first == 5
    assert second == 0
    assert reverse == 0
    assert await total_xp(session, user_a) == 5
    assert await total_xp(session, user_b) == 0


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
    assert await total_rep(session, author) == author_xp
    assert await total_rep(session, validator) == validator_xp


async def test_recipe_published_awards_ten(
    session: AsyncSession, make_user: MakeUser
) -> None:
    author = await make_user(email="a@test.tld", handle="alpha", country="SN")
    recipe = await create_recipe(
        session,
        author=author,
        title="Retry Wave",
        body="Timeout 15 s",
        tag_ids=await context_tag_ids(session),
    )
    assert await total_xp(session, author) == AWARDS[XpReason.RECIPE_PUBLISHED]
    row = await session.scalar(
        select(XpLedger).where(
            XpLedger.user_id == author.id,
            XpLedger.reason == XpReason.RECIPE_PUBLISHED,
        )
    )
    assert row is not None
    assert row.delta == 10
    assert row.rep == 10
    assert recipe.id == row.source_post_id


async def test_recipe_published_respects_daily_cap(
    session: AsyncSession, make_user: MakeUser
) -> None:
    author = await make_user(email="a@test.tld", handle="alpha", country="SN")
    actor = await make_user(email="b@test.tld", handle="beta", country="CI")
    await grant_xp(
        session,
        user=author,
        delta=95,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=actor,
    )
    await session.commit()
    recipe = await _recipe(session, author.id)
    awarded = await grant_recipe_published(session, recipe=recipe, author=author)
    assert awarded == 5
    assert await total_xp(session, author) == 100


async def test_ledger_writes_rep_saison_multiplicateur(
    session: AsyncSession, make_user: MakeUser
) -> None:
    author = await make_user(email="a@test.tld", handle="alpha")
    actor = await make_user(email="b@test.tld", handle="beta")
    await grant_xp(
        session,
        user=author,
        delta=15,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=actor,
    )
    await session.commit()
    row = await session.scalar(select(XpLedger).where(XpLedger.user_id == author.id))
    assert row is not None
    assert row.rep == 15
    assert row.multiplicateur == 1
    assert row.saison == season_for()
    assert await total_rep(session, author) == 15
    assert reputation_level(15) == "membre"
    assert can_edit(15) is True
    assert can_moderate(15) is False
    assert can_moderate(100) is True
    assert rep_progress(0) == 0.0
    assert rep_progress(15) == 0.0
    assert rep_progress(50) > 0.0
    assert rep_progress(500) == 1.0


async def test_ledger_is_append_only(
    session: AsyncSession, make_user: MakeUser
) -> None:
    author = await make_user(email="a@test.tld", handle="alpha")
    actor = await make_user(email="b@test.tld", handle="beta")
    await grant_xp(
        session,
        user=author,
        delta=15,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=None,
        actor=actor,
    )
    await session.commit()
    with pytest.raises(Exception, match="append-only"):
        await session.execute(text("UPDATE xp_ledger SET delta = 99"))
        await session.commit()
    await session.rollback()


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
    assert await total_rep(session, reply) == 15
