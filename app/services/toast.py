from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.countries import AFRICAN_COUNTRIES
from app.core.i18n import t
from app.services.ranking import country_rank, refresh_coupe

_LABELS = dict(AFRICAN_COUNTRIES)


async def flash_xp_toast(
    request: Request,
    session: AsyncSession,
    *,
    country: str | None,
    awarded: int,
) -> None:
    if awarded <= 0:
        return
    before = await country_rank(session, country) if country else None
    await refresh_coupe(session)
    after = await country_rank(session, country) if country else None
    if country and before is not None and after is not None and before - after > 0:
        request.session["toast"] = t("xp_toast_up").format(
            xp=awarded,
            country=_LABELS.get(country, country),
            places=before - after,
        )
        return
    request.session["toast"] = t("xp_toast_plain").format(xp=awarded)
