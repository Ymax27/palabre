from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PostType, XpReason
from app.models.post import Post
from app.models.tag import Tag
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.challenges import award_podium, create_challenge
from app.services.system import get_system_user
from app.services.xp import grant_xp, total_xp

MakeUser = Callable[..., Awaitable[User]]


async def test_podium_respects_daily_cap(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    author = await make_user(email="a@test.tld", handle="askia", country="SN")
    actor = await make_user(email="b@test.tld", handle="bakary", country="CI")
    pays = await session.scalar(
        select(Tag).where(Tag.category == "pays", Tag.slug == "sn")
    )
    assert pays is not None
    ended = datetime.now(UTC) - timedelta(hours=1)
    challenge = await create_challenge(
        session,
        title="Défi test",
        description="Timeout.",
        starts_at=ended - timedelta(days=7),
        ends_at=ended,
        tag_ids=[pays.id],
    )
    recipe = Post(
        type=PostType.RECETTE,
        author_id=author.id,
        title="Retry",
        body="timeout 15s",
        challenge_id=challenge.id,
    )
    session.add(recipe)
    await session.commit()
    await session.refresh(recipe)

    first = await grant_xp(
        session,
        user=author,
        delta=80,
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=recipe,
        actor=actor,
    )
    assert first == 80
    await session.commit()

    system = await get_system_user(session)
    awarded = await award_podium(session, challenge)
    assert awarded == [20]
    assert await total_xp(session, author) == 100
    row = await session.scalar(
        select(XpLedger).where(
            XpLedger.user_id == author.id,
            XpLedger.reason == XpReason.CHALLENGE_GOLD,
        )
    )
    assert row is not None
    assert row.delta == 20
    assert row.source_user_id == system.id
