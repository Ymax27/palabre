# PALABRE · Plan d'action CADEV 2026

Version 1 · 27/10/2026 · Soumission visée : **dimanche 15/11 avant 12h GMT** (limite officielle 17h)

## 0. Décisions verrouillées

| Sujet | Décision |
|---|---|
| Nom | **Palabre** (l'arbre à palabres des devs africains) |
| Pitch (haut de l'accueil) | « Ici, les devs africains se répondent, se valident et font monter leur pays. » |
| Principe central | Le jeu découle de l'échange : **aucun point sans validation par un pair**. Bavarder ne rapporte rien. |
| Périmètre | Tout ce qui est en section 2 est dans le MVP livré. MVP-0 interne le 30/10. |
| Stack | Python : FastAPI, SQLAlchemy 2, PostgreSQL, Valkey, Jinja2 + HTMX + Alpine + Tailwind |
| Design | `DESIGN.md` : Stitch pour explorer, Figma pour finaliser, Cursor pour intégrer |
| Hébergement | VPS Datacloud **à Dakar** (le code promo de 40 % exclut seulement les VPS hors Dakar) |
| Hors périmètre | Messages privés, bot Telegram, doublons sémantiques (pgvector), traduction auto, paiements, app native, quiz du jour, webhooks |

Pourquoi ces exclusions : valeur faible pour le jury par rapport au coût, ou dépendance externe qui contredit la page « Souveraineté ».

## 1. Règlement : ce qui contraint le projet

| Règle | Conséquence |
|---|---|
| Soumission avant le 15/11 17h GMT, projet déployé et accessible | Déploiement continu dès le J1 |
| Au moins un produit Datacloud acquis (art. 6) | Acheter le VPS tôt et garder la facture |
| Licences GPL, AGPL, LGPL = irrecevable | Scan automatique en CI (section 7) |
| Création pendant le concours | Dépôt Git neuf, commits de tous les membres |
| Déclaration IA : outils et parties concernées | `docs/AI_USAGE.md` mis à jour à chaque PR (Cursor, Stitch, bots Grok) |
| Titularité : chaque membre déclare | Vérifier avec chacun aujourd'hui (employeur, école) |
| Vote des pairs 15/11 18h → 16/11 23h59 : obligatoire pour **chaque** membre | Alerte agenda pour les 4 |
| Jury 90 %, public 10 % | Qualité technique, pertinence et UX d'abord |
| Pays de représentation : définitif | Confirmer avant inscription |

À demander à cadev@systalink.com : images Docker (base Debian) = composants ? Correction possible après soumission ? Pays éligibles ? Renvois d'articles incohérents (art. 6 cite l'art. 9, remises à l'art. 8).

## 2. Fonctionnalités (MVP complet)

**A. Compte**
- Connexion par lien magique ou GitHub
- Onboarding en 3 étapes : pays, stacks, langue
- Profil public (pays, stacks, XP, réputation, badges, contributions)
- Export de ses données (JSON) et suppression du compte

**B. Questions et réponses**
- Poser une question : markdown, aperçu, code colorisé, bouton « copier »
- Tags de contexte obligatoires : pays, paiement, réseau, stack
- Répondre, **« Utile »** (vote positif uniquement), accepter une réponse
- « Moi aussi » (même problème), commentaires courts, suivre, historique d'édition
- Suggestion de doublons à la saisie (`pg_trgm`)

**C. Recettes**
- Fiche structurée : problème, solution, code, prérequis, versions, limites
- Création depuis une réponse acceptée ou depuis un salon
- **« Ça a marché chez moi »** : validation contextualisée (pays, environnement, date)
- Indicateur de fraîcheur (« à revérifier » après 6 mois) et signalement d'obsolescence

**D. Défi de la semaine**
- Publié le lundi, échéance le dimanche 20h GMT, rappel par email, podium le lundi
- Défis #1 (02/11), #2 (09/11), #3 (16/11), préparés à l'avance

**E. Jeu**
- Registre d'XP (plafond 100/jour), toast « +15 XP, le Sénégal monte de 2 places »
- Réputation permanente à 4 niveaux (débloque modération et édition)
- **Capitaine** : une contribution par semaine, points ×2 si validée
- Série d'utilité (répondre, valider, relire) avec un gel par semaine
- 6 badges maximum, tous liés à l'utilité
- Anti-triche : validateur de plus de 3 jours, votes réciproques plafonnés
- Les points n'apparaissent qu'après la première contribution

**F. Classements**
- **Coupe des Nations** : score d'un pays = moyenne de ses 10 meilleurs contributeurs, avec « forme » sur 5 semaines
- Classement individuel (onglets Semaine / Saison)
- Ligues privées avec code d'invitation et classement interne
- Saison 1 = 02/11 → 22/11 (une seule saison, pas de remise à zéro à gérer)

**G. Salons**
- Types : pays, stack, ligue, **Aide en direct** (rattaché à une question ouverte)
- Messages markdown avec code, historique 30 jours, présence simple, 3 réactions (✅ 🙏 🔥)
- **Convertir en question ou recette** : sélection de messages, attribution des aidants
- Mode lent, signalement, pas de liens pour les comptes de moins de 24 h
- Chat sans XP

**H. Découverte**
- Fil avec filtres pays/stack, onglets Récent, Actif, Sans réponse, Mes stacks
- Recherche full-text avec filtres de contexte, pages de tag
- **Palette de commandes (Ctrl/Cmd+K)** : recherche et saut vers salon, pays ou tag
- « Pour toi » : règle simple sur tes stacks, sans ML

**I. Notifications**
- Cloche in-app, emails (réponse, acceptation, validation, rappel de défi, résumé hebdo) avec préférences
- Mises à jour en direct des fils et des salons (SSE)

**J. Modération et admin**
- Signalements, file de modération, masquer, verrouiller, fusionner les doublons
- Limites de débit pour les nouveaux comptes, page code de conduite
- Back-office : utilisateurs, signalements, défis, paramètres XP

**K. Accessibilité et faible débit**
- Interface FR/EN, langue déclarée par post
- PWA, mode faible débit (bouton + Save-Data), lecture hors ligne des recettes enregistrées
- Navigation clavier, contrastes, thèmes clair et sombre

**L. Ouverture (« par les devs »)**
- API REST en lecture (questions, recettes, classements), OpenAPI, clé personnelle

**M. Transverse**
- Page « Comment ça marche » en un écran, **Mode juge** (visite de 90 s, comptes de démo)
- Page Souveraineté / statut du service, page santé de la communauté (rétention, délai médian de réponse)
- Confidentialité, états vides, 404

## 3. Architecture et données

**Composants**

| Couche | Choix |
|---|---|
| Backend | FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic, `asyncpg` |
| Base | PostgreSQL (`pg_trgm`, full-text) sur le VPS |
| Cache, pub/sub, classements | Valkey (ZSET pour les classements, pub/sub pour SSE) |
| Jobs | `arq` : cron des défis, séries, classements, emails, fraîcheur des recettes |
| Temps réel | SSE (`sse-starlette`) + POST ; reconnexion tolérante aux réseaux instables |
| Front | Jinja2 + HTMX + Alpine ; Tailwind CLI compilé ; aucun CDN en production |
| Auth et sécurité | `authlib`, `itsdangerous`, `argon2-cffi`, CSP stricte, CSRF, `slowapi` |
| Contenu | `markdown-it-py`, `nh3` (assainissement), Pygments |
| Déploiement | Docker Compose, Caddy (HTTPS), Uptime Kuma, Umami, `pg_dump` + `restic` |
| Email | SMTP transactionnel (Brevo ou Mailjet, à valider) |

**Tables principales** : `users`, `posts` (question, réponse, recette, commentaire), `tags`, `post_tags`, `reactions` (utile), `worked_reports` (ça a marché + pays + environnement), `xp_ledger` (xp, rep, saison, multiplicateur), `streaks`, `captain_picks`, `defis`, `leagues`, `league_members`, `badges`, `rooms`, `messages`, `message_reactions`, `notifications`, `reports`, `mod_actions`, `follows`, `post_edits`, `api_keys`.

**Règles du registre** : une ligne par événement ; le total est recalculé, jamais modifié à la main. Le plafond de 100 XP/jour et l'anti-réciprocité sont appliqués à l'écriture. La Coupe est recalculée toutes les 5 minutes par un job.

**Barème de départ (à calibrer)** : réponse acceptée +15, recette publiée +10, recette validée par un pair d'un autre pays +20 (auteur) et +3 (validateur), défi : podium +30/+20/+10.

**Budgets de performance** : page de fil ≤ 100 Ko compressée, JS ≤ 40 Ko, 3 fichiers de police maximum, Lighthouse ≥ 90, réponse serveur médiane < 200 ms.

## 4. Design et UX

Tout est dans `DESIGN.md` (identité, vocabulaire d'interactions, composants, écrans, prompts Stitch). Résumé du workflow :

1. **J1 (27–28/10)** : écrire/valider `DESIGN.md`, l'importer dans Stitch, générer les 10 écrans (desktop et mobile).
2. **J2–J3** : export vers Figma, construction à la main des 8 composants signature, thème clair/sombre. Stitch tend vers des patterns conventionnels : l'identité vient de nos tokens et de ces composants, pas de la génération.
3. **J3 → fin** : export HTML/Tailwind comme échafaudage, que Cursor convertit en partials Jinja/HTMX. Polices auto-hébergées (pas de Google Fonts en production).
4. **Tests** : test des 5 secondes sur 5 devs extérieurs (objectif 4/5), test de la première question (< 90 s).

À vérifier côté Stitch : quotas et conditions d'usage (outil récent, tarification évolutive) et déclaration dans `docs/AI_USAGE.md`.

## 5. Équipe (4) et outillage

| Rôle | Modules |
|---|---|
| **R1 Lead / Backend cœur** | Auth, Q&R, recettes, modèles, registre XP, déploiement |
| **R2 Temps réel et jeu** | Salons SSE, jobs, classements, notifications, emails, API |
| **R3 Front / UX** | Design system, templates, a11y, PWA, i18n, Ctrl+K |
| **R4 QA / Ops / Contenu** | CI/CD, Datacloud, sécurité, licences, tests, contenu de départ, entretiens, bêta, déclaration, démo |

Règles : toute PR est relue par un autre membre ; chacun doit savoir expliquer un module qu'il n'a pas écrit (répétition « swap » le 14/11) ; revue de 15 minutes chaque jour.

**Cursor** : `AGENTS.md` à la racine, règles dans `.cursor/rules/`, plan avant chaque tâche, petites PR, tests d'abord. Vérifie les options de ton abonnement.

**Bots Grok**
- **Architecte** : lit `AGENTS.md` + `PLAN.md`, produit des ADR de 10 lignes (décision, alternatives, raison) et vérifie la cohérence des modèles.
- **Jury simulé** : prompt basé sur l'annexe 1. Note chaque critère sur 20, cite les preuves (captures, repo), liste 3 faiblesses. Passages : 05/11, 13/11. Compare les écarts.
- **Conformité** : checklist des articles 4, 6 et 10 (licences, originalité, déclaration IA, titularité), rapport de licences de la CI, suivi de `docs/AI_USAGE.md`.

## 6. Calendrier (aujourd'hui mardi 27/10)

| Dates | Livrable |
|---|---|
| **Mar 27 – Mer 28/10** | Dépôt Git, VPS Dakar acheté avec le code promo, CI/CD, hello-world en HTTPS. Questions à l'organisateur. Titularité vérifiée. Entretiens lancés. `DESIGN.md` → Stitch. |
| **Jeu 29 – Ven 30/10** | **MVP-0 (R1)** : auth, profil, onboarding, fil, poser, répondre, Utile, accepter, tags de contexte, registre XP, pastille, Coupe v0, déployé. En parallèle : R2 écrit les ADR et le jeu de test du registre ; R3 Figma + tokens ; R4 CI, contenu de départ (tableur), entretiens. |
| **Sam 31/10** | Transmission de 2 h : chacun prend ses modules. |
| **Dim 01 – Jeu 05/11** | Recettes et « Ça a marché chez moi », Défi #1 publié le 02/11, ligues, Capitaine, séries, réputation, notifications et emails, recherche et doublons, modération de base. **Bêta fermée le 05/11 (30 invités).** Jury simulé #1. |
| **Ven 06 – Lun 09/11** | Salons SSE, Aide en direct, conversion en recette, Ctrl+K, PWA et faible débit, i18n EN, API, back-office, Mode juge. Bêta élargie le 09/11 (50 invités). Défi #2 publié le 09/11. |
| **Mar 10 – Mer 11/11** | Contenu de départ (50 entrées vérifiées), polish UX, accessibilité, états vides, santé de la communauté. **Gel des fonctionnalités mercredi 11/11 au soir.** |
| **Jeu 12 – Ven 13/11** | Tests de charge, audit sécurité et licences, restauration de sauvegarde testée, README, ADR, déclaration. Jury simulé #2. |
| **Sam 14/11** | Répétition de la démo (3 min), swap des modules, vidéo, soumission à blanc, relecture par une personne extérieure. |
| **Dim 15/11** | **Soumission finale avant 12h.** Puis vote des pairs (18h) : chaque membre vote avant le 16/11 23h59. |
| **17 – 20/11** | Campagne publique : Défi #3 (16/11), ligues, contenu. Questions probables du jury préparées. Composition du jury publiée au plus tard le 20/11. |
| **21 – 22/11** | Notation du jury. Plateforme figée, correctifs critiques seulement. |

Aucune fonctionnalité n'est reportée par défaut : les jours 12–14/11 servent de marge pour absorber les imprévus, pas de nouvelles fonctionnalités.

**Plan de repli si la réalité contredit le calendrier** (à décider le 08/11, dans cet ordre) : badges, clé API, EN, hors-ligne des recettes, page santé.

**Réalité de l'engagement** : les vrais utilisateurs externes arrivent surtout le 15–16/11 (votants) et 21–22/11 (jury). Les chiffres de rétention avant la soumission seront modestes : la bêta de 30 puis 50 invités sert à avoir une activité réelle et des citations, pas des statistiques impressionnantes. Présente-les honnêtement.

## 7. Qualité, sécurité, licences

**Qualité** : Ruff, mypy, pytest, Playwright (parcours : inscription → question → réponse → acceptation → XP ; validation d'une recette ; conversion d'un salon), Locust (200 utilisateurs simultanés), Bandit, `pip-audit`, `gitleaks`, pre-commit, GitHub Actions.

**Sécurité** : CSP stricte, CSRF, assainissement du markdown, `argon2`, cookies sécurisés, limites de débit, aucune clé dans le dépôt, sauvegarde quotidienne avec restauration testée.

**Licences** (d'après mes connaissances ; le scan CI fait foi)

| À utiliser | À éviter |
|---|---|
| FastAPI, Starlette, Uvicorn, SQLAlchemy, Alembic, Pydantic, `asyncpg`, Jinja2, HTMX, Alpine, Tailwind, `authlib`, `argon2-cffi`, `markdown-it-py`, `nh3`, Pygments, Babel, `arq`, `sse-starlette`, `slowapi`, `httpx`, Valkey, PostgreSQL, Caddy, Uptime Kuma, Umami | `psycopg` (LGPL), `python-telegram-bot` (LGPL), `chardet` (LGPL), `paramiko` (LGPL), MinIO et Grafana (AGPL), Plausible (AGPL), Redis 8+ en mode AGPL, Sentry auto-hébergé |

Commande CI : `pip-licenses --fail-on="GNU;LGPL;AGPL"` + inventaire des fichiers front vendus (HTMX, Alpine) avec leurs licences dans `docs/THIRD_PARTY.md`.

## 8. Démo et soumission

**Script de 3 minutes** : (1) pitch d'une phrase et accueil ; (2) un dev de Dakar pose une question avec contexte Wave ; (3) un dev d'Abidjan répond, un autre clique « Ça a marché chez moi » ; (4) toast XP et la Coupe bouge ; (5) un salon d'Aide en direct converti en recette ; (6) mode faible débit. Chaque membre présente une partie.

**Checklist de soumission** : URL en HTTPS fonctionnelle, comptes de démo, `docs/AI_USAGE.md`, `docs/THIRD_PARTY.md`, déclaration de titularité de chaque membre, clé de répartition du prix déclarée, facture Datacloud, README avec décisions et non-objectifs.

## 9. Risques

| Risque | Parade |
|---|---|
| Plateforme vide à l'ouverture | 50 entrées de départ + bêta + Mode juge |
| Calendrier tendu | Tranches verticales déployées chaque jour, marge 12–14/11, plan de repli |
| Un membre qui ne comprend pas le code | Transmission du 31/10, revues croisées, swap du 14/11 |
| Triche sur les classements | Plafonds, ancienneté des validateurs, anti-réciprocité |
| Chat envahi | Pas d'XP, mode lent, limites, 30 jours d'historique |
| Dépendance à un outil IA | Chaque sortie est relue ; usage déclaré ; code expliqué par son propriétaire |

## 10. Actions aujourd'hui

1. Créer le dépôt, ajouter `AGENTS.md`, `PLAN.md`, `DESIGN.md`, `docs/AI_USAGE.md`.
2. Acheter le VPS Dakar avec le code promo, garder la facture.
3. Envoyer les questions à l'organisateur.
4. Chaque membre confirme sa titularité (employeur, école).
5. R3 importe `DESIGN.md` dans Stitch ; R4 lance les entretiens.
