from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import XpReason
from app.models.user import User
from app.models.worked_report import WorkedReport
from app.services.auth import request_magic_link
from app.services.recipes import create_recipe, report_worked
from app.services.xp import AWARDS, total_xp
from tests.helpers import context_tag_ids

MakeUser = Callable[..., Awaitable[User]]


async def test_marche_other_country_awards_xp(
    session: AsyncSession,
    client: AsyncClient,
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
        title="Retry Wave",
        body="1. Timeout 15 s",
        tag_ids=await context_tag_ids(session),
    )
    await report_worked(
        session,
        recipe=recipe,
        user=validator,
        country="CI",
        environment="4G Abidjan",
    )
    await session.refresh(author)
    await session.refresh(validator)
    published = AWARDS[XpReason.RECIPE_PUBLISHED]
    validated = AWARDS[XpReason.RECIPE_VALIDATED_AUTHOR]
    assert await total_xp(session, author) == published + validated
    assert (
        await total_xp(session, validator)
        == AWARDS[XpReason.RECIPE_VALIDATED_VALIDATOR]
    )

    token = await request_magic_link(session, email=author.email, ip="127.0.0.1")
    assert token is not None
    logged = await client.get(f"/auth/magic?token={token}", follow_redirects=True)
    assert logged.status_code == 200
    assert 'id="xp-pill"' in logged.text
    assert f"{published + validated} XP" in logged.text

    coupe = await client.get("/coupe")
    assert coupe.status_code == 200
    assert "Ivoire" in coupe.text
    assert "Sénégal" in coupe.text or "Senegal" in coupe.text


async def test_marche_too_young_refused(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    author = await make_user(email="a@test.tld", handle="askia", country="SN")
    validator = await make_user(email="b@test.tld", handle="bakary", country="CI")
    recipe = await create_recipe(
        session,
        author=author,
        title="Retry Wave",
        body="1. Timeout",
        tag_ids=await context_tag_ids(session),
    )
    report, awarded = await report_worked(
        session,
        recipe=recipe,
        user=validator,
        country="CI",
        environment="4G",
    )
    assert report.id is not None
    assert awarded == 0
    count = await session.scalar(
        select(func.count())
        .select_from(WorkedReport)
        .where(WorkedReport.post_id == recipe.id)
    )
    assert int(count or 0) == 1
    assert await total_xp(session, author) == AWARDS[XpReason.RECIPE_PUBLISHED]
    assert await total_xp(session, validator) == 0


async def test_marche_same_country_no_xp(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    old = datetime.now(UTC) - timedelta(days=4)
    author = await make_user(email="a@test.tld", handle="askia", country="SN")
    validator = await make_user(
        email="b@test.tld",
        handle="fatou",
        country="SN",
        created_at=old,
    )
    recipe = await create_recipe(
        session,
        author=author,
        title="Retry Wave",
        body="1. Timeout",
        tag_ids=await context_tag_ids(session),
    )
    report, awarded = await report_worked(
        session,
        recipe=recipe,
        user=validator,
        country="SN",
        environment="Fibre Dakar",
    )
    assert report.id is not None
    assert awarded == 0
    assert await total_xp(session, author) == AWARDS[XpReason.RECIPE_PUBLISHED]
    assert await total_xp(session, validator) == 0
