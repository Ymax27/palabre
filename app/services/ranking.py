from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.countries import AFRICAN_COUNTRIES
from app.models.user import User
from app.models.xp_ledger import XpLedger

_LABELS = dict(AFRICAN_COUNTRIES)


@dataclass(frozen=True)
class CountryScore:
    rank: int
    country: str
    label: str
    score: float


async def coupe_standings(session: AsyncSession) -> list[CountryScore]:
    totals = (
        select(
            User.country.label("country"),
            User.id.label("user_id"),
            func.sum(XpLedger.delta).label("xp"),
        )
        .join(XpLedger, XpLedger.user_id == User.id)
        .where(User.country.is_not(None))
        .group_by(User.country, User.id)
        .having(func.sum(XpLedger.delta) > 0)
        .subquery()
    )
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
    standings: list[CountryScore] = []
    for index, row in enumerate(rows, start=1):
        code = str(row.country)
        standings.append(
            CountryScore(
                rank=index,
                country=code,
                label=_LABELS.get(code, code),
                score=float(row.score),
            )
        )
    return standings
