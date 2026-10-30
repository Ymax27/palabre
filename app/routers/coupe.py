from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.deps import CurrentUser, SessionDep
from app.core.templates import templates, view_context
from app.services.ranking import coupe_standings

router = APIRouter()


@router.get("/coupe", response_class=HTMLResponse)
async def coupe_page(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
) -> HTMLResponse:
    standings = await coupe_standings(session)
    return templates.TemplateResponse(
        request,
        "pages/coupe.html",
        await view_context(request, session, user, standings=standings),
    )
