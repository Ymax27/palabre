from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.core.deps import CurrentUser, OnboardedUser, SessionDep
from app.core.i18n import t
from app.core.security import require_csrf
from app.core.templates import templates, view_context
from app.services.leagues import (
    LeagueError,
    create_league,
    get_league_by_code,
    join_league,
    league_standings,
    list_user_leagues,
)

router = APIRouter()


@router.get("/ligues", response_class=HTMLResponse)
async def leagues_index(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
) -> HTMLResponse:
    leagues = await list_user_leagues(session, user)
    return templates.TemplateResponse(
        request,
        "pages/leagues.html",
        await view_context(
            request,
            session,
            user,
            leagues=leagues,
            error=None,
        ),
    )


@router.post("/ligues")
async def leagues_create(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    name: str = Form(...),
    csrf: str = Form(...),
) -> Response:
    require_csrf(request, csrf)
    try:
        league = await create_league(session, owner=user, name=name)
    except LeagueError:
        leagues = await list_user_leagues(session, user)
        return templates.TemplateResponse(
            request,
            "pages/leagues.html",
            await view_context(
                request,
                session,
                user,
                leagues=leagues,
                error=t("league_empty"),
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        f"/ligues/{league.invite_code}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/ligues/rejoindre")
async def leagues_join(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    code: str = Form(...),
    csrf: str = Form(...),
) -> Response:
    require_csrf(request, csrf)
    try:
        league = await join_league(session, user=user, code=code)
    except LeagueError:
        leagues = await list_user_leagues(session, user)
        return templates.TemplateResponse(
            request,
            "pages/leagues.html",
            await view_context(
                request,
                session,
                user,
                leagues=leagues,
                error=t("league_not_found"),
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        f"/ligues/{league.invite_code}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/ligues/{code}", response_class=HTMLResponse)
async def league_detail(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    code: str,
    periode: str = "saison",
) -> HTMLResponse:
    league = await get_league_by_code(session, code)
    if league is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    weekly = periode != "saison"
    standings = await league_standings(session, league, weekly=weekly)
    return templates.TemplateResponse(
        request,
        "pages/league.html",
        await view_context(
            request,
            session,
            user,
            league=league,
            standings=standings,
            weekly=weekly,
        ),
    )
