from collections.abc import Awaitable, Callable

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.models.user import User
from app.services.qa import create_question
from app.services.search import search_posts, similar_questions

MakeUser = Callable[..., Awaitable[User]]


async def test_search_finds_title_with_typo(
    session: AsyncSession,
    client: AsyncClient,
    make_user: MakeUser,
) -> None:
    user = await make_user(email="a@test.tld", handle="askia")
    pays = await session.scalar(
        select(Tag).where(Tag.category == "pays", Tag.slug == "sn")
    )
    assert pays is not None
    question = await create_question(
        session,
        author=user,
        title="Wave timeout",
        body="Le paiement Wave plante.",
        tag_ids=[pays.id],
    )
    hits = await search_posts(session, q="Wava timeout")
    assert any(hit.post.id == question.id for hit in hits)
    page = await client.get("/recherche", params={"q": "Wava timeout"})
    assert page.status_code == 200
    assert "Wave timeout" in page.text


async def test_similar_questions_above_threshold(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    user = await make_user(email="a@test.tld", handle="askia")
    pays = await session.scalar(
        select(Tag).where(Tag.category == "pays", Tag.slug == "sn")
    )
    assert pays is not None
    await create_question(
        session,
        author=user,
        title="Wave timeout",
        body="Le paiement Wave plante.",
        tag_ids=[pays.id],
    )
    suggestions = await similar_questions(session, "Wave timeuot")
    assert any(post.title == "Wave timeout" for post in suggestions)
