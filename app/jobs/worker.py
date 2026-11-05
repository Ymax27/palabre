from typing import Any

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.core.email import send_mail
from app.core.i18n import t
from app.models.user import User
from app.services.badges import award_badges
from app.services.captains import pick_weekly_captains
from app.services.challenges import award_due_podiums
from app.services.notify import (
    email_allowed,
    ensure_unsubscribe_token,
    get_prefs,
    notify_challenge_reminder,
    notify_weekly_digest,
)
from app.services.ranking import refresh_coupe
from app.services.streaks import refresh_all_streaks


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


async def refresh_coupe_job(_ctx: dict[str, Any]) -> int:
    async with SessionLocal() as session:
        return await refresh_coupe(session)


async def refresh_streaks_job(_ctx: dict[str, Any]) -> int:
    async with SessionLocal() as session:
        return await refresh_all_streaks(session)


async def weekly_digest_job(_ctx: dict[str, Any]) -> int:
    async with SessionLocal() as session:
        return await notify_weekly_digest(session)


async def challenge_reminder_job(_ctx: dict[str, Any]) -> int:
    async with SessionLocal() as session:
        return await notify_challenge_reminder(session)


async def send_notification_email(
    _ctx: dict[str, Any],
    user_id: int,
    kind: str,
    title: str,
    url: str,
) -> None:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None:
            return
        prefs = await get_prefs(session, user)
        if not email_allowed(prefs, kind):
            return
        token = await ensure_unsubscribe_token(session, user)
        await session.commit()
    unsub = f"{settings.app_base_url}/n/desinscription?token={token}"
    body = f"{title}\n{settings.app_base_url}{url}\n\n{t('notif_unsub')}: {unsub}"
    await send_mail(user.email, title, body)


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.valkey_url)
    functions = [
        award_challenge_podium,
        pick_captains,
        award_daily_badges,
        refresh_coupe_job,
        refresh_streaks_job,
        weekly_digest_job,
        challenge_reminder_job,
        send_notification_email,
    ]
    cron_jobs = [
        cron(award_challenge_podium, weekday="mon", hour=0, minute=10),  # type: ignore[arg-type]
        cron(pick_captains, weekday="sun", hour=21, minute=0),  # type: ignore[arg-type]
        cron(award_daily_badges, hour=3, minute=15),  # type: ignore[arg-type]
        cron(refresh_coupe_job, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),  # type: ignore[arg-type]
        cron(refresh_streaks_job, hour=0, minute=20),  # type: ignore[arg-type]
        cron(weekly_digest_job, weekday="mon", hour=8, minute=0),  # type: ignore[arg-type]
        cron(challenge_reminder_job, weekday="sun", hour=16, minute=0),  # type: ignore[arg-type]
    ]
    on_startup = startup
    on_shutdown = shutdown
