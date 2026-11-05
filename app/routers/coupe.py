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
    week_podium = [row for row in standings if row.form and row.form[-1] > 0][:3]
    if not week_podium:
        week_podium = standings[:3]
    return templates.TemplateResponse(
        request,
        "pages/coupe.html",
        await view_context(
            request,
            session,
            user,
            standings=standings,
            week_podium=week_podium,
        ),
    )
