from typing import Any

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.services.badges import award_badges
from app.services.captains import pick_weekly_captains
from app.services.challenges import award_due_podiums


async def startup(_ctx: dict[str, Any]) -> None:
    return None


async def shutdown(_ctx: dict[str, Any]) -> None:
    await engine.dispose()


async def award_challenge_podium(_ctx: dict[str, Any]) -> int:
    async with SessionLocal() as session:
        return await award_due_podiums(session)


async def pick_captains(_ctx: dict[str, Any]) -> int:
    async with SessionLocal() as session:
        return await pick_weekly_captains(session)


async def award_daily_badges(_ctx: dict[str, Any]) -> int:
    async with SessionLocal() as session:
        return await award_badges(session)


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.valkey_url)
    functions = [award_challenge_podium, pick_captains, award_daily_badges]
    cron_jobs = [
        cron(award_challenge_podium, weekday="mon", hour=0, minute=10),  # type: ignore[arg-type]
        cron(pick_captains, weekday="sun", hour=21, minute=0),  # type: ignore[arg-type]
        cron(award_daily_badges, hour=3, minute=15),  # type: ignore[arg-type]
    ]
    on_startup = startup
    on_shutdown = shutdown
