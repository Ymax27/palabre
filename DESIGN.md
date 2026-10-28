# DESIGN.md · Palabre

Format libre en Markdown, à adapter si Stitch demande une structure précise pour l'import.

## 1. Intention

Chaleureux, dense, rapide. Un site de devs qui ne ressemble pas à un template : sobriété partout, **une signature par écran**. Deux motifs d'identité : **l'anneau ouvert** (un cercle de palabre ouvert à celui qui arrive) et **le tableau de la Coupe** (esthétique de classement de football).

## 2. Principes

1. **Échanger d'abord** : l'accueil est un fil, jamais un classement.
2. **Jeu discret** : les points apparaissent après la première contribution et ne bloquent jamais une action.
3. **Rapide avant joli** : budgets de performance respectés (page ≤ 100 Ko, JS ≤ 40 Ko).
4. **Contexte visible** : pays, paiement et réseau sont toujours affichés sous forme de pastilles.
5. **Une signature par écran**, pas dix.

## 3. Tokens

```css
:root {
  /* Couleurs */
  --ink-900:#11122B; --ink-800:#1A1C3D; --ink-700:#2A2D55;
  --sand-50:#FAF6EF; --sand-100:#F1E9DB; --sand-300:#D9CDB6;
  --terra-500:#D9622B; --terra-600:#B94E1D;   /* action principale */
  --ochre-400:#E8A93B;                         /* XP, Capitaine */
  --leaf-500:#2F9E6B;                          /* « Ça a marché » */
  --info-500:#4F7CFF; --danger-500:#D64545;
  /* Formes */
  --r-sm:8px; --r-md:12px; --r-pill:999px;
  /* Espacement : échelle de 4 px */
  --s-1:4px; --s-2:8px; --s-3:12px; --s-4:16px; --s-6:24px; --s-8:32px;
  /* Mouvement */
  --t-fast:150ms; --t-base:200ms;
}
```

- **Thème clair** : fond `sand-50`, texte `ink-900`, cartes `white` + bordure `sand-300`.
- **Thème sombre** : fond `ink-900`, cartes `ink-800` + bordure `ink-700`, texte `sand-50`.
- Bouton principal : fond `terra-600`, texte blanc. **Vérifier tous les contrastes à l'outil (WCAG AA)** avant de figer.
- Profondeur par **bordures**, pas par ombres. Mouvement sobre, désactivé avec `prefers-reduced-motion`.

## 4. Typographie

| Usage | Police | Licence |
|---|---|---|
| Titres | Bricolage Grotesque | OFL |
| Interface | Inter | OFL |
| Code | JetBrains Mono | OFL |

À **auto-héberger** (woff2, sous-ensemble latin, `font-display: swap`), 3 fichiers maximum. Aucun Google Fonts en production. Vérifier les licences avant d'ajouter les fichiers au dépôt.

## 5. Voix et microcopy

Tutoiement, chaleureux, direct, sans argot appuyé. Exemples :
- État vide : « Personne n'a encore répondu. Sois le premier sous l'arbre. »
- Toast : « +15 XP. Le Sénégal monte de 2 places. »
- Série : « 4 jours d'entraide. Un gel te protège cette semaine. »
- Erreur réseau : « Connexion instable. On réessaie, ton texte est gardé. »

## 6. Vocabulaire d'interactions (l'identité dans les gestes)

| Geste | Libellé | Effet | Remplace |
|---|---|---|---|
| Voter | **Utile** | +1 sur le post, pas de vote négatif | le like / upvote générique |
| Valider | **Ça a marché chez moi** | Ouvre une feuille à 2 champs (pays prérempli, environnement). Alimente le badge « testé en prod » | un « merci » vide |
| Remercier | **Merci** | Notifie l'aidant, aucun XP | |
| Capitaine | **Brassard « C »** | Doubler une contribution par semaine | un booster abstrait |
| Chat | ✅ 🙏 🔥 | 3 réactions seulement | une palette d'emojis |

## 7. Composants signature (à dessiner à la main dans Figma)

