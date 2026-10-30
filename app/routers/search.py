from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.deps import CurrentUser, SessionDep
from app.core.i18n import t
from app.core.templates import templates, view_context
from app.services.qa import tags_grouped
from app.services.search import search_posts, similar_questions

router = APIRouter()


@router.get("/recherche", response_class=HTMLResponse)
async def search_page(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    q: str = "",
    tag: str | None = None,
) -> HTMLResponse:
    hits = await search_posts(session, q=q, tag_slug=tag)
    groups = await tags_grouped(session)
    return templates.TemplateResponse(
        request,
        "pages/search.html",
        await view_context(
            request,
            session,
            user,
            q=q,
            hits=hits,
            tag_groups=groups,
            active_tag=tag,
        ),
    )


@router.get("/questions/suggestions", response_class=HTMLResponse)
async def question_suggestions(
    request: Request,
    session: SessionDep,
    title: str = "",
) -> HTMLResponse:
    suggestions = await similar_questions(session, title)
    return templates.TemplateResponse(
        request,
        "partials/suggestions.html",
        {"suggestions": suggestions, "t": t},
    )
