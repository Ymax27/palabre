from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

from app.core.bus import subscribe_feed
from app.core.deps import CurrentUser, SessionDep
from app.core.templates import templates, view_context
from app.services.qa import list_questions, tags_grouped

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def feed(
    request: Request,
    session: SessionDep,
    user: CurrentUser,
    tag: str | None = None,
) -> HTMLResponse:
    questions = await list_questions(session, tag_slug=tag)
    groups = await tags_grouped(session)
    return templates.TemplateResponse(
        request,
        "pages/home.html",
        await view_context(
            request,
            session,
            user,
            questions=questions,
            tag_groups=groups,
            active_tag=tag,
        ),
    )


@router.get("/fil/events")
async def feed_events() -> EventSourceResponse:
    async def _stream() -> AsyncIterator[dict[str, str]]:
        yield {"comment": "connected"}
        async for payload in subscribe_feed():
            yield {"data": payload}

    return EventSourceResponse(_stream())
