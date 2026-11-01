import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.league import League, LeagueMember
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.notify import notify_league_join

SEASON_START = datetime(2026, 11, 2, tzinfo=UTC)
SEASON_END = datetime(2026, 11, 22, 23, 59, 59, tzinfo=UTC)


class LeagueError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class LeagueRow:
    user: User
    xp: int


def _code() -> str:
    return secrets.token_urlsafe(8)[:10]


async def list_user_leagues(session: AsyncSession, user: User) -> list[League]:
    stmt = (
        select(League)
        .join(LeagueMember)
        .where(LeagueMember.user_id == user.id)
        .options(selectinload(League.owner))
        .order_by(League.created_at.desc())
    )
    return list((await session.scalars(stmt)).all())


async def get_league_by_code(session: AsyncSession, code: str) -> League | None:
    return await session.scalar(
        select(League)
        .where(League.invite_code == code.strip())
        .options(selectinload(League.owner))
    )


async def create_league(session: AsyncSession, *, owner: User, name: str) -> League:
    cleaned = name.strip()
    if not cleaned:
        raise LeagueError("empty")
    league = League(name=cleaned, invite_code=_code(), owner_id=owner.id)
    session.add(league)
    await session.flush()
    session.add(LeagueMember(league_id=league.id, user_id=owner.id))
    await session.commit()
    await session.refresh(league)
    return league


async def join_league(session: AsyncSession, *, user: User, code: str) -> League:
    league = await get_league_by_code(session, code)
    if league is None:
        raise LeagueError("not_found")
    existing = await session.scalar(
        select(LeagueMember).where(
            LeagueMember.league_id == league.id,
            LeagueMember.user_id == user.id,
        )
    )
    if existing is None:
        session.add(LeagueMember(league_id=league.id, user_id=user.id))
        await session.commit()
        if league.owner_id != user.id:
            owner = league.owner or await session.get(User, league.owner_id)
            if owner is not None:
                await notify_league_join(
                    session,
                    owner=owner,
                    code=league.invite_code,
                )
    return league


async def league_standings(session: AsyncSession, league: League) -> list[LeagueRow]:
    members = (
        select(LeagueMember.user_id)
        .where(LeagueMember.league_id == league.id)
        .subquery()
    )
    stmt = (
        select(User, func.coalesce(func.sum(XpLedger.delta), 0).label("xp"))
        .join(members, members.c.user_id == User.id)
        .outerjoin(
            XpLedger,
            (XpLedger.user_id == User.id)
            & (XpLedger.created_at >= SEASON_START)
            & (XpLedger.created_at <= SEASON_END),
        )
        .group_by(User.id)
        .order_by(func.coalesce(func.sum(XpLedger.delta), 0).desc())
    )
    rows = (await session.execute(stmt)).all()
    return [LeagueRow(user=row[0], xp=int(row[1] or 0)) for row in rows]
