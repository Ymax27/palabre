from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.db import SessionLocal

router = APIRouter()


@router.get("/health")
async def health() -> JSONResponse:
    # SELECT 1 : sonde de santé, pas du SQL métier (exception à AGENTS.md).
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "database": "error"},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "ok", "database": "ok"},
    )
