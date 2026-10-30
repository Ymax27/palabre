from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from app.core.bus import close_redis
from app.core.config import settings
from app.core.db import engine
from app.core.limiter import limiter, rate_limit_exceeded_handler
from app.routers import (
    auth,
    coupe,
    health,
    home,
    profile,
    questions,
    recipes,
    rooms,
    search,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=settings.session_cookie_name,
        https_only=not settings.debug,
        same_site="lax",
        max_age=14 * 24 * 3600,
    )
    application.state.limiter = limiter
    application.add_exception_handler(
        RateLimitExceeded,
        rate_limit_exceeded_handler,  # type: ignore[arg-type]
    )
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    application.include_router(health.router)
    application.include_router(home.router)
    application.include_router(auth.router)
    application.include_router(search.router)
    application.include_router(questions.router)
    application.include_router(recipes.router)
    application.include_router(profile.router)
    application.include_router(coupe.router)
    application.include_router(rooms.router)
    return application


app = create_app()
