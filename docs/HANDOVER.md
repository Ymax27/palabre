# Transmission · Palabre (31/10)

Brief pour l'équipe après le MVP-0. Lire aussi [AGENTS.md](../AGENTS.md), [PLAN.md](../PLAN.md) et [DESIGN.md](../DESIGN.md).

## Lancer en local

```bash
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Ports 5432/6379 déjà pris : POSTGRES_PORT=5433 VALKEY_PORT=6380
docker compose up -d
alembic upgrade head
python -m app.seed
```

- Accueil : `http://localhost:8000/`
- Santé : `GET /health`
- `DEBUG=true` (défaut Compose) : le lien magique est **loggé**, pas envoyé par SMTP. Extraire : `docker compose logs app | grep '/auth/magic'`
- GitHub OAuth : renseigner `GITHUB_CLIENT_ID` et `GITHUB_CLIENT_SECRET` dans `.env` (jamais dans le code). Callback : `{APP_BASE_URL}/auth/github/callback`. Sans ces variables, le bouton GitHub est masqué.
- Seed : `python -m app.seed` (ou `docker compose exec app python -m app.seed`). Idempotent. Comptes `askia` / `bakary` / `amina` / `yaw` (SN, CI, KE, GH), déjà âgés de 10 jours.
- Tests : `DATABASE_URL=postgresql+asyncpg://palabre:palabre@localhost:5433/palabre pytest -q` si Postgres est sur 5433.
- Qualité : `ruff check . && ruff format --check . && mypy app` et `pip-licenses --fail-on="GNU;LGPL;AGPL"`

## Structure

```
app/
  main.py          # app FastAPI, middleware session, routeurs
  core/            # config, db, deps, i18n, oauth, sécurité, rate limit
  models/          # SQLAlchemy 2
  services/        # logique métier (xp, qa, recipes, auth, ranking, profile)
  routers/         # HTTP fin : valide, appelle un service, rend un partial
  templates/       # Jinja2 + partials HTMX
  static/          # CSS compilé, vendor/htmx.min.js (pas de CDN)
  seed.py          # python -m app.seed
migrations/
tests/
docs/              # AI_USAGE.md, THIRD_PARTY.md, ce fichier
```

## Règles (AGENTS.md)

- Tout est **async**, types partout. Ruff + mypy doivent passer.
- Routeurs fins ; le métier vit dans `app/services/`.
- Toute XP passe par `app/services/xp.py` (plafond 100/jour, anti-réciprocité, pas d'auto-crédit). Jamais d'UPDATE du total à la main.
- Markdown utilisateur : `markdown-it-py` puis **toujours** `nh3`.
- HTMX : partials HTML, pas de JSON sauf `/api/v1/*`.
- Licences GPL / AGPL / LGPL interdites. Nouvelle dépendance → `docs/THIRD_PARTY.md` + scan CI.
- Chaque PR met à jour `docs/AI_USAGE.md`.
- Pas de fonctionnalité hors `PLAN.md`. Petites PR, un sujet.

**Jeu** : Utile n'apporte pas d'XP. Accepter une réponse : +15. « Ça a marché » : +20 auteur / +3 validateur si **autre pays**, validateur ≥ 3 jours (`VALIDATOR_MIN_AGE_DAYS`). Publier une recette ne donne pas de points (pair only).

## Tâche de départ par rôle

### R2 · Temps réel et jeu

Premier livrable : salons SSE (`sse-starlette` déjà en dépendance) + job `arq` qui recalcule la Coupe (forme 5 semaines, ZSET Valkey). Lire PLAN.md §2 F/G/I. Ne pas toucher à `xp.py` sans revue R1.

### R3 · Front et Stitch

Importer `DESIGN.md` dans Stitch, générer accueil + recette + Coupe (desktop et mobile), puis tokens et composants signature (pastille contexte, bouton « Ça a marché », tableau Coupe). Contrast WCAG AA, clavier, pas de Google Fonts. Déclarer Stitch dans `AI_USAGE.md`.

### R4 · Tests, contenu, opérations

Playwright : inscription → question → réponse → acceptation → XP ; recette → « Ça a marché ». Préparer 50 fiches de contenu (tableur). VPS Dakar / Caddy / sauvegarde `pg_dump`. Vérifier la CI (`alembic upgrade head` avant pytest) et le scan de licences.
