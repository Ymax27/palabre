from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.countries import AFRICAN_COUNTRIES
from app.core.deps import CurrentUser, OnboardedUser, SessionDep
from app.core.i18n import t
from app.core.limiter import limiter
from app.core.security import require_csrf
from app.core.templates import templates, view_context
from app.models.post import Post
from app.services.challenges import featured_challenge
from app.services.qa import tags_grouped
from app.services.recipes import (
    RecipeError,
    create_recipe,
    get_recipe,
    list_recipes,
    report_worked,
    worked_counts,
)
from app.services.toast import flash_xp_toast

router = APIRouter()


async def _recipe_or_404(session: AsyncSession, recipe_id: int) -> Post:
    recipe = await get_recipe(session, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return recipe


def _marche_error(code: str) -> str:
    messages = {
        "too_young": t("marche_too_young"),
        "own_post": t("marche_own"),
        "duplicate": t("marche_duplicate"),
        "bad_country": t("marche_bad_country"),
        "empty": t("marche_empty"),
    }
    return messages.get(code, t("marche_error"))


@router.get("/recettes", response_class=HTMLResponse)
async def recipes_index(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    tag: str | None = None,
) -> HTMLResponse:
    recipes = await list_recipes(session, tag_slug=tag)
    return templates.TemplateResponse(
        request,
        "pages/recipes.html",
        await view_context(request, session, user, recipes=recipes, active_tag=tag),
    )


@router.get("/recettes/nouvelle", response_class=HTMLResponse)
async def recipe_form(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    from_answer: int | None = None,
) -> HTMLResponse:
    groups = await tags_grouped(session)
    challenge = await featured_challenge(session)
    prefill_title = ""
    prefill_body = ""
    prefill_probleme = ""
    prefill_solution = ""
    if from_answer is not None:
        answer = await session.get(Post, from_answer)
        if answer is not None and answer.type == "answer" and answer.body:
            parent = (
                await session.get(Post, answer.parent_id) if answer.parent_id else None
            )
            prefill_title = (parent.title if parent and parent.title else "")[:200]
            prefill_body = answer.body
            prefill_probleme = parent.body if parent else ""
            prefill_solution = answer.body
    return templates.TemplateResponse(
        request,
        "pages/recipe_new.html",
        await view_context(
            request,
            session,
            user,
            tag_groups=groups,
            error=None,
            challenge=challenge,
            prefill_title=prefill_title,
            prefill_body=prefill_body,
            prefill_probleme=prefill_probleme,
            prefill_solution=prefill_solution,
        ),
    )


@router.post("/recettes")
@limiter.limit("10/minute")
async def recipe_submit(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    title: str = Form(...),
    body: str = Form(...),
    csrf: str = Form(...),
    source_message_id: str | None = Form(None),
    probleme: str = Form(""),
    solution: str = Form(""),
    code: str = Form(""),
    prerequis: str = Form(""),
    versions: str = Form(""),
    limites: str = Form(""),
) -> Response:
    require_csrf(request, csrf)
    form = await request.form()
    raw_tags = form.getlist("tag_id")
    tag_ids = [
        int(value) for value in raw_tags if isinstance(value, str) and value.isdigit()
    ]
    source_id = (
        int(source_message_id)
        if source_message_id and source_message_id.isdigit()
        else None
    )
    join = form.get("join_challenge")
    challenge_id = int(join) if isinstance(join, str) and join.isdigit() else None
    if not probleme.strip() or not solution.strip():
        groups = await tags_grouped(session)
        return templates.TemplateResponse(
            request,
            "pages/recipe_new.html",
            await view_context(
                request,
                session,
                user,
                tag_groups=groups,
                error=t("recipe_empty"),
                challenge=await featured_challenge(session),
                prefill_title=title,
                prefill_body=body,
                prefill_probleme=probleme,
                prefill_solution=solution,
                source_message_id=source_id,
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        recipe = await create_recipe(
            session,
            author=user,
            title=title,
            body=body,
            tag_ids=tag_ids,
            source_message_id=source_id,
            challenge_id=challenge_id,
            probleme=probleme,
            solution=solution,
            code=code,
            prerequis=prerequis,
            versions=versions,
            limites=limites,
        )
    except RecipeError as exc:
        groups = await tags_grouped(session)
        message = (
            t("need_country_tag") if exc.code == "need_country" else t("recipe_empty")
        )
        return templates.TemplateResponse(
            request,
            "pages/recipe_new.html",
            await view_context(
                request,
                session,
                user,
                tag_groups=groups,
                error=message,
                challenge=await featured_challenge(session),
                prefill_title=title,
                prefill_body=body,
                source_message_id=source_id,
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        f"/recettes/{recipe.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/recettes/{recipe_id}", response_class=HTMLResponse)
async def recipe_detail(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    recipe_id: int,
) -> HTMLResponse:
    recipe = await _recipe_or_404(session, recipe_id)
    marked = bool(
        user and any(report.user_id == user.id for report in recipe.worked_reports)
    )
    return templates.TemplateResponse(
        request,
        "pages/recipe.html",
        await view_context(
            request,
            session,
            user,
            recipe=recipe,
            counts=worked_counts(recipe),
            marked=marked,
            can_report=bool(
                user and user.handle and user.id != recipe.author_id and not marked
            ),
            countries=AFRICAN_COUNTRIES,
            error=None,
        ),
    )


@router.post("/recettes/{recipe_id}/marche", response_class=HTMLResponse)
async def marche_submit(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    recipe_id: int,
    csrf: str = Form(...),
    country: str = Form(...),
    environment: str = Form(...),
) -> HTMLResponse:
    require_csrf(request, csrf)
    recipe = await _recipe_or_404(session, recipe_id)
    error: str | None = None
    try:
        _report, awarded = await report_worked(
            session,
            recipe=recipe,
            user=user,
            country=country,
            environment=environment,
        )
        await flash_xp_toast(
            request,
            session,
            country=recipe.author.country if recipe.author else None,
            awarded=awarded,
        )
    except RecipeError as exc:
        error = _marche_error(exc.code)
    recipe = await _recipe_or_404(session, recipe_id)
    marked = any(report.user_id == user.id for report in recipe.worked_reports)
    return templates.TemplateResponse(
        request,
        "partials/marche.html",
        {
            "recipe": recipe,
            "user": user,
            "csrf": csrf,
            "counts": worked_counts(recipe),
            "marked": marked,
            "can_report": user.id != recipe.author_id and not marked,
            "countries": AFRICAN_COUNTRIES,
            "error": error,
            "t": t,
        },
    )
