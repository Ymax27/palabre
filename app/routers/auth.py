from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select

from app.core.countries import AFRICAN_COUNTRIES, COUNTRY_CODES
from app.core.deps import CurrentUser, LoginUser, SessionDep, is_onboarded
from app.core.security import csrf_token, require_csrf
from app.core.templates import templates
from app.models.tag import Tag
from app.models.user import User
from app.services.auth import MagicLinkError, consume_magic_link, request_magic_link

router = APIRouter()


def _client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host


@router.get("/connexion", response_class=HTMLResponse)
async def connexion_form(request: Request, user: CurrentUser) -> Response:
    if user is not None:
        target = "/" if is_onboarded(user) else "/onboarding"
        return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request,
        "pages/connexion.html",
        {"csrf": csrf_token(request)},
    )


@router.post("/connexion")
async def connexion_submit(
    request: Request,
    session: SessionDep,
    email: str = Form(...),
    csrf: str = Form(...),
) -> RedirectResponse:
    require_csrf(request, csrf)
    await request_magic_link(session, email=email, ip=_client_ip(request))
    return RedirectResponse("/connexion/envoyee", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/connexion/envoyee", response_class=HTMLResponse)
async def connexion_sent(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "pages/connexion_envoyee.html", {})


@router.get("/auth/magic")
async def magic_consume(
    request: Request,
    session: SessionDep,
    token: str = "",
) -> Response:
    try:
        user = await consume_magic_link(session, token)
    except MagicLinkError:
        return templates.TemplateResponse(
            request,
            "pages/magic_invalide.html",
            {},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    request.session["uid"] = user.id
    target = "/" if is_onboarded(user) else "/onboarding"
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_form(
    request: Request,
    session: SessionDep,
    user: LoginUser,
) -> Response:
    if is_onboarded(user):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    stack_stmt = select(Tag).where(Tag.category == "stack").order_by(Tag.label)
    stacks = (await session.scalars(stack_stmt)).all()
    return templates.TemplateResponse(
        request,
        "pages/onboarding.html",
        {
            "csrf": csrf_token(request),
            "countries": AFRICAN_COUNTRIES,
            "stacks": stacks,
            "error": None,
        },
    )


@router.post("/onboarding", response_class=HTMLResponse)
async def onboarding_submit(
    request: Request,
    session: SessionDep,
    user: LoginUser,
    handle: str = Form(...),
    country: str = Form(...),
    stack: str = Form(...),
    csrf: str = Form(...),
) -> Response:
    require_csrf(request, csrf)
    handle_clean = handle.strip().lstrip("@")
    stack_clean = stack.strip()
    country_clean = country.strip().upper()
    error: str | None = None
    if len(handle_clean) < 3 or len(handle_clean) > 40:
        error = "Le pseudo doit faire entre 3 et 40 caractères."
    elif not handle_clean.replace("_", "").isalnum():
        error = "Le pseudo n'accepte que des lettres, chiffres et _."
    elif country_clean not in COUNTRY_CODES:
        error = "Choisis un pays dans la liste."
    elif not stack_clean:
        error = "Indique ta stack principale."

    if error is None:
        taken = await session.scalar(
            select(User.id).where(User.handle == handle_clean, User.id != user.id)
        )
        if taken is not None:
            error = "Ce pseudo est déjà pris."

    if error is not None:
        stacks = (
            await session.scalars(
                select(Tag).where(Tag.category == "stack").order_by(Tag.label)
            )
        ).all()
        return templates.TemplateResponse(
            request,
            "pages/onboarding.html",
            {
                "csrf": csrf_token(request),
                "countries": AFRICAN_COUNTRIES,
                "stacks": stacks,
                "error": error,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user.handle = handle_clean
    user.country = country_clean
    user.stack = stack_clean[:80]
    await session.commit()
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/deconnexion")
async def logout(request: Request, csrf: str = Form(...)) -> RedirectResponse:
    require_csrf(request, csrf)
    request.session.clear()
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
