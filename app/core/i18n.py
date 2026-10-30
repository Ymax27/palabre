STRINGS: dict[str, str] = {
    "nav_home": "Accueil",
    "nav_coupe": "Coupe",
    "nav_ask": "Poser",
    "nav_login": "Connexion",
    "nav_logout": "Déconnexion",
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
}


def t(key: str) -> str:
    return STRINGS.get(key, key)
