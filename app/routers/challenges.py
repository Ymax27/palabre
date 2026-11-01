from datetime import UTC, datetime

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.core.deps import AdminUser, CurrentUser, SessionDep
from app.core.i18n import t
from app.core.security import require_csrf
from app.core.templates import templates, view_context
from app.services.challenges import (
    ChallengeError,
    challenge_standings,
    create_challenge,
    featured_challenge,
    list_participations,
)
from app.services.qa import tags_grouped

router = APIRouter()


@router.get("/defi", response_class=HTMLResponse)
async def challenge_page(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
) -> HTMLResponse:
    challenge = await featured_challenge(session)
    posts = await list_participations(session, challenge) if challenge else []
    standings = await challenge_standings(session, challenge) if challenge else []
    return templates.TemplateResponse(
        request,
        "pages/challenge.html",
        await view_context(
            request,
            session,
            user,
            challenge=challenge,
            posts=posts,
            standings=standings,
        ),
    )


@router.get("/admin/defis", response_class=HTMLResponse)
async def admin_challenge_form(
    request: Request,
    session: SessionDep,
    user: AdminUser,
) -> HTMLResponse:
    groups = await tags_grouped(session)
    return templates.TemplateResponse(
        request,
        "pages/admin_challenge.html",
        await view_context(
            request,
            session,
            user,
            tag_groups=groups,
            error=None,
        ),
    )


@router.post("/admin/defis")
async def admin_challenge_submit(
    request: Request,
    session: SessionDep,
    user: AdminUser,
    title: str = Form(...),
    description: str = Form(...),
    starts_at: str = Form(...),
    ends_at: str = Form(...),
    csrf: str = Form(...),
) -> Response:
    require_csrf(request, csrf)
    form = await request.form()
    raw_tags = form.getlist("tag_id")
    tag_ids = [
        int(value) for value in raw_tags if isinstance(value, str) and value.isdigit()
    ]
    start = datetime.fromisoformat(starts_at)
    end = datetime.fromisoformat(ends_at)
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    try:
        await create_challenge(
            session,
            title=title,
            description=description,
            starts_at=start,
            ends_at=end,
            tag_ids=tag_ids,
        )
    except ChallengeError:
        groups = await tags_grouped(session)
        return templates.TemplateResponse(
            request,
            "pages/admin_challenge.html",
            await view_context(
                request,
                session,
                user,
                tag_groups=groups,
                error=t("challenge_invalid"),
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse("/defi", status_code=status.HTTP_303_SEE_OTHER)
