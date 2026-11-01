from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.tag import Tag
from app.models.user import User
from app.services.challenges import create_challenge
from app.services.leagues import create_league, join_league
from app.services.qa import accept_answer, add_answer, create_question
from app.services.recipes import create_recipe, report_worked

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
    pays = await session.scalar(
        select(Tag).where(Tag.category == "pays", Tag.slug == "sn")
    )
    assert pays is not None

    question = await create_question(
        session,
        author=asker,
        title="Timeout Wave",
        body="ça coupe",
        tag_ids=[pays.id],
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
        tag_ids=[pays.id],
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
    assert queued_kinds.count("league_join") == 1
    assert "challenge" in queued_kinds
    count = await session.scalar(select(func.count()).select_from(Notification))
    assert int(count or 0) >= 5
