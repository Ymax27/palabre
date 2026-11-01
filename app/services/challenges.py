from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.challenge import Challenge
from app.models.post import Post
from app.models.tag import Tag
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.system import get_system_user
from app.services.xp import PEER_REASONS, grant_challenge_podium


class ChallengeError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ChallengeRow:
    user: User
    xp: int


async def featured_challenge(session: AsyncSession) -> Challenge | None:
    now = datetime.now(UTC)
    live = await session.scalar(
        select(Challenge)
        .where(Challenge.starts_at <= now, Challenge.ends_at >= now)
        .options(selectinload(Challenge.tags))
        .order_by(Challenge.starts_at.desc())
    )
    if live is not None:
        return live
    upcoming = await session.scalar(
        select(Challenge)
        .where(Challenge.starts_at > now)
        .options(selectinload(Challenge.tags))
        .order_by(Challenge.starts_at.asc())
    )
    if upcoming is not None:
        return upcoming
    return await session.scalar(
        select(Challenge)
        .options(selectinload(Challenge.tags))
        .order_by(Challenge.starts_at.desc())
    )


async def get_challenge(session: AsyncSession, challenge_id: int) -> Challenge | None:
    return await session.scalar(
        select(Challenge)
        .where(Challenge.id == challenge_id)
        .options(selectinload(Challenge.tags))
    )


async def list_participations(
    session: AsyncSession,
    challenge: Challenge,
) -> list[Post]:
    stmt = (
        select(Post)
        .where(Post.challenge_id == challenge.id)
        .options(selectinload(Post.author), selectinload(Post.tags))
        .order_by(Post.created_at.desc())
    )
    return list((await session.scalars(stmt)).all())


async def challenge_standings(
    session: AsyncSession,
    challenge: Challenge,
) -> list[ChallengeRow]:
    stmt = (
        select(User, func.coalesce(func.sum(XpLedger.delta), 0).label("xp"))
        .join(XpLedger, XpLedger.user_id == User.id)
        .join(Post, Post.id == XpLedger.source_post_id)
        .where(
            Post.challenge_id == challenge.id,
            XpLedger.reason.in_(PEER_REASONS),
        )
        .group_by(User.id)
        .order_by(func.sum(XpLedger.delta).desc())
    )
    rows = (await session.execute(stmt)).all()
    return [ChallengeRow(user=row[0], xp=int(row[1] or 0)) for row in rows]


async def create_challenge(
    session: AsyncSession,
    *,
    title: str,
    description: str,
    starts_at: datetime,
    ends_at: datetime,
    tag_ids: list[int],
) -> Challenge:
    title_clean = title.strip()
    body = description.strip()
    if not title_clean or not body:
        raise ChallengeError("empty")
    if ends_at <= starts_at:
        raise ChallengeError("dates")
    tags = list((await session.scalars(select(Tag).where(Tag.id.in_(tag_ids)))).all())
    challenge = Challenge(
        title=title_clean,
        description=body,
        starts_at=starts_at,
        ends_at=ends_at,
        tags=tags,
    )
    session.add(challenge)
    await session.commit()
    await session.refresh(challenge)
    return challenge


async def attach_challenge(
    session: AsyncSession,
    post: Post,
    challenge_id: int | None,
) -> None:
    if challenge_id is None:
        return
    challenge = await get_challenge(session, challenge_id)
    if challenge is None:
        return
    now = datetime.now(UTC)
    if challenge.starts_at <= now <= challenge.ends_at:
        post.challenge_id = challenge.id


async def award_podium(session: AsyncSession, challenge: Challenge) -> list[int]:
    if challenge.podium_awarded_at is not None:
        return []
    now = datetime.now(UTC)
    if now < challenge.ends_at:
        return []
    standings = await challenge_standings(session, challenge)
    if not standings:
        challenge.podium_awarded_at = now
        await session.commit()
        return []
    actor = await get_system_user(session)
    awarded: list[int] = []
    posts = await list_participations(session, challenge)
    by_author = {post.author_id: post for post in reversed(posts)}
    for place, row in enumerate(standings[:3], start=1):
        source = by_author.get(row.user.id)
        delta = await grant_challenge_podium(
            session,
            user=row.user,
            place=place,
            source_post=source,
            actor=actor,
        )
        awarded.append(delta)
    challenge.podium_awarded_at = now
    await session.commit()
    return awarded


async def award_due_podiums(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    due = list(
        (
            await session.scalars(
                select(Challenge).where(
                    Challenge.ends_at < now,
                    Challenge.podium_awarded_at.is_(None),
                )
            )
        ).all()
    )
    count = 0
    for challenge in due:
        await award_podium(session, challenge)
        count += 1
    return count
