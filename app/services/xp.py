"""Registre d'XP.

Tout gain ou perte passe par ce module. Ne jamais modifier un total à la main.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import XpReason
from app.models.post import Post
from app.models.user import User
from app.models.xp_ledger import XpLedger

AWARDS: dict[XpReason, int] = {
    XpReason.ANSWER_ACCEPTED: 15,
    XpReason.RECIPE_PUBLISHED: 10,
    XpReason.RECIPE_VALIDATED_AUTHOR: 20,
    XpReason.RECIPE_VALIDATED_VALIDATOR: 3,
}

DAILY_CAP = 100
RECIPROCITY_LIMIT = 3
RECIPROCITY_DAYS = 7
VALIDATOR_MIN_AGE_DAYS = 3

_CHAT_REASONS = frozenset({"chat", "message", "room"})

_LEVELS: tuple[tuple[int, int], ...] = (
    (500, 3),
    (100, 2),
    (15, 1),
    (0, 0),
)


def reputation_level(xp: int) -> int:
    for threshold, level in _LEVELS:
        if xp >= threshold:
            return level
    return 0


async def total_xp(session: AsyncSession, user: User) -> int:
    stmt = select(func.coalesce(func.sum(XpLedger.delta), 0)).where(
        XpLedger.user_id == user.id,
    )
    result = await session.scalar(stmt)
    return int(result or 0)


async def _xp_today(session: AsyncSession, user_id: int) -> int:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(func.coalesce(func.sum(XpLedger.delta), 0)).where(
        XpLedger.user_id == user_id,
        XpLedger.created_at >= start,
    )
    result = await session.scalar(stmt)
    return int(result or 0)


async def _reciprocity_count(
    session: AsyncSession,
    user_id: int,
    actor_id: int,
) -> int:
    since = datetime.now(UTC) - timedelta(days=RECIPROCITY_DAYS)
    pair = or_(
        (XpLedger.user_id == user_id) & (XpLedger.source_user_id == actor_id),
        (XpLedger.user_id == actor_id) & (XpLedger.source_user_id == user_id),
    )
    stmt = (
        select(func.count())
        .select_from(XpLedger)
        .where(
            pair,
            XpLedger.created_at >= since,
            XpLedger.delta > 0,
        )
    )
    result = await session.scalar(stmt)
    return int(result or 0)


async def grant_xp(
    session: AsyncSession,
    *,
    user: User,
    delta: int,
    reason: XpReason | str,
    source_post: Post | None,
    actor: User,
) -> int:
    reason_value = reason.value if isinstance(reason, XpReason) else reason
    if user.id == actor.id:
        return 0
    if reason_value in _CHAT_REASONS:
        return 0
    if delta <= 0:
        return 0

    remaining = DAILY_CAP - await _xp_today(session, user.id)
    if remaining <= 0:
        return 0
    awarded = min(delta, remaining)

    if await _reciprocity_count(session, user.id, actor.id) >= RECIPROCITY_LIMIT:
        return 0

    entry = XpLedger(
        user_id=user.id,
        delta=awarded,
        reason=reason_value,
        source_post_id=source_post.id if source_post is not None else None,
        source_user_id=actor.id,
    )
    session.add(entry)
    await session.flush()

    user.niveau = reputation_level(await total_xp(session, user))
    await session.flush()
    return awarded


async def grant_answer_accepted(
    session: AsyncSession,
    *,
    answer: Post,
    question_author: User,
) -> int:
    if answer.author_id == question_author.id:
        return 0
    author = await session.get(User, answer.author_id)
    if author is None:
        return 0
    return await grant_xp(
        session,
        user=author,
        delta=AWARDS[XpReason.ANSWER_ACCEPTED],
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=answer,
        actor=question_author,
    )


async def grant_recipe_validated(
    session: AsyncSession,
    *,
    recipe: Post,
    validator: User,
    author: User,
) -> tuple[int, int]:
    age = datetime.now(UTC) - validator.created_at
    if age < timedelta(days=VALIDATOR_MIN_AGE_DAYS):
        return (0, 0)
    if validator.country is None or author.country is None:
        return (0, 0)
    if validator.country == author.country:
        return (0, 0)

    author_delta = await grant_xp(
        session,
        user=author,
        delta=AWARDS[XpReason.RECIPE_VALIDATED_AUTHOR],
        reason=XpReason.RECIPE_VALIDATED_AUTHOR,
        source_post=recipe,
        actor=validator,
    )
    validator_delta = await grant_xp(
        session,
        user=validator,
        delta=AWARDS[XpReason.RECIPE_VALIDATED_VALIDATOR],
        reason=XpReason.RECIPE_VALIDATED_VALIDATOR,
        source_post=recipe,
        actor=author,
    )
    return (author_delta, validator_delta)
