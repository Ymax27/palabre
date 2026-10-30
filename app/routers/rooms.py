import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.bus import publish_room, subscribe_room
from app.core.deps import CurrentUser, OnboardedUser, SessionDep
from app.core.i18n import t
from app.core.limiter import limiter
from app.core.security import require_csrf
from app.core.templates import templates, view_context
from app.models.enums import PostType
from app.models.room import Room
from app.models.room_message import RoomMessage
from app.models.user import User
from app.services.qa import tags_grouped
from app.services.rooms import (
    RoomError,
    draft_from_thread,
    get_message,
    get_room_by_slug,
    last_messages,
    list_rooms,
    mark_needs_help,
    post_message,
)

router = APIRouter()


async def _room_or_404(session: AsyncSession, slug: str) -> Room:
    room = await get_room_by_slug(session, slug)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return room


def _message_html(
    message: RoomMessage,
    *,
    csrf: str,
    user: User | None,
    room_slug: str,
) -> str:
    return templates.env.get_template("partials/message.html").render(
        message=message,
        csrf=csrf,
        user=user,
        t=t,
        room_slug=room_slug,
    )


async def _message_in_room(
    session: AsyncSession,
    room: Room,
    message_id: int,
) -> RoomMessage:
    message = await get_message(session, message_id)
    if message is None or message.room_id != room.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return message


def _converted_location(message: RoomMessage) -> str | None:
    post = message.converted_post
    if post is None or message.converted_post_id is None:
        return None
    if post.type == PostType.RECETTE:
        return f"/recettes/{post.id}"
    return f"/questions/{post.id}"


@router.get("/salons", response_class=HTMLResponse)
async def rooms_index(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
) -> HTMLResponse:
    rooms = await list_rooms(session)
    return templates.TemplateResponse(
        request,
        "pages/rooms.html",
        await view_context(request, session, user, rooms=rooms),
    )


@router.get("/salons/{slug}", response_class=HTMLResponse)
async def room_detail(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    slug: str,
) -> HTMLResponse:
    room = await _room_or_404(session, slug)
    messages = await last_messages(session, room.id)
    return templates.TemplateResponse(
        request,
        "pages/room.html",
        await view_context(
            request,
            session,
            user,
            room=room,
            messages=messages,
        ),
    )


@router.post("/salons/{slug}/messages", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def room_post_message(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    slug: str,
    body: str = Form(...),
    csrf: str = Form(...),
    parent_id: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    require_csrf(request, csrf)
    room = await _room_or_404(session, slug)
    parent: int | None = None
    if parent_id and parent_id.isdigit():
        parent = int(parent_id)
    try:
        message = await post_message(
            session,
            room=room,
            author=user,
            body=body,
            parent_id=parent,
        )
    except RoomError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from None
    html = _message_html(message, csrf=csrf, user=user, room_slug=room.slug)
    await publish_room(room.id, json.dumps(html))
    return HTMLResponse(html)


@router.post("/salons/{slug}/messages/{message_id}/aide", response_class=HTMLResponse)
async def room_needs_help(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    slug: str,
    message_id: int,
    csrf: str = Form(...),
) -> HTMLResponse:
    require_csrf(request, csrf)
    room = await _room_or_404(session, slug)
    message = await _message_in_room(session, room, message_id)
    message = await mark_needs_help(session, message)
    html = _message_html(message, csrf=csrf, user=user, room_slug=room.slug)
    await publish_room(room.id, json.dumps(html))
    return HTMLResponse(html)


@router.get("/salons/{slug}/messages/{message_id}/convertir")
async def room_convert(
    request: Request,
    session: SessionDep,
    user: OnboardedUser,
    slug: str,
    message_id: int,
    vers: str = "question",
) -> Response:
    room = await _room_or_404(session, slug)
    message = await _message_in_room(session, room, message_id)
    existing = _converted_location(message)
    if existing is not None:
        return RedirectResponse(existing, status_code=status.HTTP_303_SEE_OTHER)
    if vers not in {"question", "recette"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    title, body = draft_from_thread(message)
    groups = await tags_grouped(session)
    template = "pages/ask.html" if vers == "question" else "pages/recipe_new.html"
    return templates.TemplateResponse(
        request,
        template,
        await view_context(
            request,
            session,
            user,
            tag_groups=groups,
            error=None,
            prefill_title=title,
            prefill_body=body,
            source_message_id=message.id,
        ),
    )


@router.get("/salons/{slug}/events")
async def room_events(
    session: SessionDep,
    slug: str,
) -> EventSourceResponse:
    room = await _room_or_404(session, slug)
    room_id = room.id

    async def _stream() -> AsyncIterator[dict[str, str]]:
        async for payload in subscribe_room(room_id):
            yield {"data": payload}

    return EventSourceResponse(_stream())
