from fastapi.responses import HTMLResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.i18n import t


def rate_key(request: Request) -> str:
    uid = request.session.get("uid")
    if isinstance(uid, int):
        return f"uid:{uid}"
    return get_remote_address(request) or "anonymous"


limiter = Limiter(key_func=rate_key, default_limits=[])


def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> HTMLResponse:
    return HTMLResponse(t("rate_limited"), status_code=429)