1. **Bouton « Ça a marché chez moi »** + résumé sous le post : `✅ 14 · 🇸🇳 6  🇨🇮 4  🇰🇪 2`.
2. **Pastilles de contexte** : drapeau + paiement + réseau, discrètes et cliquables (filtre).
3. **Tableau de la Coupe** : rang, pays, score, **forme sur 5 semaines (points colorés)**, flèche de mouvement, ligne de qualification pour le top 3.
4. **Anneau d'avatar** : le contour indique la progression vers le niveau suivant ; ouvert pour un nouveau membre.
5. **Carte Défi de la semaine** : titre, compte à rebours (« Reste 2 j 4 h »), participants.
6. **Brassard Capitaine** : étoile ocre sur une contribution désignée.
7. **Toast XP** : bref, avec le mouvement du pays ; jamais de confettis, sauf un effet léger quand le Capitaine est validé.
8. **Barre de sélection du salon** : « Convertir en question / recette » apparaît quand on sélectionne des messages.

Aussi : palette de commandes **Ctrl/Cmd+K**, états vides illustrés avec le motif.

## 8. Mise en page et navigation

- **Desktop** : 3 colonnes. Gauche = navigation (Accueil, Salons, Coupe, Défi, Recettes). Centre = fil. Droite = Défi de la semaine + mini-tableau de la Coupe.
- **Mobile** : barre du bas à 5 onglets : Accueil, Salons, **Poser** (bouton central), Coupe, Profil.
- En-tête : recherche (Ctrl+K), cloche, pastille XP (visible après la première contribution), avatar.
- Raccourcis : `/` recherche, `n` nouvelle question.

## 9. Écrans (10)

1. Accueil / fil · 2. Question (détail) · 3. Poser une question · 4. Recette · 5. Coupe des Nations · 6. Salon (avec Aide en direct) · 7. Défi de la semaine · 8. Profil · 9. Onboarding (3 étapes) · 10. Mode juge (visite guidée)

## 10. Logo et motif

- **Logo** : un cercle presque fermé (anneau ouvert) avec un point à l'ouverture. Monogramme P possible.
- **Motif** : géométrique, inspiré des tissus (bogolan), en un seul ton, utilisé seulement dans les états vides, l'en-tête de la Coupe et les badges. Dessiné à la main (SVG), pas de visuels générés.

## 11. Accessibilité et faible débit

Contraste AA, navigation clavier complète, focus visible, cibles tactiles ≥ 44 px, textes alternatifs, thème clair/sombre selon le système. Mode faible débit : désactive les animations, charge les images à la demande, réduit les polices.

## 12. Workflow Stitch → Figma → Cursor

1. Importer ce fichier dans Stitch comme système de design (import de DESIGN.md signalé depuis mars 2026 dans mes recherches).
2. Générer les 10 écrans avec les prompts ci-dessous, en mobile et en desktop.
3. Exporter vers Figma, construire les 8 composants signature, définir les états (survol, vide, erreur, chargement).
4. Exporter le HTML/Tailwind comme échafaudage et le faire convertir par Cursor en partials Jinja/HTMX.
5. Déclarer Stitch dans `docs/AI_USAGE.md` ; vérifier quotas et conditions d'usage.

**Attention** : Stitch tend vers des patterns conventionnels. Si l'écran généré ressemble à un template, on retire le superflu et on réintroduit les composants signature.

## 13. Prompts Stitch

**Prompt maître**
> Palabre est une plateforme d'entraide pour développeurs africains : questions et réponses, recettes de solutions validées par des pairs, salons de discussion et un classement par pays appelé « Coupe des Nations ». Ton chaleureux, interface dense et rapide, thème clair et sombre. Utilise la palette, la typographie et les composants décrits dans le design system joint. Évite l'aspect template : sobre, avec une seule signature par écran.

**Accueil**
> Écran d'accueil desktop en 3 colonnes. Gauche : navigation. Centre : barre de recherche, trois actions (Chercher, Poser, Partager), puis un fil de questions avec pastilles de contexte (drapeau, Wave/Orange Money, réseau), un bouton « Utile » et un résumé « Ça a marché chez moi ». Droite : carte Défi de la semaine avec compte à rebours et mini-tableau de la Coupe.

**Coupe des Nations**
> Page de classement façon tableau de football : rang, pays avec drapeau, score, forme sur 5 semaines en points colorés, flèche de mouvement, les 3 premiers mis en évidence. En haut, le podium de la semaine. Style sobre, ocre pour les points.

**Question**
> Page de question : titre, pastilles de contexte, corps avec code, réponses triées. Chaque réponse a « Utile », « Ça a marché chez moi » avec drapeaux des pays, et un brassard Capitaine optionnel. Réponse acceptée mise en avant en vert.
