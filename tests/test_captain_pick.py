from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PostType
from app.models.post import Post
from app.models.user import User
from app.services.captains import CaptainError, designate
from app.services.xp import grant_answer_accepted, total_xp

MakeUser = Callable[..., Awaitable[User]]


async def test_captain_doubles_only_when_validated(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    asker = await make_user(email="a@test.tld", handle="askia", country="SN")
    reply = await make_user(email="b@test.tld", handle="bakary", country="CI")
    question = Post(
        type=PostType.QUESTION,
        author_id=asker.id,
        title="Wave",
        body="timeout",
    )
    session.add(question)
    await session.commit()
    await session.refresh(question)
    answer = Post(
        type=PostType.ANSWER,
        parent_id=question.id,
        author_id=reply.id,
        body="retry",
    )
    session.add(answer)
    await session.commit()
    await session.refresh(answer)
    await designate(session, user=reply, post=answer)
    awarded = await grant_answer_accepted(session, answer=answer, question_author=asker)
    assert awarded == 30
    assert await total_xp(session, reply) == 30
    try:
        await designate(session, user=reply, post=answer)
        raise AssertionError("second pick")
    except CaptainError as exc:
        assert exc.code == "already"


async def test_captain_no_double_without_validation(
    session: AsyncSession,
    make_user: MakeUser,
) -> None:
    author = await make_user(email="a@test.tld", handle="askia", country="SN")
    post = Post(
        type=PostType.ANSWER,
        author_id=author.id,
        body="draft",
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    await designate(session, user=author, post=post)
    assert await total_xp(session, author) == 0
