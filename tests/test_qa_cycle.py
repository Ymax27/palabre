from collections.abc import Awaitable, Callable

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.models.user import User
from app.services.auth import request_magic_link
from app.services.qa import accept_answer, add_answer, create_question, mark_utile
from app.services.xp import total_xp

MakeUser = Callable[..., Awaitable[User]]


async def test_pose_repond_utile_accepte_xp(
    session: AsyncSession,
    client: AsyncClient,
    make_user: MakeUser,
) -> None:
    user_a = await make_user(email="a@test.tld", handle="askia", country="SN")
    user_b = await make_user(email="b@test.tld", handle="bakary", country="CI")
    pays = await session.scalar(
        select(Tag).where(Tag.category == "pays", Tag.slug == "sn")
    )
    assert pays is not None

    question = await create_question(
        session,
        author=user_a,
        title="Timeout Wave",
        body="Le paiement **Wave** plante.",
        tag_ids=[pays.id],
    )
    answer = await add_answer(
        session,
        question=question,
        author=user_b,
        body="Réessaie hors 2G.",
    )
    count = await mark_utile(session, post=answer, user=user_a)
    assert count == 1
    assert await total_xp(session, user_b) == 0

    awarded = await accept_answer(
        session, question=question, answer=answer, user=user_a
    )
    assert awarded == 15
    await session.refresh(user_b)
    assert await total_xp(session, user_b) == 15
    assert user_b.niveau == 1

    token = await request_magic_link(session, email=user_b.email, ip="127.0.0.1")
    assert token is not None
    logged = await client.get(
        f"/auth/magic?token={token}",
        follow_redirects=True,
    )
    assert logged.status_code == 200
    assert 'id="xp-pill"' in logged.text
    assert "15 XP" in logged.text

    coupe = await client.get("/coupe")
    assert coupe.status_code == 200
    assert "Ivoire" in coupe.text
    assert "15.0" in coupe.text
