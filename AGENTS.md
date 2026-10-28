# AGENTS.md · Palabre

Brief partagé pour Cursor et les autres agents. Lire aussi `PLAN.md` (périmètre) et `DESIGN.md` (identité).

## Projet

Palabre : plateforme d'échange pour devs africains (Q&R, recettes validées par des pairs, salons, jeu d'XP et classement par pays). Concours CADEV 2026. Soumission : 15/11/2026 avant 12h GMT.

**Principe** : le jeu découle de l'échange. Aucun point sans validation par un pair. Le chat ne rapporte aucun XP.

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Alembic · Pydantic · `asyncpg` · PostgreSQL (`pg_trgm`) · Valkey · `arq` · `sse-starlette` · Jinja2 + HTMX + Alpine · Tailwind CLI · Docker Compose · Caddy.

## Structure

```
app/
  main.py            # création de l'app, montage des routeurs
  core/              # config, sécurité, dépendances, i18n
  models/            # SQLAlchemy
  schemas/           # Pydantic
  services/          # logique métier (xp, qa, recipes, rooms, ranking…)
  routers/           # HTTP fin : valide, appelle un service, renvoie une vue
  templates/         # base, pages, partials HTMX
  static/            # css compilé, htmx, alpine, polices (auto-hébergées)
  jobs/              # tâches arq (cron)
migrations/
tests/               # unit, integration, e2e (Playwright)
docs/                # AI_USAGE.md, THIRD_PARTY.md, adr/
```

## Conventions

- Tout est **async**. Type hints partout. Ruff + mypy doivent passer.
- Routeurs fins ; la logique métier vit dans `services/`.
- Les points XP passent **uniquement** par `services/xp.py` (une ligne de registre par événement, plafond 100/jour, anti-réciprocité). Ne jamais modifier un total à la main.
- Réponses HTMX : renvoyer des partials, pas du JSON, sauf pour `/api/v1/*`.
- Pas de SQL brut, sauf requêtes `pg_trgm` / full-text documentées.
- Markdown utilisateur : toujours passer par le rendu + `nh3`.
- Toutes les chaînes visibles passent par i18n (FR par défaut, EN).
- Aucune ressource externe en production (pas de CDN, pas de Google Fonts).
- Respecter `DESIGN.md` : tokens, pastilles de contexte, vocabulaire d'interactions (Utile, Ça a marché chez moi, Merci, Capitaine).

## Licences (strict)

Interdits : GPL, AGPL, LGPL. À éviter notamment : `psycopg`, `python-telegram-bot`, `chardet`, `paramiko`, MinIO, Grafana, Redis 8+ en AGPL. Toute nouvelle dépendance : vérifier la licence, l'ajouter à `docs/THIRD_PARTY.md`, laisser passer le scan CI.

## Usage de l'IA (obligatoire)

À chaque PR, mettre à jour `docs/AI_USAGE.md` : outil utilisé (Cursor, Stitch, bots Grok), partie du projet concernée. Le développeur qui fusionne doit pouvoir expliquer le code.

## Commandes

```bash
docker compose up -d                # postgres, valkey, app
alembic upgrade head
pytest -q
ruff check . && ruff format --check . && mypy app
pip-licenses --fail-on="GNU;LGPL;AGPL"
npx tailwindcss -i ... -o app/static/app.css   # ou le binaire standalone
```

## Méthode de travail

1. **Plan avant code** : décris les fichiers touchés et les tests, puis attends validation.
2. Petites PR (moins de 400 lignes), un sujet par PR, tests d'abord.
3. Si une règle ou une demande est ambiguë, pose la question au lieu de deviner.
4. Ne pas ajouter de fonctionnalité hors `PLAN.md`.

## Définition de « fini »

- Tests passent (unit + le parcours E2E concerné).
- Lint, types et scan de licences OK.
- Déployé en préproduction, vérifié sur mobile et en mode faible débit.
- Textes FR/EN, navigation clavier, contrastes OK.
- `docs/AI_USAGE.md` à jour, relu par un autre membre.

## Priorités de MVP-0 (30/10)

Auth (lien magique + GitHub) · profil avec pays · onboarding · fil · poser une question avec tags de contexte · répondre · Utile · accepter · registre XP · pastille XP · Coupe v0 · déploiement HTTPS avec CI.
