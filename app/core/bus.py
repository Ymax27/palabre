from collections.abc import AsyncIterator

from redis.asyncio import Redis

from app.core.config import settings

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(settings.valkey_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def room_channel(room_id: int) -> str:
    return f"palabre:room:{room_id}"


async def publish_room(room_id: int, payload: str) -> None:
    await get_redis().publish(room_channel(room_id), payload)


async def subscribe_room(room_id: int) -> AsyncIterator[str]:
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(room_channel(room_id))
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message.get("data")
            if isinstance(data, str):
                yield data
    finally:
        await pubsub.unsubscribe(room_channel(room_id))
        await pubsub.aclose()  # type: ignore[no-untyped-call]
