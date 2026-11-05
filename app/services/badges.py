from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.badge import UserBadge
from app.models.enums import XpReason
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.system import SYSTEM_EMAIL

BADGE_SLUGS: tuple[str, ...] = ("teste_en_prod",)


async def list_user_badges(session: AsyncSession, user: User) -> list[UserBadge]:
    stmt = (
        select(UserBadge)
        .where(UserBadge.user_id == user.id)
        .order_by(UserBadge.awarded_at.asc())
        .limit(6)
    )
    return list((await session.scalars(stmt)).all())


async def award_user_badges(session: AsyncSession, user: User) -> int:
    has_worked = await session.scalar(
        select(XpLedger.id)
        .where(
            XpLedger.user_id == user.id,
            XpLedger.reason == XpReason.RECIPE_VALIDATED_AUTHOR,
        )
        .limit(1)
    )
    if has_worked is None:
        return 0
    existing = await session.scalar(
        select(UserBadge).where(
            UserBadge.user_id == user.id,
            UserBadge.slug == "teste_en_prod",
        )
    )
    if existing is not None:
        return 0
    session.add(UserBadge(user_id=user.id, slug="teste_en_prod"))
    await session.flush()
    return 1


async def award_badges(session: AsyncSession) -> int:
    users = list(
        (await session.scalars(select(User).where(User.email != SYSTEM_EMAIL))).all()
    )
    added = 0
    for user in users:
        added += await award_user_badges(session, user)
    await session.commit()
    return added
