from typing import Any, cast

from authlib.integrations.starlette_client import OAuthError  # type: ignore[import-untyped]
from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select

from app.core.config import settings
from app.core.countries import AFRICAN_COUNTRIES, COUNTRY_CODES
from app.core.deps import CurrentUser, LoginUser, SessionDep, is_onboarded
from app.core.oauth import github_client, github_configured
from app.core.security import csrf_token, require_csrf
from app.core.templates import templates
from app.models.tag import Tag
from app.models.user import User
from app.services.auth import (
    GitHubAuthError,
    MagicLinkError,
    consume_magic_link,
    github_verified_email,
    login_or_link_github,
    request_magic_link,
)

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
        {
            "csrf": csrf_token(request),
            "github_enabled": github_configured(),
        },
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


@router.get("/auth/github")
async def github_start(request: Request) -> Response:
    client = github_client()
    if client is None:
        return RedirectResponse("/connexion", status_code=status.HTTP_303_SEE_OTHER)
    redirect_uri = f"{settings.app_base_url.rstrip('/')}/auth/github/callback"
    return cast(Response, await client.authorize_redirect(request, redirect_uri))


@router.get("/auth/github/callback")
async def github_callback(request: Request, session: SessionDep) -> Response:
    client = github_client()
    if client is None:
        return RedirectResponse("/connexion", status_code=status.HTTP_303_SEE_OTHER)
    try:
        token = await client.authorize_access_token(request)
        profile_resp = await client.get("user", token=token)
        emails_resp = await client.get("user/emails", token=token)
        profile = cast(dict[str, Any], profile_resp.json())
        emails_raw = emails_resp.json()
        emails = emails_raw if isinstance(emails_raw, list) else None
        email = github_verified_email(profile, emails)
        github_id = str(profile.get("id") or "")
        if not email or not github_id:
            raise GitHubAuthError("no_email")
        user = await login_or_link_github(
            session,
            github_id=github_id,
            email=email,
        )
    except (OAuthError, GitHubAuthError, TypeError, ValueError, AttributeError):
        return templates.TemplateResponse(
            request,
            "pages/github_invalide.html",
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
