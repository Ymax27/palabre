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
from app.services.system import SYSTEM_EMAIL

AWARDS: dict[XpReason, int] = {
    XpReason.ANSWER_ACCEPTED: 15,
    XpReason.RECIPE_PUBLISHED: 10,
    XpReason.RECIPE_VALIDATED_AUTHOR: 20,
    XpReason.RECIPE_VALIDATED_VALIDATOR: 3,
    XpReason.CHALLENGE_GOLD: 30,
    XpReason.CHALLENGE_SILVER: 20,
    XpReason.CHALLENGE_BRONZE: 10,
}

PEER_REASONS: frozenset[str] = frozenset(
    {
        XpReason.ANSWER_ACCEPTED,
        XpReason.RECIPE_VALIDATED_AUTHOR,
        XpReason.RECIPE_VALIDATED_VALIDATOR,
    }
)

_PODIUM: dict[int, XpReason] = {
    1: XpReason.CHALLENGE_GOLD,
    2: XpReason.CHALLENGE_SILVER,
    3: XpReason.CHALLENGE_BRONZE,
}

DAILY_CAP = 100
# 1 crédit XP max entre deux mêmes comptes (tous sens) par jour UTC.
RECIPROCITY_LIMIT = 1
VALIDATOR_MIN_AGE_DAYS = 3
SEASON_1_START = datetime(2026, 11, 2, tzinfo=UTC)
SEASON_1_END = datetime(2026, 11, 22, 23, 59, 59, tzinfo=UTC)

# Seuils de réputation (somme des colonnes rep du registre).
REP_LEVELS: tuple[tuple[int, str], ...] = (
    (0, "nouveau"),
    (15, "membre"),
    (100, "pilier"),
    (500, "ancien"),
)
EDIT_REP_MIN = 15
MODERATE_REP_MIN = 100

_CHAT_REASONS = frozenset({"chat", "message", "room"})


def season_for(moment: datetime | None = None) -> int | None:
    stamp = moment or datetime.now(UTC)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    if SEASON_1_START <= stamp <= SEASON_1_END:
        return 1
    return None


def reputation_level(rep: int) -> str:
    level = REP_LEVELS[0][1]
    for threshold, key in REP_LEVELS:
        if rep >= threshold:
            level = key
    return level


def can_edit(rep: int) -> bool:
    return rep >= EDIT_REP_MIN


def can_moderate(rep: int) -> bool:
    return rep >= MODERATE_REP_MIN


def rep_progress(rep: int) -> float:
    """Fraction 0–1 vers le seuil suivant. Nouveau (rep 0) = anneau ouvert."""
    if rep <= 0:
        return 0.0
    current = REP_LEVELS[0][0]
    nxt: int | None = None
    for threshold, _key in REP_LEVELS:
        if rep >= threshold:
            current = threshold
        elif nxt is None:
            nxt = threshold
    if nxt is None:
        return 1.0
    span = nxt - current
    if span <= 0:
        return 1.0
    return min(1.0, max(0.0, (rep - current) / span))


async def total_xp(session: AsyncSession, user: User) -> int:
    stmt = select(func.coalesce(func.sum(XpLedger.delta), 0)).where(
        XpLedger.user_id == user.id,
    )
    result = await session.scalar(stmt)
    return int(result or 0)


async def total_rep(session: AsyncSession, user: User) -> int:
    stmt = select(func.coalesce(func.sum(XpLedger.rep), 0)).where(
        XpLedger.user_id == user.id,
    )
    result = await session.scalar(stmt)
    return int(result or 0)


async def has_contribution(session: AsyncSession, user: User) -> bool:
    from app.models.enums import PostType
    from app.models.post import Post

    count = await session.scalar(
        select(func.count())
        .select_from(Post)
        .where(
            Post.author_id == user.id,
            Post.type.in_((PostType.QUESTION, PostType.ANSWER, PostType.RECETTE)),
        )
    )
    return int(count or 0) > 0


def _utc_day_start() -> datetime:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


async def _xp_today(session: AsyncSession, user_id: int) -> int:
    start = _utc_day_start()
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
    since = _utc_day_start()
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
    multiplicateur: int = 1,
    skip_reciprocity: bool = False,
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
    raw = delta * max(multiplicateur, 1)
    awarded = min(raw, remaining)

    # 1 échange (au moins 1 ligne) entre la paire par jour UTC ; hors acteur système.
    if (
        not skip_reciprocity
        and actor.email != SYSTEM_EMAIL
        and await _reciprocity_count(session, user.id, actor.id) >= RECIPROCITY_LIMIT
    ):
        return 0

    entry = XpLedger(
        user_id=user.id,
        delta=awarded,
        reason=reason_value,
        source_post_id=source_post.id if source_post is not None else None,
        source_user_id=actor.id,
        rep=awarded,
        saison=season_for(),
        multiplicateur=max(multiplicateur, 1),
    )
    session.add(entry)
    await session.flush()
    return awarded


async def grant_recipe_published(
    session: AsyncSession,
    *,
    recipe: Post,
    author: User,
) -> int:
    from app.services.system import get_system_user

    actor = await get_system_user(session)
    return await grant_xp(
        session,
        user=author,
        delta=AWARDS[XpReason.RECIPE_PUBLISHED],
        reason=XpReason.RECIPE_PUBLISHED,
        source_post=recipe,
        actor=actor,
    )


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
    from app.services.captains import is_designated_post

    multiplier = 2 if await is_designated_post(session, answer) else 1
    return await grant_xp(
        session,
        user=author,
        delta=AWARDS[XpReason.ANSWER_ACCEPTED],
        reason=XpReason.ANSWER_ACCEPTED,
        source_post=answer,
        actor=question_author,
        multiplicateur=multiplier,
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

    from app.services.captains import is_designated_post

    if await _reciprocity_count(session, author.id, validator.id) >= RECIPROCITY_LIMIT:
        return (0, 0)

    multiplier = 2 if await is_designated_post(session, recipe) else 1
    # Une validation « Ça a marché » = un échange (2 lignes) ; skip sur les 2 écritures.
    author_delta = await grant_xp(
        session,
        user=author,
        delta=AWARDS[XpReason.RECIPE_VALIDATED_AUTHOR],
        reason=XpReason.RECIPE_VALIDATED_AUTHOR,
        source_post=recipe,
        actor=validator,
        multiplicateur=multiplier,
        skip_reciprocity=True,
    )
    validator_delta = await grant_xp(
        session,
        user=validator,
        delta=AWARDS[XpReason.RECIPE_VALIDATED_VALIDATOR],
        reason=XpReason.RECIPE_VALIDATED_VALIDATOR,
        source_post=recipe,
        actor=author,
        skip_reciprocity=True,
    )
    return (author_delta, validator_delta)


async def grant_challenge_podium(
    session: AsyncSession,
    *,
    user: User,
    place: int,
    source_post: Post | None,
    actor: User,
) -> int:
    reason = _PODIUM.get(place)
    if reason is None:
        return 0
    return await grant_xp(
        session,
        user=user,
        delta=AWARDS[reason],
        reason=reason,
        source_post=source_post,
        actor=actor,
    )
