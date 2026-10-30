from datetime import UTC, datetime, timedelta

from itsdangerous import BadSignature, SignatureExpired
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.email import send_magic_link
from app.core.rate_limit import allow
from app.core.security import hash_token, magic_serializer
from app.models.magic_link import MagicLink
from app.models.user import User


class MagicLinkError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def request_magic_link(
    session: AsyncSession,
    *,
    email: str,
    ip: str,
) -> None:
    email = normalize_email(email)
    if not email or "@" not in email:
        return
    if not allow(f"magic-email:{email}", 5, 15 * 60):
        return
    if not allow(f"magic-ip:{ip}", 20, 60 * 60):
        return

    token = magic_serializer().dumps({"e": email})
    expires = datetime.now(UTC) + timedelta(seconds=settings.magic_link_ttl_seconds)
    session.add(
        MagicLink(
            email=email,
            token_hash=hash_token(token),
            expires_at=expires,
        )
    )
    await session.commit()
    url = f"{settings.app_base_url.rstrip('/')}/auth/magic?token={token}"
    await send_magic_link(email, url)


async def consume_magic_link(session: AsyncSession, token: str) -> User:
    try:
        payload = magic_serializer().loads(
            token,
            max_age=settings.magic_link_ttl_seconds,
        )
    except SignatureExpired as exc:
        raise MagicLinkError("expired") from exc
    except BadSignature as exc:
        raise MagicLinkError("invalid") from exc

    if not isinstance(payload, dict) or "e" not in payload:
        raise MagicLinkError("invalid")
    email = normalize_email(str(payload["e"]))

    stmt = select(MagicLink).where(MagicLink.token_hash == hash_token(token))
    link = await session.scalar(stmt)
    if link is None:
        raise MagicLinkError("invalid")
    if link.consumed_at is not None:
        raise MagicLinkError("reused")
    if link.expires_at <= datetime.now(UTC):
        raise MagicLinkError("expired")

    link.consumed_at = datetime.now(UTC)
    user_stmt = select(User).where(User.email == email)
    user = await session.scalar(user_stmt)
    if user is None:
        user = User(email=email)
        session.add(user)
        await session.flush()
    await session.commit()
    await session.refresh(user)
    return user
