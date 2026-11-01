from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.badge import UserBadge
from app.models.enums import XpReason
from app.models.post import Post
from app.models.reaction import Reaction
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.system import SYSTEM_EMAIL
from app.services.xp import PEER_REASONS

_Actor = aliased(User)

BADGE_SLUGS: tuple[str, ...] = (
    "accepted",
    "marche_auteur",
    "marche_validateur",
    "utile_5",
    "autre_pays",
    "defi_podium",
)

_PODIUM = frozenset(
    {
        XpReason.CHALLENGE_GOLD,
        XpReason.CHALLENGE_SILVER,
        XpReason.CHALLENGE_BRONZE,
    }
)


async def list_user_badges(session: AsyncSession, user: User) -> list[UserBadge]:
    stmt = (
        select(UserBadge)
        .where(UserBadge.user_id == user.id)
        .order_by(UserBadge.awarded_at.asc())
        .limit(6)
    )
    return list((await session.scalars(stmt)).all())


async def _has_reason(
    session: AsyncSession,
    user_id: int,
    reasons: frozenset[str] | set[XpReason] | frozenset[XpReason],
) -> bool:
    values = [
        reason.value if isinstance(reason, XpReason) else reason for reason in reasons
    ]
    row = await session.scalar(
        select(XpLedger.id)
        .where(XpLedger.user_id == user_id, XpLedger.reason.in_(values))
        .limit(1)
    )
    return row is not None


async def _utile_received(session: AsyncSession, user_id: int) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(Reaction)
        .join(Post, Post.id == Reaction.post_id)
        .where(Post.author_id == user_id)
    )
    return int(count or 0)


async def _has_other_country_peer(session: AsyncSession, user: User) -> bool:
    if not user.country:
        return False
    row = await session.scalar(
        select(XpLedger.id)
        .join(_Actor, _Actor.id == XpLedger.source_user_id)
        .where(
            XpLedger.user_id == user.id,
            XpLedger.reason.in_(PEER_REASONS),
            _Actor.country.is_not(None),
            _Actor.country != user.country,
        )
        .limit(1)
    )
    return row is not None


async def earned_slugs(session: AsyncSession, user: User) -> set[str]:
    earned: set[str] = set()
    if await _has_reason(session, user.id, {XpReason.ANSWER_ACCEPTED}):
        earned.add("accepted")
    if await _has_reason(session, user.id, {XpReason.RECIPE_VALIDATED_AUTHOR}):
        earned.add("marche_auteur")
    if await _has_reason(session, user.id, {XpReason.RECIPE_VALIDATED_VALIDATOR}):
        earned.add("marche_validateur")
    if await _utile_received(session, user.id) >= 5:
        earned.add("utile_5")
    if await _has_other_country_peer(session, user):
        earned.add("autre_pays")
    if await _has_reason(session, user.id, _PODIUM):
        earned.add("defi_podium")
    return earned


async def award_user_badges(session: AsyncSession, user: User) -> int:
    existing = {
        badge.slug
        for badge in (
            await session.scalars(select(UserBadge).where(UserBadge.user_id == user.id))
        ).all()
    }
    added = 0
    for slug in await earned_slugs(session, user):
        if slug in existing:
            continue
        session.add(UserBadge(user_id=user.id, slug=slug))
        added += 1
    if added:
        await session.flush()
    return added


async def award_badges(session: AsyncSession) -> int:
    users = list(
        (await session.scalars(select(User).where(User.email != SYSTEM_EMAIL))).all()
    )
    added = 0
    for user in users:
        added += await award_user_badges(session, user)
    await session.commit()
    return added
