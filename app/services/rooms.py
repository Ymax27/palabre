from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.room import Room
from app.models.room_message import RoomMessage
from app.models.user import User

LAST_MESSAGES = 50


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
        .options(selectinload(RoomMessage.author))
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
