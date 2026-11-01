from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.core.deps import LoginUser, SessionDep
from app.core.security import require_csrf
from app.core.templates import templates, view_context
from app.services.notify import (
    get_prefs,
    list_notifications,
    mark_all_read,
    save_prefs,
    unsubscribe_by_token,
)

router = APIRouter()


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_partial(
    request: Request,
    session: SessionDep,
    user: LoginUser,
) -> HTMLResponse:
    items = await list_notifications(session, user)
    await mark_all_read(session, user)
    return templates.TemplateResponse(
        request,
        "partials/notifications.html",
        await view_context(request, session, user, notifications=items),
    )


@router.get("/notifications/preferences", response_class=HTMLResponse)
async def notifications_prefs(
    request: Request,
    session: SessionDep,
    user: LoginUser,
) -> HTMLResponse:
    prefs = await get_prefs(session, user)
    return templates.TemplateResponse(
        request,
        "pages/notification_prefs.html",
        await view_context(request, session, user, prefs=prefs),
    )


@router.post("/notifications/preferences")
async def notifications_prefs_save(
    request: Request,
    session: SessionDep,
    user: LoginUser,
    csrf: str = Form(...),
    in_app: str | None = Form(None),
    email: str | None = Form(None),
) -> Response:
    require_csrf(request, csrf)
    await save_prefs(
        session,
        user,
        in_app=in_app == "on",
        email=email == "on",
    )
    return RedirectResponse(
        "/notifications/preferences",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/n/desinscription", response_class=HTMLResponse)
async def unsubscribe(
    request: Request,
    session: SessionDep,
    token: str = "",
) -> HTMLResponse:
    user = await unsubscribe_by_token(session, token)
    return templates.TemplateResponse(
        request,
        "pages/unsubscribe.html",
        await view_context(
            request,
            session,
            None,
            ok=user is not None,
        ),
    )
