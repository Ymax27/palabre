from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import Subquery, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.countries import AFRICAN_COUNTRIES
from app.models.captain import CaptainPick
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.xp import PEER_REASONS

_LABELS = dict(AFRICAN_COUNTRIES)


@dataclass(frozen=True)
class CountryScore:
    rank: int
    country: str
    label: str
    score: float
    captain_handle: str | None = None
    form: list[float] = field(default_factory=list)


def _user_coupe_xp() -> Subquery:
    bonus = (
        select(
            XpLedger.user_id.label("user_id"),
            func.sum(XpLedger.delta).label("bonus"),
        )
        .join(User, User.id == XpLedger.user_id)
        .join(
            CaptainPick,
            (CaptainPick.user_id == User.id)
            & (CaptainPick.country == User.country)
            & (XpLedger.created_at >= CaptainPick.week_start)
            & (XpLedger.created_at < CaptainPick.week_start + timedelta(days=7)),
        )
        .where(XpLedger.reason.in_(PEER_REASONS))
        .group_by(XpLedger.user_id)
        .subquery()
    )
    totals = (
        select(
            User.country.label("country"),
            User.id.label("user_id"),
            (func.sum(XpLedger.delta) + func.coalesce(bonus.c.bonus, 0)).label("xp"),
        )
        .join(XpLedger, XpLedger.user_id == User.id)
        .outerjoin(bonus, bonus.c.user_id == User.id)
        .where(User.country.is_not(None))
        .group_by(User.country, User.id, bonus.c.bonus)
        .having(func.sum(XpLedger.delta) > 0)
        .subquery()
    )
    return totals


async def coupe_standings(session: AsyncSession) -> list[CountryScore]:
    totals = _user_coupe_xp()
    ranked = (
        select(
            totals.c.country,
            totals.c.xp,
            func.row_number()
            .over(partition_by=totals.c.country, order_by=totals.c.xp.desc())
            .label("rn"),
        )
    ).subquery()
    stmt = (
        select(
            ranked.c.country,
            func.avg(ranked.c.xp).label("score"),
        )
        .where(ranked.c.rn <= 10)
        .group_by(ranked.c.country)
        .order_by(func.avg(ranked.c.xp).desc())
    )
    rows = (await session.execute(stmt)).all()
    from app.services.weeks import week_start

    start = week_start()
    picks = {
        pick.country: pick
        for pick in (
            await session.scalars(
                select(CaptainPick).where(CaptainPick.week_start == start)
            )
        ).all()
    }
    handles: dict[int, str] = {}
    if picks:
        users = (
            await session.scalars(
                select(User).where(User.id.in_([p.user_id for p in picks.values()]))
            )
        ).all()
        handles = {user.id: user.handle or "" for user in users}

    standings: list[CountryScore] = []
    for index, row in enumerate(rows, start=1):
        code = str(row.country)
        pick = picks.get(code)
        handle = handles.get(pick.user_id) if pick else None
        standings.append(
            CountryScore(
                rank=index,
                country=code,
                label=_LABELS.get(code, code),
                score=float(row.score),
                captain_handle=handle or None,
            )
        )
    return standings
