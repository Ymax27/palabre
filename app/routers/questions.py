from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, OnboardedUser, SessionDep
from app.core.i18n import t
from app.core.security import require_csrf
from app.core.templates import templates, view_context
from app.models.post import Post
from app.services.qa import (
    QaError,
    accept_answer,
    add_answer,
    get_question,
    mark_utile,
    tags_grouped,
    user_marked_utile,
    utile_count,
)
from app.services.qa import create_question as create_question_post

router = APIRouter()


async def _question_or_404(session: AsyncSession, question_id: int) -> Post:
    question = await get_question(session, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return question


@router.get("/questions/nouvelle", response_class=HTMLResponse)
async def ask_form(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
) -> HTMLResponse:
    groups = await tags_grouped(session)
    return templates.TemplateResponse(
        request,
        "pages/ask.html",
        await view_context(request, session, user, tag_groups=groups, error=None),
    )


@router.post("/questions")
async def ask_submit(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    title: str = Form(...),
    body: str = Form(...),
    csrf: str = Form(...),
) -> Response:
    require_csrf(request, csrf)
    form = await request.form()
    raw_tags = form.getlist("tag_id")
    tag_ids = [
        int(value) for value in raw_tags if isinstance(value, str) and value.isdigit()
    ]
    try:
        question = await create_question_post(
            session,
            author=user,
            title=title,
            body=body,
            tag_ids=tag_ids,
        )
    except QaError as exc:
        groups = await tags_grouped(session)
        if exc.code == "need_country":
            message = t("need_country_tag")
        else:
            message = "Question incomplète."
        return templates.TemplateResponse(
            request,
            "pages/ask.html",
            await view_context(
                request,
                session,
                user,
                tag_groups=groups,
                error=message,
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        f"/questions/{question.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/questions/{question_id}", response_class=HTMLResponse)
async def question_detail(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    question_id: int,
) -> HTMLResponse:
    question = await _question_or_404(session, question_id)
    utile_counts: dict[int, int] = {}
    utile_mine: dict[int, bool] = {}
    for answer in question.answers:
        utile_counts[answer.id] = len(answer.reactions)
        utile_mine[answer.id] = bool(
            user and any(r.user_id == user.id for r in answer.reactions)
        )
    return templates.TemplateResponse(
        request,
        "pages/question.html",
        await view_context(
            request,
            session,
            user,
            question=question,
            utile_counts=utile_counts,
            utile_mine=utile_mine,
        ),
    )


@router.post("/questions/{question_id}/reponses")
async def answer_submit(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    question_id: int,
    body: str = Form(...),
    csrf: str = Form(...),
) -> RedirectResponse:
    require_csrf(request, csrf)
    question = await _question_or_404(session, question_id)
    await add_answer(session, question=question, author=user, body=body)
    return RedirectResponse(
        f"/questions/{question_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/posts/{post_id}/utile", response_class=HTMLResponse)
async def utile_submit(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    post_id: int,
    csrf: str = Form(...),
) -> HTMLResponse:
    require_csrf(request, csrf)
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        count = await mark_utile(session, post=post, user=user)
    except QaError:
        count = await utile_count(session, post_id)
    marked = await user_marked_utile(session, user.id, post_id)
    return templates.TemplateResponse(
        request,
        "partials/utile.html",
        {
            "post_id": post_id,
            "count": count,
            "marked": marked,
            "csrf": csrf,
            "can_vote": post.author_id != user.id,
            "t": t,
        },
    )


@router.post("/questions/{question_id}/accepter/{answer_id}")
async def accept_submit(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    question_id: int,
    answer_id: int,
    csrf: str = Form(...),
) -> RedirectResponse:
    require_csrf(request, csrf)
    question = await _question_or_404(session, question_id)
    answer = await session.get(Post, answer_id)
    if answer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        await accept_answer(session, question=question, answer=answer, user=user)
    except QaError:
        pass
    return RedirectResponse(
        f"/questions/{question_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
