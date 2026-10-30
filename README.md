# Palabre

Ici, les devs africains se répondent, se valident et font monter leur pays.

Plateforme d'échange (questions, recettes, salons, XP et Coupe des Nations). Concours CADEV 2026.

- Périmètre et calendrier : [PLAN.md](PLAN.md)
- Conventions pour les agents et le code : [AGENTS.md](AGENTS.md)
- Identité visuelle : [DESIGN.md](DESIGN.md)

## Prérequis

- Python 3.12
- Docker et Docker Compose
- Un binaire [Tailwind CSS standalone](https://github.com/tailwindlabs/tailwindcss/releases) (v3) pour compiler le CSS en local

## Lancer en local

```bash
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

docker compose up -d
alembic upgrade head
# équivalent : docker compose exec app alembic upgrade head
python -m app.seed
# équivalent : docker compose exec app python -m app.seed
curl -sf localhost:8000/health
```

`/health` doit répondre `200` avec `{"status":"ok","database":"ok"}`. L'accueil (le fil) est sur `http://localhost:8000/`.

Les identifiants Postgres du `.env.example` et de Compose (`palabre` / `palabre`) sont des valeurs locales, pas des secrets. Si les ports 5432 ou 6379 sont déjà pris : `POSTGRES_PORT=5433 VALKEY_PORT=6380 docker compose up -d`. Avec Postgres sur 5433, les tests locaux : `DATABASE_URL=postgresql+asyncpg://palabre:palabre@localhost:5433/palabre pytest -q`.

## Parcours local (deux comptes)

`DEBUG=true` (valeur par défaut de Compose) : le lien magique n'est pas envoyé par SMTP, il est écrit dans les logs.

```bash
docker compose up -d
docker compose exec app alembic upgrade head
# extraire les deux liens : docker compose logs app | grep '/auth/magic'
```

1. Compte A : ouvrir le premier lien, remplir l'onboarding (pseudo, pays, stack).
2. Poser une question avec au moins un tag pays.
3. Compte B : ouvrir le second lien (autre navigateur ou fenêtre privée), onboarding.
4. Répondre à la question de A.
5. Compte A : **Utile** (aucun XP), puis **accepter**.
6. Compte B : pastille ocre **15 XP**. `http://localhost:8000/coupe` affiche le pays de B.

## CSS (Tailwind CLI standalone)

Pas de npm. Télécharger le binaire, puis :

```bash
./tailwindcss -i app/static/src.css -o app/static/app.css --minify
```

Exemple Linux x64 :

```bash
curl -fsSL -o tailwindcss \
  https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64
chmod +x tailwindcss
./tailwindcss -i app/static/src.css -o app/static/app.css --minify
```

L'image Docker compile `app.css` au build. Le fichier généré n'est pas versionné.

## Qualité

```bash
pytest -q
ruff check . && ruff format --check . && mypy app
pip-licenses --fail-on="GNU;LGPL;AGPL"
pre-commit install
```

`pytest` attend Postgres sur `DATABASE_URL` (Compose par défaut).

## Conventions

- Tout est async, avec des annotations de types.
- Les routeurs HTTP restent fins ; la logique métier vit dans `app/services/`.
- Les points XP passent uniquement par `app/services/xp.py`.
- Markdown utilisateur : rendu puis assainissement (`nh3`).
- Licences GPL, AGPL et LGPL interdites ; toute dépendance va dans [docs/THIRD_PARTY.md](docs/THIRD_PARTY.md).
