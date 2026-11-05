from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.badge import UserBadge
from app.models.challenge import Challenge
from app.models.notification import Notification
from app.models.user import User
from app.models.xp_ledger import XpLedger
from app.services.badges import award_user_badges
from app.services.challenges import remaining_label
from app.services.notify import notify_merci
from app.services.recipes import create_recipe, report_worked
from app.services.xp import total_xp
from tests.helpers import context_tag_ids, csrf_from, login_client

MakeUser = Callable[..., Awaitable[User]]


async def test_merci_notifies_without_xp(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    helper = await make_user(email="a@test.tld", handle="askia")
    await notify_merci(session, helper=helper, url="/questions/1")
    kinds = list((await session.scalars(select(Notification.kind))).all())
    assert kinds == ["merci"]
    count = await session.scalar(select(func.count()).select_from(XpLedger))
    assert int(count or 0) == 0
    assert await total_xp(session, helper) == 0


async def test_badge_teste_en_prod_once(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    old = datetime.now(UTC) - timedelta(days=4)
    author = await make_user(email="a@test.tld", handle="askia", country="SN")
    validator = await make_user(
        email="b@test.tld",
        handle="bakary",
        country="CI",
        created_at=old,
    )
    recipe = await create_recipe(
        session,
        author=author,
        title="Retry",
        body="timeout",
        tag_ids=await context_tag_ids(session),
    )
    await report_worked(
        session,
        recipe=recipe,
        user=validator,
        country="CI",
        environment="4G",
    )
    badges = list(
        (
            await session.scalars(
                select(UserBadge).where(UserBadge.user_id == author.id)
            )
        ).all()
    )
    assert [badge.slug for badge in badges] == ["teste_en_prod"]
    added = await award_user_badges(session, author)
    assert added == 0


async def test_challenge_ends_sunday_20h(
    session: AsyncSession,
) -> None:
    challenge = Challenge(
        title="Wave",
        description="recette",
        starts_at=datetime(2026, 11, 2, tzinfo=UTC),
        ends_at=datetime(2026, 11, 8, 20, 0, tzinfo=UTC),
    )
    session.add(challenge)
    await session.commit()
    assert challenge.ends_at.hour == 20
    assert challenge.ends_at.weekday() == 6
    label = remaining_label(
        challenge,
        now=datetime(2026, 11, 6, 16, 0, tzinfo=UTC),
    )
    assert "2 j" in label
    assert "4 h" in label


async def test_palette_has_country_and_tag(
    session: AsyncSession,
    client: AsyncClient,
    make_user: MakeUser,
) -> None:
    user = await make_user(email="a@test.tld", handle="askia")
    await login_client(client, session, user)
    page = await client.get("/")
    assert page.status_code == 200
    assert "/salons/sn" in page.text
    assert "/recherche?tag=wave" in page.text
    assert "/classement" in page.text


async def test_classement_page(
    session: AsyncSession,
    client: AsyncClient,
) -> None:
    page = await client.get("/classement")
    assert page.status_code == 200
    assert "Semaine" in page.text or "Saison" in page.text


async def test_recipe_form_requires_fields(
    session: AsyncSession,
    client: AsyncClient,
    make_user: MakeUser,
) -> None:
    user = await make_user(email="a@test.tld", handle="askia")
    await login_client(client, session, user)
    page = await client.get("/recettes/nouvelle")
    csrf = csrf_from(page.text)
    assert "probleme" in page.text
    submitted = await client.post(
        "/recettes",
        data={
            "csrf": csrf,
            "title": "Retry",
            "body": "étapes",
            "probleme": "",
            "solution": "",
        },
    )
    assert submitted.status_code == 400
