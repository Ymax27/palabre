# Dépendances tierces

Licences des dépendances directes. Interdites : GPL, AGPL, LGPL. Le scan CI (`pip-licenses --fail-on="GNU;LGPL;AGPL"`) fait foi pour les transitives.

| Composant | Licence | Usage |
|---|---|---|
| fastapi | MIT | API HTTP async |
| uvicorn | BSD-3-Clause | Serveur ASGI (`[standard]`) |
| sqlalchemy | MIT | ORM async (`[asyncio]` ≥ 2) |
| asyncpg | Apache-2.0 | Pilote PostgreSQL async |
| alembic | MIT | Migrations |
| pydantic-settings | MIT | Configuration par variables d'environnement |
| jinja2 | BSD-3-Clause | Templates HTML |
| python-multipart | Apache-2.0 | Formulaires et fichiers |
| itsdangerous | BSD-3-Clause | Jetons signés (auth) |
| argon2-cffi | MIT | Hachage de secrets |
| httpx | BSD-3-Clause | Client HTTP async |
| sse-starlette | BSD-3-Clause | Server-Sent Events |
| hatchling | MIT | Backend de build (`pyproject.toml`) |
| pytest | MIT | Tests (dev) |
| pytest-asyncio | Apache-2.0 | Tests async (dev) |
| ruff | MIT | Lint et format (dev) |
| mypy | MIT | Vérification de types (dev) |
| pip-licenses | MIT | Scan de licences (dev) |
| pre-commit | MIT | Hooks git (dev) |
