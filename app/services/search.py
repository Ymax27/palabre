from dataclasses import dataclass

from markupsafe import Markup
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import PostType
from app.models.post import Post
from app.services.markdown import sanitize_headline

# Exception AGENTS.md : SQL brut FTS / pg_trgm
# (search_tsv @@, ts_headline, similarity / %).

SEARCH_SQL = """
SELECT p.id,
       ts_rank(p.search_tsv, plainto_tsquery('simple', :q))
         + similarity(coalesce(p.title, ''), :q) AS score,
       ts_headline(
         'simple',
         coalesce(p.title, '') || ' ' || coalesce(p.body, ''),
         plainto_tsquery('simple', :q),
         'StartSel=<mark>, StopSel=</mark>, MaxWords=32, MinWords=10'
       ) AS headline
FROM posts p
WHERE p.type IN ('question', 'recette')
  AND (
    p.search_tsv @@ plainto_tsquery('simple', :q)
    OR similarity(coalesce(p.title, ''), :q) > 0.2
    OR coalesce(p.title, '') % :q
  )
  AND (
    CAST(:tag AS text) IS NULL OR EXISTS (
      SELECT 1 FROM post_tags pt
      JOIN tags t ON t.id = pt.tag_id
      WHERE pt.post_id = p.id AND t.slug = :tag
    )
  )
ORDER BY score DESC
LIMIT 30
"""

SUGGEST_SQL = """
SELECT id
FROM posts
WHERE type = 'question'
  AND similarity(coalesce(title, ''), :title) > 0.25
ORDER BY similarity(coalesce(title, ''), :title) DESC
LIMIT :limit
"""


@dataclass(frozen=True)
class SearchHit:
    post: Post
    headline: Markup
    score: float


async def search_posts(
    session: AsyncSession,
    *,
    q: str,
    tag_slug: str | None = None,
) -> list[SearchHit]:
    query = q.strip()
    if not query:
        return []
    tag = tag_slug.strip() if tag_slug and tag_slug.strip() else None
    result = await session.execute(text(SEARCH_SQL), {"q": query, "tag": tag})
    rows = result.all()
    if not rows:
        return []
    ids = [int(row.id) for row in rows]
    posts = list(
        (
            await session.scalars(
                select(Post)
                .where(Post.id.in_(ids))
                .options(selectinload(Post.tags), selectinload(Post.author))
            )
        ).all()
    )
    by_id = {post.id: post for post in posts}
    hits: list[SearchHit] = []
    for row in rows:
        post = by_id.get(int(row.id))
        if post is None:
            continue
        hits.append(
            SearchHit(
                post=post,
                headline=Markup(sanitize_headline(str(row.headline or ""))),
                score=float(row.score or 0),
            )
        )
    return hits


async def similar_questions(
    session: AsyncSession,
    title: str,
    *,
    limit: int = 5,
) -> list[Post]:
    cleaned = title.strip()
    if len(cleaned) < 3:
        return []
    result = await session.execute(
        text(SUGGEST_SQL),
        {"title": cleaned, "limit": limit},
    )
    ids = [int(row.id) for row in result.all()]
    if not ids:
        return []
    posts = list(
        (
            await session.scalars(
                select(Post)
                .where(Post.id.in_(ids), Post.type == PostType.QUESTION)
                .options(selectinload(Post.tags))
            )
        ).all()
    )
    order = {post_id: index for index, post_id in enumerate(ids)}
    posts.sort(key=lambda post: order.get(post.id, 0))
    return posts
