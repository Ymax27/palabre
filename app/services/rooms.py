import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.bus import get_redis
from app.models.enums import RoomKind
from app.models.message_reaction import MessageReaction
from app.models.post import Post
from app.models.post_helper import PostHelper
from app.models.report import Report
from app.models.room import Room
from app.models.room_message import RoomMessage
from app.models.user import User

HISTORY_DAYS = 30
TITLE_MAX = 80
SLOW_SECONDS = 10
PRESENCE_TTL = 300
LINK_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
REACT_KINDS = frozenset({"✅", "🙏", "🔥"})


class RoomError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def list_rooms(session: AsyncSession) -> list[Room]:
    stmt = select(Room).order_by(Room.kind, Room.title)
    return list((await session.scalars(stmt)).all())


async def get_room_by_slug(session: AsyncSession, slug: str) -> Room | None:
    return await session.scalar(select(Room).where(Room.slug == slug))


async def get_message(
    session: AsyncSession,
    message_id: int,
) -> RoomMessage | None:
    stmt = (
        select(RoomMessage)
        .where(RoomMessage.id == message_id)
        .options(
            selectinload(RoomMessage.author),
            selectinload(RoomMessage.replies).selectinload(RoomMessage.author),
            selectinload(RoomMessage.room),
            selectinload(RoomMessage.converted_post),
        )
    )
    return await session.scalar(stmt)


async def last_messages(
    session: AsyncSession,
    room_id: int,
    *,
    limit: int | None = None,
) -> list[RoomMessage]:
    since = datetime.now(UTC) - timedelta(days=HISTORY_DAYS)
    stmt = (
        select(RoomMessage)
        .where(RoomMessage.room_id == room_id, RoomMessage.created_at >= since)
        .options(
            selectinload(RoomMessage.author),
            selectinload(RoomMessage.converted_post),
        )
        .order_by(RoomMessage.created_at.desc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    items = list((await session.scalars(stmt)).all())
    items.reverse()
    return items


async def post_message(
    session: AsyncSession,
    *,
    room: Room,
    author: User,
    body: str,
    parent_id: int | None = None,
) -> RoomMessage:
    text = body.strip()
    if not text:
        raise RoomError("empty")
    age = datetime.now(UTC) - author.created_at
    if age < timedelta(hours=24) and LINK_RE.search(text):
        raise RoomError("no_links")
    last = await session.scalar(
        select(RoomMessage)
        .where(RoomMessage.room_id == room.id, RoomMessage.author_id == author.id)
        .order_by(RoomMessage.created_at.desc())
    )
    if last is not None:
        gap = datetime.now(UTC) - last.created_at
        if gap < timedelta(seconds=SLOW_SECONDS):
            raise RoomError("slow")
    if parent_id is not None:
        parent = await session.get(RoomMessage, parent_id)
        if parent is None or parent.room_id != room.id:
            raise RoomError("parent")
    message = RoomMessage(
        room_id=room.id,
        author_id=author.id,
        parent_id=parent_id,
        body=text,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    await session.refresh(message, attribute_names=["author"])
    return message


async def mark_needs_help(
    session: AsyncSession,
    message: RoomMessage,
) -> RoomMessage:
    message.needs_help = True
    await session.commit()
    await session.refresh(message)
    await session.refresh(message, attribute_names=["author", "converted_post"])
    return message


def draft_from_thread(message: RoomMessage) -> tuple[str, str]:
    stripped = message.body.strip()
    first_line = stripped.splitlines()[0] if stripped else ""
    title = first_line[:TITLE_MAX]
    chunks = [stripped]
    replies = sorted(message.replies, key=lambda item: item.created_at)
    for reply in replies:
        text = reply.body.strip()
        if text:
            chunks.append(text)
    return title, "\n\n".join(chunks)


async def link_converted_post(
    session: AsyncSession,
    *,
    message_id: int | None,
    post: Post,
) -> None:
    if message_id is None:
        return
    message = await session.get(RoomMessage, message_id)
    if message is None:
        return
    post.source_message_id = message.id
    message.converted_post_id = post.id
    helper_ids = {message.author_id}
    replies = list(
        (
            await session.scalars(
                select(RoomMessage).where(RoomMessage.parent_id == message.id)
            )
        ).all()
    )
    for reply in replies:
        helper_ids.add(reply.author_id)
    helper_ids.discard(post.author_id)
    for user_id in helper_ids:
        session.add(PostHelper(post_id=post.id, user_id=user_id))
    if post.type == "question":
        await ensure_aide_room(session, post)


async def ensure_aide_room(session: AsyncSession, question: Post) -> Room:
    existing = await session.scalar(select(Room).where(Room.question_id == question.id))
    if existing is not None:
        return existing
    room = Room(
        kind=RoomKind.AIDE,
        slug=f"aide-{question.id}",
        title=(question.title or "Aide")[:80],
        question_id=question.id,
    )
    session.add(room)
    await session.flush()
    return room


async def react_message(
    session: AsyncSession,
    *,
    message: RoomMessage,
    user: User,
    kind: str,
) -> MessageReaction:
    if kind not in REACT_KINDS:
        raise RoomError("react")
    existing = await session.scalar(
        select(MessageReaction).where(
            MessageReaction.message_id == message.id,
            MessageReaction.user_id == user.id,
            MessageReaction.kind == kind,
        )
    )
    if existing is not None:
        return existing
    reaction = MessageReaction(message_id=message.id, user_id=user.id, kind=kind)
    session.add(reaction)
    await session.commit()
    return reaction


async def report_message(
    session: AsyncSession,
    *,
    message: RoomMessage,
    user: User,
    reason: str,
) -> Report:
    cleaned = reason.strip()[:200]
    if not cleaned:
        raise RoomError("empty")
    row = Report(user_id=user.id, message_id=message.id, reason=cleaned)
    session.add(row)
    await session.commit()
    return row


async def touch_presence(room_id: int, user_id: int) -> int:
    redis = get_redis()
    key = f"room:{room_id}:here"
    member = str(user_id)
    await redis.sadd(key, member)  # type: ignore[misc]
    await redis.expire(key, PRESENCE_TTL)
    return int(await redis.scard(key) or 0)  # type: ignore[misc]


async def presence_count(room_id: int) -> int:
    redis = get_redis()
    return int(await redis.scard(f"room:{room_id}:here") or 0)  # type: ignore[misc]
