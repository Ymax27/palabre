import logging
import secrets
from datetime import UTC, datetime

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.i18n import t
from app.models.notification import Notification, NotificationPref
from app.models.user import User
from app.services.system import SYSTEM_EMAIL

logger = logging.getLogger("palabre.notify")

KINDS = frozenset(
    {
        "answer",
        "accepted",
        "worked",
        "challenge",
        "league_join",
        "merci",
        "weekly",
        "reminder",
    }
)


def new_unsubscribe_token() -> str:
    return secrets.token_urlsafe(32)


async def ensure_unsubscribe_token(session: AsyncSession, user: User) -> str:
    if user.unsubscribe_token:
        return user.unsubscribe_token
    user.unsubscribe_token = new_unsubscribe_token()
    await session.flush()
    return user.unsubscribe_token


async def get_prefs(session: AsyncSession, user: User) -> NotificationPref:
    pref = await session.get(NotificationPref, user.id)
    if pref is not None:
        return pref
    pref = NotificationPref(user_id=user.id, in_app=True, email=True)
    session.add(pref)
    await session.flush()
    return pref


async def save_prefs(
    session: AsyncSession,
    user: User,
    *,
    in_app: bool,
    email: bool,
) -> NotificationPref:
    pref = await get_prefs(session, user)
    pref.in_app = in_app
    pref.email = email
    await session.commit()
    return pref


async def unread_count(session: AsyncSession, user: User) -> int:
    count = await session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return int(count or 0)


async def list_notifications(
    session: AsyncSession,
    user: User,
    *,
    limit: int = 20,
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list((await session.scalars(stmt)).all())


async def mark_all_read(session: AsyncSession, user: User) -> None:
    await session.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    await session.commit()


async def enqueue_email(
    user: User,
    kind: str,
    title: str,
    url: str,
) -> None:
    try:
        redis = await create_pool(RedisSettings.from_dsn(settings.valkey_url))
        try:
            await redis.enqueue_job(
                "send_notification_email",
                user.id,
                kind,
                title,
                url,
            )
        finally:
            await redis.aclose()
    except Exception:
        logger.exception("Impossible d'enfiler l'email de notification")


async def notify(
    session: AsyncSession,
    *,
    user: User,
    kind: str,
    title: str,
    url: str,
) -> Notification | None:
    if kind not in KINDS:
        return None
    if user.email == SYSTEM_EMAIL:
        return None
    prefs = await get_prefs(session, user)
    item: Notification | None = None
    if prefs.in_app:
        item = Notification(user_id=user.id, kind=kind, title=title, url=url)
        session.add(item)
        await session.flush()
    if prefs.email:
        await enqueue_email(user, kind, title, url)
    await session.commit()
    return item


async def notify_answer(
    session: AsyncSession,
    *,
    author: User,
    question_id: int,
) -> None:
    await notify(
        session,
        user=author,
        kind="answer",
        title=t("notif_answer"),
        url=f"/questions/{question_id}",
    )


async def notify_accepted(
    session: AsyncSession,
    *,
    author: User,
    question_id: int,
) -> None:
    await notify(
        session,
        user=author,
        kind="accepted",
        title=t("notif_accepted"),
        url=f"/questions/{question_id}",
    )


async def notify_worked(
    session: AsyncSession,
    *,
    author: User,
    recipe_id: int,
) -> None:
    await notify(
        session,
        user=author,
        kind="worked",
        title=t("notif_worked"),
        url=f"/recettes/{recipe_id}",
    )


async def notify_challenge_open(
    session: AsyncSession,
    *,
    challenge_id: int,
) -> None:
    users = list(
        (
            await session.scalars(
                select(User).where(
                    User.email != SYSTEM_EMAIL,
                    User.handle.is_not(None),
                )
            )
        ).all()
    )
    for user in users:
        await notify(
            session,
            user=user,
            kind="challenge",
            title=t("notif_challenge"),
            url=f"/defi#c{challenge_id}",
        )


async def notify_merci(
    session: AsyncSession,
    *,
    helper: User,
    url: str,
) -> None:
    await notify(
        session,
        user=helper,
        kind="merci",
        title=t("notif_merci"),
        url=url,
    )


async def notify_league_join(
    session: AsyncSession,
    *,
    owner: User,
    code: str,
) -> None:
    await notify(
        session,
        user=owner,
        kind="league_join",
        title=t("notif_league_join"),
        url=f"/ligues/{code}",
    )


async def notify_weekly_digest(session: AsyncSession) -> int:
    users = list(
        (
            await session.scalars(
                select(User).where(
                    User.email != SYSTEM_EMAIL,
                    User.handle.is_not(None),
                )
            )
        ).all()
    )
    for user in users:
        await notify(
            session,
            user=user,
            kind="weekly",
            title=t("notif_weekly"),
            url="/classement",
        )
    return len(users)


async def notify_challenge_reminder(session: AsyncSession) -> int:
    users = list(
        (
            await session.scalars(
                select(User).where(
                    User.email != SYSTEM_EMAIL,
                    User.handle.is_not(None),
                )
            )
        ).all()
    )
    for user in users:
        await notify(
            session,
            user=user,
            kind="reminder",
            title=t("notif_reminder"),
            url="/defi",
        )
    return len(users)


async def unsubscribe_by_token(session: AsyncSession, token: str) -> User | None:
    cleaned = token.strip()
    if not cleaned:
        return None
    user = await session.scalar(select(User).where(User.unsubscribe_token == cleaned))
    if user is None:
        return None
    prefs = await get_prefs(session, user)
    prefs.email = False
    await session.commit()
    return user
