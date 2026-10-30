from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.deps import CurrentUser, SessionDep
from app.core.templates import templates, view_context
from app.services.qa import list_questions, tags_grouped

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def feed(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    tag: str | None = None,
) -> HTMLResponse:
    questions = await list_questions(session, tag_slug=tag)
    groups = await tags_grouped(session)
    return templates.TemplateResponse(
        request,
        "pages/home.html",
        await view_context(
            request,
            session,
            user,
            questions=questions,
            tag_groups=groups,
            active_tag=tag,
        ),
    )
