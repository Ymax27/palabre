from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.post import Post
from app.models.room import Room
from app.models.room_message import RoomMessage
from app.models.user import User

LAST_MESSAGES = 50
TITLE_MAX = 80


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
    limit: int = LAST_MESSAGES,
) -> list[RoomMessage]:
    stmt = (
        select(RoomMessage)
        .where(RoomMessage.room_id == room_id)
        .options(
            selectinload(RoomMessage.author),
            selectinload(RoomMessage.converted_post),
        )
        .order_by(RoomMessage.created_at.desc())
        .limit(limit)
    )
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
