from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.worker import send_notification_email
from app.models.notification import Notification, NotificationPref
from app.models.tag import Tag
from app.models.user import User
from app.services.challenges import create_challenge
from app.services.leagues import create_league, join_league
from app.services.notify import (
    email_allowed,
    get_prefs,
    notify,
    notify_challenge_reminder,
    notify_merci,
    notify_weekly_digest,
    save_prefs,
)
from app.services.qa import accept_answer, add_answer, create_question
from app.services.recipes import create_recipe, report_worked
from tests.helpers import context_tag_ids, csrf_from, login_client

MakeUser = Callable[..., Awaitable[User]]


async def test_one_notification_per_event_no_smtp(
    session: AsyncSession,
    make_user: MakeUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queued: list[tuple[object, ...]] = []

    async def record(
        user: User,
        kind: str,
        title: str,
        url: str,
    ) -> None:
        queued.append((user.id, kind, title, url))

    async def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("SMTP appelé dans la requête")

    monkeypatch.setattr("app.services.notify.enqueue_email", record)
    monkeypatch.setattr("app.core.email.send_mail", boom)

    old = datetime.now(UTC) - timedelta(days=4)
    asker = await make_user(email="a@test.tld", handle="askia", country="SN")
    reply = await make_user(email="b@test.tld", handle="bakary", country="CI")
    validator = await make_user(
        email="c@test.tld",
        handle="amina",
        country="KE",
        created_at=old,
    )
    tags = await context_tag_ids(session)
    pays = await session.scalar(select(Tag).where(Tag.slug == "sn"))
    question = await create_question(
        session,
        author=asker,
        title="Timeout Wave",
        body="ça coupe",
        tag_ids=tags,
    )
    answer = await add_answer(
        session,
        question=question,
        author=reply,
        body="Réessaie hors 2G.",
    )
    await accept_answer(session, question=question, answer=answer, user=asker)

    recipe = await create_recipe(
        session,
        author=asker,
        title="Retry Wave",
        body="Timeout 15 s",
        tag_ids=tags,
    )
    await report_worked(
        session,
        recipe=recipe,
        user=validator,
        country="KE",
        environment="4G Nairobi",
    )

    await create_challenge(
        session,
        title="Défi ouvert",
        description="Une recette.",
        starts_at=datetime.now(UTC),
        ends_at=datetime.now(UTC) + timedelta(days=6),
        tag_ids=[pays.id],
    )

    league = await create_league(session, owner=asker, name="Baobab")
    await join_league(session, user=reply, code=league.invite_code)

    kinds = list((await session.scalars(select(Notification.kind))).all())
    assert kinds.count("answer") == 1
    assert kinds.count("accepted") == 1
    assert kinds.count("worked") == 1
    assert kinds.count("league_join") == 1
    assert kinds.count("challenge") >= 1
    queued_kinds = [item[1] for item in queued]
    assert queued_kinds.count("answer") == 1
    assert queued_kinds.count("accepted") == 1
    assert queued_kinds.count("worked") == 1
    assert "challenge" not in queued_kinds
    assert "league_join" not in queued_kinds
    count = await session.scalar(select(func.count()).select_from(Notification))
    assert int(count or 0) >= 5


async def test_merci_in_app_only_no_email(
    session: AsyncSession,
    make_user: MakeUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queued: list[str] = []

    async def record(*_args: object, **_kwargs: object) -> None:
        queued.append("sent")

    monkeypatch.setattr("app.services.notify.enqueue_email", record)
    helper = await make_user(email="a@test.tld", handle="askia")
    await notify_merci(session, helper=helper, url="/questions/1")
    prefs = await get_prefs(session, helper)
    assert prefs.email is True
    assert email_allowed(prefs, "merci") is False
    assert queued == []
    kinds = list((await session.scalars(select(Notification.kind))).all())
    assert kinds == ["merci"]


async def test_email_pref_per_kind_blocks_enqueue(
    session: AsyncSession,
    make_user: MakeUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queued: list[str] = []

    async def record(
        user: User,
        kind: str,
        title: str,
        url: str,
    ) -> None:
        queued.append(kind)

    monkeypatch.setattr("app.services.notify.enqueue_email", record)
    user = await make_user(email="a@test.tld", handle="askia")
    await save_prefs(
        session,
        user,
        in_app=True,
        email=True,
        email_answer=False,
        email_accepted=True,
        email_worked=True,
        email_reminder=True,
        email_weekly=True,
    )
    await notify(
        session,
        user=user,
        kind="answer",
        title="Réponse",
        url="/questions/1",
    )
    await notify(
        session,
        user=user,
        kind="accepted",
        title="Acceptée",
        url="/questions/1",
    )
    assert queued == ["accepted"]
    prefs = await session.get(NotificationPref, user.id)
    assert prefs is not None
    assert prefs.email_answer is False


async def test_weekly_digest_and_reminder_enqueue(
    session: AsyncSession,
    make_user: MakeUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queued: list[str] = []

    async def record(
        user: User,
        kind: str,
        title: str,
        url: str,
    ) -> None:
        queued.append(kind)

    monkeypatch.setattr("app.services.notify.enqueue_email", record)
    await make_user(email="a@test.tld", handle="askia")
    await make_user(email="b@test.tld", handle="bakary")
    assert await notify_weekly_digest(session) == 2
    assert await notify_challenge_reminder(session) == 2
    assert queued.count("weekly") == 2
    assert queued.count("reminder") == 2
    kinds = list((await session.scalars(select(Notification.kind))).all())
    assert kinds.count("weekly") == 2
    assert kinds.count("reminder") == 2


async def test_send_notification_email_respects_prefs(
    session: AsyncSession,
    make_user: MakeUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[str] = []

    async def fake_mail(to: str, subject: str, body: str) -> None:
        sent.append(to)

    monkeypatch.setattr("app.jobs.worker.send_mail", fake_mail)
    user = await make_user(email="a@test.tld", handle="askia")
    await save_prefs(
        session,
        user,
        in_app=True,
        email=True,
        email_answer=False,
        email_accepted=True,
        email_worked=True,
        email_reminder=True,
        email_weekly=True,
    )
    await send_notification_email({}, user.id, "answer", "Réponse", "/q/1")
    assert sent == []
    await send_notification_email({}, user.id, "accepted", "OK", "/q/1")
    assert sent == ["a@test.tld"]


async def test_prefs_form_and_bell(
    client: AsyncClient,
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    user = await make_user(email="a@test.tld", handle="askia")
    await notify(
        session,
        user=user,
        kind="answer",
        title="Réponse",
        url="/questions/1",
    )
    await login_client(client, session, user)
    bell = await client.get("/notifications")
    assert bell.status_code == 200
    assert "Réponse" in bell.text

    page = await client.get("/notifications/preferences")
    assert page.status_code == 200
    assert 'name="email_answer"' in page.text
    csrf = csrf_from(page.text)
    saved = await client.post(
        "/notifications/preferences",
        data={
            "csrf": csrf,
            "in_app": "on",
            "email": "on",
            "email_accepted": "on",
        },
    )
    assert saved.status_code == 303
    prefs = await get_prefs(session, user)
    assert prefs.email_answer is False
    assert prefs.email_accepted is True


async def test_home_shows_challenge_card(
    client: AsyncClient,
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    await make_user(email="a@test.tld", handle="askia", country="SN")
    pays = await session.scalar(select(Tag).where(Tag.slug == "sn"))
    assert pays is not None
    await create_challenge(
        session,
        title="Timeout Wave : une recette qui tient",
        description="Partage une recette.",
        starts_at=datetime.now(UTC) - timedelta(hours=1),
        ends_at=datetime.now(UTC) + timedelta(days=3),
        tag_ids=[pays.id],
    )
    page = await client.get("/")
    assert page.status_code == 200
    assert "Timeout Wave : une recette qui tient" in page.text
    assert "challenge-card" in page.text
