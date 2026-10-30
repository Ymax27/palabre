import hashlib
import hmac
import secrets

from fastapi import HTTPException, Request, status
from itsdangerous import URLSafeTimedSerializer

from app.core.config import settings


def magic_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="palabre-magic")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return token


def require_csrf(request: Request, submitted: str) -> None:
    expected = request.session.get("csrf")
    if not isinstance(expected, str) or not submitted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf")
    if not hmac.compare_digest(expected, submitted):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf")
