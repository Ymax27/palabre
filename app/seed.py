"""Remplir une base vide avec des comptes et contenus de démo."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal, engine
from app.models.tag import Tag
from app.models.user import User
from app.services.qa import add_answer, create_question
from app.services.recipes import create_recipe, report_worked

SENTINEL_EMAIL = "askia@demo.palabre.local"

_OLD = datetime.now(UTC) - timedelta(days=10)

_USERS: tuple[tuple[str, str, str, str, str], ...] = (
    (SENTINEL_EMAIL, "askia", "SN", "Python", "Wave timeout sur Orange"),
    ("bakary@demo.palabre.local", "bakary", "CI", "JavaScript", "MTN MoMo en 2G"),
    ("amina@demo.palabre.local", "amina", "KE", "Flutter", "M-Pesa hors réseau"),
    ("yaw@demo.palabre.local", "yaw", "GH", "Django", "MoMo Ghana timeout"),
)

_QUESTIONS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "askia",
        "Wave coupe à la confirmation",
        "Le callback Wave n'arrive jamais en 3G. Quel timeout vous mettez ?",
        ("sn", "wave", "3g", "python"),
    ),
    (
        "bakary",
        "MTN MoMo refuse le sandbox",
        "En Côte d'Ivoire le sandbox MoMo répond 403. Un header manquant ?",
        ("ci", "mtn-momo", "4g", "javascript"),
    ),
    (
        "amina",
        "Flutter et certificats interceptés",
        "Sur un réseau d'hôtel le handshake TLS casse. Vous pinnez comment ?",
        ("ke", "4g", "flutter"),
    ),
    (
        "yaw",
        "Django derrière un proxy 2G",
        "Les POST longs meurent. Keep-alive ou files d'attente ?",
        ("gh", "2g", "django"),
    ),
    (
        "askia",
        "Orange Money webhook en double",
        "Je reçois deux notifications pour un seul paiement.",
        ("sn", "orange-money", "4g", "fastapi"),
    ),
    (
        "bakary",
        "CORS et app Flutter web",
        "Les cookies de session ne passent pas depuis Flutter web.",
        ("ci", "4g", "flutter"),
    ),
    (
        "amina",
        "USSD qui expire trop vite",
        "Le menu USSD coupe à 20 s. Vous découpez comment les étapes ?",
        ("ke", "2g", "python"),
    ),
    (
        "yaw",
        "Logs trop lourds en fibre saturée",
        "Notre VPS Dakar saturé d'I/O. Rotation ou Valkey ?",
        ("gh", "fibre", "python"),
    ),
    (
        "askia",
        "pg_trgm trop lent sans index",
        "La recherche de questions rame. Vous avez un GIN ?",
        ("sn", "fibre", "python"),
    ),
    (
        "bakary",
        "HTMX et réseau instable",
        "Les partials se perdent. Vous retentez côté client ?",
        ("ci", "instable", "javascript"),
    ),
)

_RECIPES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "askia",
        "Retry Wave avec idempotence",
        "1. Clé d'idempotence par paiement.\n2. Timeout 15 s puis une seule relance.\n"
        "3. Journaliser le callback, jamais le montant deux fois.",
        ("sn", "wave", "3g", "python"),
    ),
    (
        "bakary",
        "Sandbox MTN MoMo derrière un proxy",
        "1. En-tête X-Target-Environment = sandbox.\n2. Certificat système à jour.\n"
        "3. Tester hors VPN d'entreprise.",
        ("ci", "mtn-momo", "4g", "javascript"),
    ),
    (
        "amina",
        "Pinning TLS léger en Flutter",
        "1. Extraire le SPKI.\n2. BadCertificateCallback strict hors debug.\n"
        "3. Prévoir un fallback documenté.",
        ("ke", "4g", "flutter"),
    ),
    (
        "yaw",
        "File d'attente Django en 2G",
        "1. Couper les vues longues.\n2. Celery/arq pour le webhook.\n"
        "3. Répondre 202 tout de suite.",
        ("gh", "2g", "django"),
    ),
    (
        "askia",
        "Dédupliquer un webhook Orange Money",
        "1. Unique (provider, txn_id).\n2. Traiter en upsert.\n"
        "3. Ignorer le second POST silencieusement.",
        ("sn", "orange-money", "4g", "fastapi"),
    ),
)

# (recipe_index, validator_handle, country, environment)
_VALIDATIONS: tuple[tuple[int, str, str, str], ...] = (
    (0, "bakary", "CI", "Node 20 · Wave · 4G Abidjan"),
    (1, "amina", "KE", "Chrome · MTN sandbox · 4G Nairobi"),
    (2, "yaw", "GH", "Flutter 3.24 · 4G Accra"),
    (3, "askia", "SN", "Django 5 · Orange · 2G Thiès"),
    (4, "amina", "KE", "FastAPI · Orange Money · Fibre"),
)


async def _tag(session: AsyncSession, slug: str) -> Tag:
    tag = await session.scalar(select(Tag).where(Tag.slug == slug))
    if tag is None:
        raise RuntimeError(f"tag manquant: {slug} (alembic upgrade head ?)")
    return tag


async def seed(session: AsyncSession) -> bool:
    already = await session.scalar(select(User).where(User.email == SENTINEL_EMAIL))
    if already is not None:
        return False

    users: dict[str, User] = {}
    for email, handle, country, stack, _note in _USERS:
        user = User(
            email=email,
            handle=handle,
            country=country,
            stack=stack,
            created_at=_OLD,
        )
        session.add(user)
        users[handle] = user
    await session.commit()
    for user in users.values():
        await session.refresh(user)

    for handle, title, body, slugs in _QUESTIONS:
        tags = [await _tag(session, slug) for slug in slugs]
        question = await create_question(
            session,
            author=users[handle],
            title=title,
            body=body,
            tag_ids=[tag.id for tag in tags],
        )
        if handle == "askia" and title.startswith("Wave"):
            await add_answer(
                session,
                question=question,
                author=users["bakary"],
                body=(
                    "Passe le timeout à 15 s et une clé d'idempotence. "
                    "Ça tient chez moi à Abidjan."
                ),
            )

    recipes = []
    for handle, title, body, slugs in _RECIPES:
        tags = [await _tag(session, slug) for slug in slugs]
        recipe = await create_recipe(
            session,
            author=users[handle],
            title=title,
            body=body,
            tag_ids=[tag.id for tag in tags],
        )
        recipes.append(recipe)

    for index, validator_handle, country, environment in _VALIDATIONS:
        await report_worked(
            session,
            recipe=recipes[index],
            user=users[validator_handle],
            country=country,
            environment=environment,
        )
    return True


async def main() -> None:
    async with SessionLocal() as session:
        created = await seed(session)
    await engine.dispose()
    if created:
        print("Seed OK : 4 comptes, 10 questions, 5 recettes, validations inter-pays.")
    else:
        print("Seed ignoré : les comptes de démo existent déjà.")


if __name__ == "__main__":
    asyncio.run(main())
