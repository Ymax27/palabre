from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.deps import CurrentUser, SessionDep
from app.core.templates import templates, view_context
from app.services.ranking import people_standings

router = APIRouter()


@router.get("/classement", response_class=HTMLResponse)
async def classement_page(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    periode: str = "semaine",
) -> HTMLResponse:
    weekly = periode != "saison"
    rows = await people_standings(session, weekly=weekly)
    return templates.TemplateResponse(
        request,
        "pages/classement.html",
        await view_context(
            request,
            session,
            user,
            rows=rows,
            weekly=weekly,
        ),
    )
