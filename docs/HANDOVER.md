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

**Jeu** (PLAN §0, §2 E, §3) : Utile et chat = 0 XP. Accepter : +15. **Recette publiée : +10** (via `grant_recipe_published`, acteur système, plafond 100/j UTC). « Ça a marché » autre pays : +20 / +3 ; même pays : 0. Validateur &lt; 3 jours : l'action passe, 0 XP. **Anti-réciprocité** : 1 échange XP max entre deux mêmes comptes par jour UTC (hors acteur système ; une validation « Ça a marché » compte pour un échange). **Réputation** : `rep = delta` sur chaque ligne ; niveaux Nouveau 0 / Membre 15 / Pilier 100 / Ancien 500 ; édition dès Membre ; modération dès Pilier ; affichage profil + anneau. Capitaine : ×2 si validée (`multiplicateur`, puis plafond 100/j). Coupe = moyenne top 10, ZSET 5 min, sans bonus Capitaine. Défi : lundi → dimanche 20h GMT. Série + gel, 0 XP. Badge « testé en prod ». Params XP : constantes dans `xp.py` jusqu'au back-office 06–09/11 (voir `docs/adr/0001-xp-params-backoffice.md`).

## Tâche de départ par rôle

### R2 · Temps réel et jeu

Premier livrable : salons SSE (`sse-starlette` déjà en dépendance) + job `arq` `refresh_coupe` toutes les 5 min (ZSET `coupe:s1`). Lire PLAN.md §2 F/G/I. Ne pas toucher à `xp.py` sans revue R1.

### R3 · Front et Stitch

Importer `DESIGN.md` dans Stitch, générer accueil + recette + Coupe (desktop et mobile), puis tokens et composants signature (pastille contexte, bouton « Ça a marché », tableau Coupe). Contrast WCAG AA, clavier, pas de Google Fonts. Déclarer Stitch dans `AI_USAGE.md`.

### R4 · Tests, contenu, opérations

Parcours HTTP déjà couverts (pytest). Playwright n'est pas ajouté dans cette tranche (licence à vérifier + note ici). Préparer 50 fiches de contenu (tableur). VPS Dakar / Caddy / sauvegarde `pg_dump`. Vérifier la CI (`alembic upgrade head` avant pytest) et le scan de licences.

**Coupe** : lecture ZSET Valkey, pas de SQL live, pas de bonus Capitaine. Flèches via snapshot précédent. Podium de la semaine en tête.

**Capitaine** : l'auteur désigne une réponse ou recette par semaine (lundi UTC). ×2 seulement si un pair valide, via `multiplicateur` puis plafond 100/j.

**Séries** : table `streaks`, gel auto au premier trou de la semaine, 0 XP. Utile compte comme « relire ».

**Défis** : table `defis`, lundi 00:00 → dimanche 20:00 GMT. Seed #1 02/11 (« Timeout Wave : une recette qui tient »), #2 09/11, #3 16/11. Participation = post tagué ; podium = XP pair, +30/+20/+10 via `grant_xp`, plafond 100/j. Rappel email dimanche 16:00 GMT ; digest lundi 08:00 GMT → `/classement`. Carte défi (compte à rebours + participants) à droite sur l'accueil desktop et page `/defi`.

**Notifications** : cloche in-app (réponse, acceptation, validation, rappel, digest, Merci). Emails Brevo (`SMTP_*` dans `.env`) pour réponse / acceptation / validation / rappel / digest — prefs par type. Merci = in-app seulement, 0 XP. Envoi hors requête via arq.
