from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import XpReason
from app.models.tag import Tag
from app.models.user import User
from app.models.worked_report import WorkedReport
from app.services.auth import request_magic_link
from app.services.recipes import RecipeError, create_recipe, report_worked
from app.services.xp import AWARDS, total_xp

MakeUser = Callable[..., Awaitable[User]]


async def _pays(session: AsyncSession, slug: str = "sn") -> Tag:
    tag = await session.scalar(
        select(Tag).where(Tag.category == "pays", Tag.slug == slug)
    )
    assert tag is not None
    return tag


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
    pays = await _pays(session)
    recipe = await create_recipe(
        session,
        author=author,
        title="Retry Wave",
        body="1. Timeout 15 s",
        tag_ids=[pays.id],
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
    assert await total_xp(session, author) == AWARDS[XpReason.RECIPE_VALIDATED_AUTHOR]
    assert (
        await total_xp(session, validator)
        == AWARDS[XpReason.RECIPE_VALIDATED_VALIDATOR]
    )
    assert author.niveau == 1

    token = await request_magic_link(session, email=author.email, ip="127.0.0.1")
    assert token is not None
    logged = await client.get(f"/auth/magic?token={token}", follow_redirects=True)
    assert logged.status_code == 200
    assert 'id="xp-pill"' in logged.text
    assert "20 XP" in logged.text

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
    pays = await _pays(session)
    recipe = await create_recipe(
        session,
        author=author,
        title="Retry Wave",
        body="1. Timeout",
        tag_ids=[pays.id],
    )
    try:
        await report_worked(
            session,
            recipe=recipe,
            user=validator,
            country="CI",
            environment="4G",
        )
        raise AssertionError("expected RecipeError")
    except RecipeError as exc:
        assert exc.code == "too_young"
    count = await session.scalar(
        select(func.count())
        .select_from(WorkedReport)
        .where(WorkedReport.post_id == recipe.id)
    )
    assert int(count or 0) == 0
    assert await total_xp(session, author) == 0
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
    pays = await _pays(session)
    recipe = await create_recipe(
        session,
        author=author,
        title="Retry Wave",
        body="1. Timeout",
        tag_ids=[pays.id],
    )
    report = await report_worked(
        session,
        recipe=recipe,
        user=validator,
        country="SN",
        environment="Fibre Dakar",
    )
    assert report.id is not None
    assert await total_xp(session, author) == 0
    assert await total_xp(session, validator) == 0
