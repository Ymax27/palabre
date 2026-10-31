from collections.abc import Awaitable, Callable
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth import github_verified_email, login_or_link_github

MakeUser = Callable[..., Awaitable[User]]


class _FakeResp:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def json(self) -> object:
        return self._payload


class _FakeGitHub:
    async def authorize_access_token(self, _request: object) -> dict[str, str]:
        return {"access_token": "test-token"}

    async def get(self, url: str, token: object = None) -> _FakeResp:
        _ = token
        if url == "user":
            return _FakeResp({"id": 4242, "login": "octo"})
        return _FakeResp(
            [{"email": "octo@test.tld", "primary": True, "verified": True}]
        )


async def test_link_existing_email(session: AsyncSession, make_user: MakeUser) -> None:
    existing = await make_user(email="octo@test.tld", handle="octo")
    linked = await login_or_link_github(session, github_id="99", email="octo@test.tld")
    assert linked.id == existing.id
    assert linked.github_id == "99"


async def test_create_user_from_github(session: AsyncSession) -> None:
    user = await login_or_link_github(session, github_id="7", email="new@test.tld")
    assert user.email == "new@test.tld"
    assert user.github_id == "7"
    assert user.handle is None


async def test_reconnect_by_github_id(session: AsyncSession) -> None:
    first = await login_or_link_github(session, github_id="7", email="a@test.tld")
    second = await login_or_link_github(session, github_id="7", email="other@test.tld")
    assert second.id == first.id


def test_github_verified_email_required() -> None:
    profile: dict[str, Any] = {"email": "hidden@test.tld"}
    assert github_verified_email(profile, None) is None
    unverified = [{"email": "x@t.tld", "verified": False}]
    assert github_verified_email(profile, unverified) is None
    assert (
        github_verified_email(
            profile,
            [{"email": "ok@test.tld", "primary": True, "verified": True}],
        )
        == "ok@test.tld"
    )


async def test_github_callback_simulated(
    client: AsyncClient,
    monkeypatch: Any,
) -> None:
    from app.core import oauth

    monkeypatch.setattr(oauth, "github_client", lambda: _FakeGitHub())
    response = await client.get("/auth/github/callback", follow_redirects=True)
    assert response.status_code == 200
    assert "Présente-toi" in response.text or "Pseudo" in response.text
