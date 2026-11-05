import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bus import get_redis
from app.core.countries import AFRICAN_COUNTRIES
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.weeks import week_start
from app.services.xp import SEASON_1_END, SEASON_1_START


def _coupe_bounds() -> tuple[datetime, datetime]:
    now = datetime.now(SEASON_1_START.tzinfo)
    if now < SEASON_1_START:
        return datetime(2026, 1, 1, tzinfo=SEASON_1_START.tzinfo), SEASON_1_END
    return SEASON_1_START, SEASON_1_END


_LABELS = dict(AFRICAN_COUNTRIES)
_FORM_WEEKS = 5
COUPE_ZSET = "coupe:s1"
COUPE_PREV = "coupe:s1:prev"
COUPE_FORM = "coupe:s1:form"
RANK_SEASON = "rank:season:1"


@dataclass(frozen=True)
class CountryScore:
    rank: int
    country: str
    label: str
    score: float
    captain_handle: str | None = None
    form: list[float] = field(default_factory=list)
    movement: int = 0


@dataclass(frozen=True)
class PersonScore:
    rank: int
    handle: str
    country: str
    xp: int


def _rank_week_key(start: datetime | None = None) -> str:
    monday = week_start(start)
    return f"rank:week:{monday.date().isoformat()}"


async def _country_scores(
    session: AsyncSession,
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict[str, float]:
    default_start, default_end = _coupe_bounds()
    window_start = start if start is not None else default_start
    window_end = end if end is not None else default_end
    totals = (
        select(
            User.country.label("country"),
            User.id.label("user_id"),
            func.sum(XpLedger.delta).label("xp"),
        )
        .join(XpLedger, XpLedger.user_id == User.id)
        .where(
            User.country.is_not(None),
            XpLedger.created_at >= window_start,
            XpLedger.created_at <= window_end,
        )
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
        select(ranked.c.country, func.avg(ranked.c.xp).label("score"))
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


async def compute_standings(session: AsyncSession) -> list[CountryScore]:
    scores = await _country_scores(session)
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    weekly: list[dict[str, float]] = []
    for window_start, window_end in _form_windows():
        weekly.append(await _country_scores(session, window_start, window_end))
    standings: list[CountryScore] = []
    for index, (code, score) in enumerate(ordered, start=1):
        standings.append(
            CountryScore(
                rank=index,
                country=code,
                label=_LABELS.get(code, code),
                score=score,
                form=[week.get(code, 0.0) for week in weekly],
            )
        )
    return standings


async def refresh_coupe(session: AsyncSession) -> int:
    standings = await compute_standings(session)
    redis = get_redis()
    old = await redis.zrevrange(COUPE_ZSET, 0, -1)
    old_ranks = {str(country): str(index) for index, country in enumerate(old, start=1)}
    pipe = redis.pipeline()
    await pipe.delete(COUPE_ZSET)
    await pipe.delete(COUPE_FORM)
    for row in standings:
        await pipe.zadd(COUPE_ZSET, {row.country: row.score})
        await pipe.hset(COUPE_FORM, row.country, json.dumps(row.form))  # type: ignore[misc]
    await pipe.delete(COUPE_PREV)
    if old_ranks:
        await pipe.hset(COUPE_PREV, mapping=old_ranks)  # type: ignore[misc]
    await pipe.execute()
    await _refresh_people(session)
    return len(standings)


async def _refresh_people(session: AsyncSession) -> None:
    monday = week_start()
    week_rows = await _people_xp(session, monday, monday + timedelta(days=7))
    season_rows = await _people_xp(session, SEASON_1_START, SEASON_1_END)
    week_key = _rank_week_key(monday)
    redis = get_redis()
    await redis.delete(week_key)
    await redis.delete(RANK_SEASON)
    if week_rows:
        await redis.zadd(week_key, week_rows)
    if season_rows:
        await redis.zadd(RANK_SEASON, season_rows)


async def _people_xp(
    session: AsyncSession,
    start: datetime,
    end: datetime,
) -> dict[str, float]:
    stmt = (
        select(User.id, func.coalesce(func.sum(XpLedger.delta), 0))
        .join(XpLedger, XpLedger.user_id == User.id)
        .where(XpLedger.created_at >= start, XpLedger.created_at <= end)
        .group_by(User.id)
        .having(func.sum(XpLedger.delta) > 0)
    )
    rows = (await session.execute(stmt)).all()
    return {str(row[0]): float(row[1]) for row in rows}


async def coupe_standings(session: AsyncSession) -> list[CountryScore]:
    redis = get_redis()
    raw = await redis.zrevrange(COUPE_ZSET, 0, -1, withscores=True)
    if not raw:
        await refresh_coupe(session)
        raw = await redis.zrevrange(COUPE_ZSET, 0, -1, withscores=True)
    prev = await redis.hgetall(COUPE_PREV)  # type: ignore[misc]
    form_map = await redis.hgetall(COUPE_FORM)  # type: ignore[misc]
    standings: list[CountryScore] = []
    for index, (code, score) in enumerate(raw, start=1):
        country = str(code)
        old = int(prev[country]) if country in prev else index
        form_raw = form_map.get(country, "[]")
        form = [float(item) for item in json.loads(form_raw)]
        standings.append(
            CountryScore(
                rank=index,
                country=country,
                label=_LABELS.get(country, country),
                score=float(score),
                form=form,
                movement=old - index,
            )
        )
    return standings


async def country_rank(session: AsyncSession, country: str) -> int | None:
    standings = await coupe_standings(session)
    for row in standings:
        if row.country == country:
            return row.rank
    return None


async def people_standings(
    session: AsyncSession,
    *,
    weekly: bool,
) -> list[PersonScore]:
    redis = get_redis()
    key = _rank_week_key() if weekly else RANK_SEASON
    raw = await redis.zrevrange(key, 0, 49, withscores=True)
    if not raw:
        await refresh_coupe(session)
        raw = await redis.zrevrange(key, 0, 49, withscores=True)
    ids = [int(user_id) for user_id, _score in raw]
    users = {
        user.id: user
        for user in (await session.scalars(select(User).where(User.id.in_(ids)))).all()
    }
    result: list[PersonScore] = []
    for index, (user_id, xp) in enumerate(raw, start=1):
        user = users.get(int(user_id))
        if user is None:
            continue
        result.append(
            PersonScore(
                rank=index,
                handle=user.handle or "",
                country=user.country or "",
                xp=int(xp),
            )
        )
    return result
