from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.i18n import t
from app.core.security import csrf_token
from app.models.user import User
from app.services.markdown import render_markdown
from app.services.xp import total_xp

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
def _md_filter(source: str | None) -> Markup:
    return Markup(render_markdown(source or ""))


templates.env.globals["t"] = t
templates.env.filters["md"] = _md_filter


async def view_context(
    request: Request,
    session: AsyncSession,
    user: User | None,
    **extra: Any,
) -> dict[str, Any]:
    xp = await total_xp(session, user) if user is not None else 0
    ctx: dict[str, Any] = {
        "user": user,
        "xp": xp,
        "csrf": csrf_token(request),
        "t": t,
    }
    ctx.update(extra)
    return ctx
