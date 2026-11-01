from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import ColumnElement, Subquery, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.countries import AFRICAN_COUNTRIES
from app.models.captain import CaptainPick
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.weeks import week_start
from app.services.xp import PEER_REASONS

_LABELS = dict(AFRICAN_COUNTRIES)
_FORM_WEEKS = 5


@dataclass(frozen=True)
class CountryScore:
    rank: int
    country: str
    label: str
    score: float
    captain_handle: str | None = None
    form: list[float] = field(default_factory=list)


def _user_coupe_xp(
    start: datetime | None = None,
    end: datetime | None = None,
) -> Subquery:
    bonus_filters: list[ColumnElement[bool]] = [XpLedger.reason.in_(PEER_REASONS)]
    total_filters: list[ColumnElement[bool]] = [User.country.is_not(None)]
    if start is not None:
        bonus_filters.append(XpLedger.created_at >= start)
        total_filters.append(XpLedger.created_at >= start)
    if end is not None:
        bonus_filters.append(XpLedger.created_at < end)
        total_filters.append(XpLedger.created_at < end)
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
        .where(*bonus_filters)
        .group_by(XpLedger.user_id)
        .subquery()
    )
    return (
        select(
            User.country.label("country"),
            User.id.label("user_id"),
            (func.sum(XpLedger.delta) + func.coalesce(bonus.c.bonus, 0)).label("xp"),
        )
        .join(XpLedger, XpLedger.user_id == User.id)
        .outerjoin(bonus, bonus.c.user_id == User.id)
        .where(*total_filters)
        .group_by(User.country, User.id, bonus.c.bonus)
        .having(func.sum(XpLedger.delta) > 0)
        .subquery()
    )


async def _country_scores(
    session: AsyncSession,
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict[str, float]:
    totals = _user_coupe_xp(start, end)
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
    )
    rows = (await session.execute(stmt)).all()
    return {str(row.country): float(row.score) for row in rows}


def _form_windows(now: datetime | None = None) -> list[tuple[datetime, datetime]]:
    current = week_start(now)
    offsets = range(_FORM_WEEKS - 1, -1, -1)
    starts = [current - timedelta(days=7 * offset) for offset in offsets]
    return [(start, start + timedelta(days=7)) for start in starts]


async def coupe_standings(session: AsyncSession) -> list[CountryScore]:
    scores = await _country_scores(session)
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
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

    weekly: list[dict[str, float]] = []
    for window_start, window_end in _form_windows():
        weekly.append(await _country_scores(session, window_start, window_end))

    standings: list[CountryScore] = []
    for index, (code, score) in enumerate(ordered, start=1):
        pick = picks.get(code)
        handle = handles.get(pick.user_id) if pick else None
        form = [week.get(code, 0.0) for week in weekly]
        standings.append(
            CountryScore(
                rank=index,
                country=code,
                label=_LABELS.get(code, code),
                score=score,
                captain_handle=handle or None,
                form=form,
            )
        )
    return standings
