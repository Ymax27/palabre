from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.bus import publish_feed
from app.models.enums import PostType, ReactionKind, TagCategory
from app.models.post import Post
from app.models.reaction import Reaction
from app.models.room_message import RoomMessage
from app.models.tag import Tag
from app.models.user import User
from app.services.challenges import attach_challenge
from app.services.notify import notify_accepted, notify_answer
from app.services.rooms import link_converted_post
from app.services.xp import grant_answer_accepted

REQUIRED_TAG_CATEGORIES = (
    TagCategory.PAYS,
    TagCategory.PAIEMENT,
    TagCategory.RESEAU,
    TagCategory.STACK,
)


async def load_context_tags(session: AsyncSession, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        raise QaError("need_country")
    tags = list((await session.scalars(select(Tag).where(Tag.id.in_(tag_ids)))).all())
    present = {tag.category for tag in tags}
    if any(category not in present for category in REQUIRED_TAG_CATEGORIES):
        raise QaError("need_country")
    return tags


class QaError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def list_questions(
    session: AsyncSession,
    *,
    tag_slug: str | None = None,
) -> list[Post]:
    stmt = (
        select(Post)
        .where(Post.type == PostType.QUESTION)
        .options(selectinload(Post.tags), selectinload(Post.author))
        .order_by(Post.created_at.desc())
    )
    if tag_slug:
        stmt = stmt.join(Post.tags).where(Tag.slug == tag_slug)
    result = await session.scalars(stmt)
    return list(result.unique().all())


async def tags_grouped(session: AsyncSession) -> dict[str, list[Tag]]:
    tags = (await session.scalars(select(Tag).order_by(Tag.category, Tag.label))).all()
    grouped: dict[str, list[Tag]] = {
        TagCategory.PAYS: [],
        TagCategory.PAIEMENT: [],
        TagCategory.RESEAU: [],
        TagCategory.STACK: [],
    }
    for tag in tags:
        grouped.setdefault(tag.category, []).append(tag)
    return grouped


async def create_question(
    session: AsyncSession,
    *,
    author: User,
    title: str,
    body: str,
    tag_ids: list[int],
    source_message_id: int | None = None,
    challenge_id: int | None = None,
) -> Post:
    title_clean = title.strip()
    body_clean = body.strip()
    if not title_clean or not body_clean:
        raise QaError("empty")
    tags = await load_context_tags(session, tag_ids)
    post = Post(
        type=PostType.QUESTION,
        author_id=author.id,
        title=title_clean,
        body=body_clean,
        tags=tags,
    )
    session.add(post)
    await session.flush()
    await link_converted_post(
        session,
        message_id=source_message_id,
        post=post,
    )
    await attach_challenge(session, post, challenge_id)
    await session.commit()
    await session.refresh(post)
    return post


async def get_question(session: AsyncSession, question_id: int) -> Post | None:
    stmt = (
        select(Post)
        .where(Post.id == question_id, Post.type == PostType.QUESTION)
        .options(
            selectinload(Post.tags),
            selectinload(Post.author),
            selectinload(Post.answers).selectinload(Post.author),
            selectinload(Post.answers).selectinload(Post.reactions),
            selectinload(Post.source_message).selectinload(RoomMessage.room),
        )
    )
    return await session.scalar(stmt)


async def add_answer(
    session: AsyncSession,
    *,
    question: Post,
    author: User,
    body: str,
) -> Post:
    body_clean = body.strip()
    if not body_clean:
        raise QaError("empty")
    answer = Post(
        type=PostType.ANSWER,
        parent_id=question.id,
        author_id=author.id,
        body=body_clean,
    )
    session.add(answer)
    await session.commit()
    await session.refresh(answer)
    if question.author_id != author.id:
        target = await session.get(User, question.author_id)
        if target is not None:
            await notify_answer(session, author=target, question_id=question.id)
    await publish_feed(f"answer:{question.id}")
    return answer


async def mark_utile(
    session: AsyncSession,
    *,
    post: Post,
    user: User,
) -> int:
    if post.author_id == user.id:
        raise QaError("own_post")
    existing = await session.scalar(
        select(Reaction).where(
            Reaction.user_id == user.id,
            Reaction.post_id == post.id,
        )
    )
    if existing is None:
        session.add(Reaction(user_id=user.id, post_id=post.id, kind=ReactionKind.UTILE))
        await session.commit()
    count = await session.scalar(
        select(func.count()).select_from(Reaction).where(Reaction.post_id == post.id)
    )
    return int(count or 0)


async def utile_count(session: AsyncSession, post_id: int) -> int:
    count = await session.scalar(
        select(func.count()).select_from(Reaction).where(Reaction.post_id == post_id)
    )
    return int(count or 0)


async def user_marked_utile(session: AsyncSession, user_id: int, post_id: int) -> bool:
    row = await session.scalar(
        select(Reaction.id).where(
            Reaction.user_id == user_id,
            Reaction.post_id == post_id,
        )
    )
    return row is not None


async def accept_answer(
    session: AsyncSession,
    *,
    question: Post,
    answer: Post,
    user: User,
) -> int:
    if question.author_id != user.id:
        raise QaError("not_author")
    if answer.parent_id != question.id or answer.type != PostType.ANSWER:
        raise QaError("bad_answer")
    if question.accepted_answer_id is not None:
        raise QaError("already_accepted")
    question.accepted_answer_id = answer.id
    awarded = await grant_answer_accepted(
        session,
        answer=answer,
        question_author=user,
    )
    await session.commit()
    if awarded > 0:
        reply = await session.get(User, answer.author_id)
        if reply is not None:
            await notify_accepted(session, author=reply, question_id=question.id)
    await publish_feed(f"accepted:{question.id}")
    return awarded
