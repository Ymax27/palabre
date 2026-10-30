from enum import StrEnum


class PostType(StrEnum):
    QUESTION = "question"
    ANSWER = "answer"
    RECETTE = "recette"


class PostStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    HIDDEN = "hidden"


class TagCategory(StrEnum):
    PAYS = "pays"
    PAIEMENT = "paiement"
    RESEAU = "reseau"
    STACK = "stack"


class ReactionKind(StrEnum):
    UTILE = "utile"


class XpReason(StrEnum):
    ANSWER_ACCEPTED = "answer_accepted"
    RECIPE_PUBLISHED = "recipe_published"
    RECIPE_VALIDATED_AUTHOR = "recipe_validated_author"
    RECIPE_VALIDATED_VALIDATOR = "recipe_validated_validator"
