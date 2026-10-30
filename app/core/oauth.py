from typing import Any

from authlib.integrations.starlette_client import OAuth  # type: ignore[import-untyped]

from app.core.config import settings

oauth = OAuth()


def github_configured() -> bool:
    return bool(settings.github_client_id and settings.github_client_secret)


def github_client() -> Any | None:
    if not github_configured():
        return None
    return oauth.create_client("github")


if github_configured():
    oauth.register(
        name="github",
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )
