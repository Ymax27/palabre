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
| authlib | BSD-3-Clause | OAuth GitHub (Starlette) |
| cryptography | Apache-2.0 OR BSD-3-Clause | Transitive directe d'authlib |
| joserfc | BSD-3-Clause | Transitive directe d'authlib |
| markdown-it-py | MIT | Rendu Markdown utilisateur |
| mdurl | MIT | Transitive directe de `markdown-it-py` |
| nh3 | MIT | Assainissement HTML après le rendu Markdown |
| HTMX 2.0.4 | BSD-2-Clause | Interactions partielles (fichier auto-hébergé `app/static/vendor/htmx.min.js`) |
| hatchling | MIT | Backend de build (`pyproject.toml`) |
| pytest | MIT | Tests (dev) |
| pytest-asyncio | Apache-2.0 | Tests async (dev) |
| ruff | MIT | Lint et format (dev) |
| mypy | MIT | Vérification de types (dev) |
| pip-licenses | MIT | Scan de licences (dev) |
| pre-commit | MIT | Hooks git (dev) |
