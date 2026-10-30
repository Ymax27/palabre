STRINGS: dict[str, str] = {
    "nav_home": "Accueil",
    "nav_coupe": "Coupe",
    "nav_ask": "Poser",
    "nav_rooms": "Salons",
    "nav_login": "Connexion",
    "nav_logout": "Déconnexion",
    "rooms_intro": "Des salons par pays et par thème. Le chat ne rapporte aucun XP.",
    "rooms_message": "Message (markdown)",
    "rooms_send": "Envoyer",
    "rooms_login": "pour écrire dans le salon.",
    "rooms_reconnect": "Connexion instable. On réessaie, ton texte est gardé.",
    "pitch": (
        "Ici, les devs africains se répondent, se valident et font monter leur pays."
    ),
    "feed_empty": "Personne n'a encore posé de question. Sois le premier sous l'arbre.",
    "answers_empty": "Personne n'a encore répondu. Sois le premier sous l'arbre.",
    "utile": "Utile",
    "accept": "Accepter",
    "accepted": "Réponse acceptée",
    "ask_title": "Poser une question",
    "need_country_tag": "Ajoute au moins un tag de pays.",
    "github_continue": "Continuer avec GitHub",
    "github_or": "ou par email",
    "nav_recipes": "Recettes",
    "nav_profile": "Profil",
    "recipes_title": "Recettes",
    "recipes_empty": (
        "Personne n'a encore partagé de recette. Sois le premier sous l'arbre."
    ),
    "recipe_new": "Partager une recette",
    "recipe_steps": "Étapes (markdown)",
    "recipe_publish": "Publier",
    "recipe_empty": "Recette incomplète.",
    "marche": "Ça a marché chez moi",
    "marche_env": "Environnement",
    "marche_done": "Tu as confirmé que ça a marché chez toi.",
    "marche_login": "pour confirmer que ça a marché chez toi.",
    "marche_too_young": (
        "Ton compte doit avoir au moins 3 jours pour valider une recette."
    ),
    "marche_own": "Tu ne peux pas valider ta propre recette.",
    "marche_duplicate": "Tu as déjà confirmé cette recette.",
    "marche_bad_country": "Choisis un pays dans la liste.",
    "marche_empty": "Indique l'environnement (versions, réseau, paiement).",
    "marche_error": "Impossible d'enregistrer cette validation.",
    "level_nouveau": "Nouveau",
    "level_membre": "Membre",
    "level_pilier": "Pilier",
    "level_ancien": "Ancien",
    "profile_questions": "Questions",
    "profile_answers": "Réponses",
    "profile_recipes": "Recettes",
    "profile_none": "Pas encore de contribution ici.",
}


def t(key: str) -> str:
    return STRINGS.get(key, key)
