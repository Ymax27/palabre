from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.core.deps import CurrentUser, SessionDep
from app.core.i18n import t
from app.core.templates import templates, view_context
from app.services.profile import LEVEL_KEYS, get_public_profile

router = APIRouter()


@router.get("/u/{handle}", response_class=HTMLResponse)
async def public_profile(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    handle: str,
) -> HTMLResponse:
    profile = await get_public_profile(session, handle)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    niveau_label = t(LEVEL_KEYS[profile.niveau])
    return templates.TemplateResponse(
        request,
        "pages/profile.html",
        await view_context(
            request,
            session,
            user,
            profile=profile,
            niveau_label=niveau_label,
        ),
    )
