# DANS backend/schemas.py
"""
Schémas de validation des requêtes de l'API (pydantic).

Chaque endpoint qui lit un corps JSON passe par `parse_body(Schema)` : toute entrée
invalide est rejetée avec une erreur 400 et un message en français, sans jamais
renvoyer la valeur reçue (pour ne pas refléter de mot de passe ou de contenu hostile).
"""

from typing import Annotated, Literal, TypeVar

from email_validator import EmailNotValidError, validate_email
from flask import request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, ValidationError, field_validator

# Lettres françaises (avec accents et ligatures)
LETTERS = "A-Za-zÀ-ÖØ-öø-ÿŒœÆæ"
# Un mot : commence et finit par une lettre ; tiret, apostrophe et espace autorisés à l'intérieur
WORD_PATTERN = rf"^[{LETTERS}][{LETTERS}'’ -]*[{LETTERS}]$"
# Un motif de recherche : lettres et « ? » (plus les séparateurs des mots composés)
MASK_PATTERN = rf"^[{LETTERS}?'’ -]+$"
# Un nom de dictionnaire : lettres, chiffres, espaces et ponctuation courante
DICTIONARY_NAME_PATTERN = r"^[\w '’().,:&!-]+$"

MAX_SEED = 2_147_483_647

DictionaryName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=DICTIONARY_NAME_PATTERN)
]


class RequestValidationError(Exception):
    """Corps de requête invalide : converti en réponse 400 par le gestionnaire d'erreurs."""

    def __init__(self, message: str, details: list[dict] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class ApiModel(BaseModel):
    # Les champs inconnus sont ignorés (le frontend peut envoyer plus que nécessaire)
    model_config = ConfigDict(extra="ignore")


# --- Authentification ---

class RegisterRequest(ApiModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=3, max_length=254)]
    # Pas de strip sur le mot de passe : les espaces font partie du secret
    password: Annotated[str, Field(min_length=8, max_length=128)]

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        try:
            validate_email(value, check_deliverability=False)
        except EmailNotValidError as exc:
            raise ValueError("adresse e-mail invalide") from exc
        return value


class LoginRequest(ApiModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=254)]
    # Pas de longueur minimale : les comptes créés avant la règle des 8 caractères doivent pouvoir se connecter
    password: Annotated[str, Field(min_length=1, max_length=128)]


# --- Dictionnaires personnels ---

class DictionaryCreateRequest(ApiModel):
    name: DictionaryName


class DictionaryUpdateRequest(ApiModel):
    name: DictionaryName | None = None
    is_active: StrictBool | None = None


class WordCreateRequest(ApiModel):
    mot: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=30, pattern=WORD_PATTERN)]
    definition: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None


# --- Recherche et génération ---

class SearchRequest(ApiModel):
    mask: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30, pattern=MASK_PATTERN)]
    limit: Annotated[int, Field(ge=1, le=500)] = 200


class GridSize(ApiModel):
    width: Annotated[int, Field(ge=2, le=20)] = 10
    height: Annotated[int, Field(ge=2, le=20)] = 10


GridWord = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=30, pattern=WORD_PATTERN)
]


class GenerateRequest(ApiModel):
    size: GridSize = Field(default_factory=GridSize)
    seed: Annotated[int, Field(ge=0, le=MAX_SEED)] | None = None
    use_global: StrictBool = True
    # Plafonds de garde uniquement : la vraie limite est le layout, vérifiée avant de résoudre (ADR 0007)
    must_words: Annotated[list[GridWord], Field(max_length=50)] = Field(default_factory=list)
    wish_words: Annotated[list[GridWord], Field(max_length=500)] = Field(default_factory=list)
    # Réglage de moteur, désactivé par défaut : trier les candidats par fréquence donne des mots
    # plus courants mais fait échouer les plus grandes grilles plus souvent (mesures dans
    # backend/benchmarks/README.md). `None` : réglage du solveur.
    # Les valeurs doivent rester celles de engine.grid_solver.FREQUENCY_MODES (vérifié par un test).
    frequency_mode: Literal["none", "exact", "band", "known", "tiebreak"] | None = None
    # Dictionnaires thématiques de l'auteur, versés au pool « souhaité » (ADR 0007). Plafond de
    # garde ; l'appartenance est vérifiée dans la route, qui répond 404 pour tout autre dictionnaire.
    wish_dictionary_ids: Annotated[list[Annotated[int, Field(ge=1)]], Field(max_length=10)] = Field(
        default_factory=list)


class GridCell(ApiModel):
    x: Annotated[int, Field(ge=0, le=19)]
    y: Annotated[int, Field(ge=0, le=19)]
    # Une case noire (définition) n'a pas de lettre : la chaîne vide est normale
    char: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2)] = ""
    is_black: StrictBool = False


class GridPlacedWord(ApiModel):
    text: GridWord
    x: Annotated[int, Field(ge=0, le=19)]
    y: Annotated[int, Field(ge=0, le=19)]
    direction: Literal["across", "down"]
    source: Literal["must", "wish", "common"]


class GridPayload(ApiModel):
    """La grille telle que `/api/grids/generate` l'a renvoyée, que l'on stocke sans la rejouer."""
    width: Annotated[int, Field(ge=2, le=20)]
    height: Annotated[int, Field(ge=2, le=20)]
    layout: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    seed: Annotated[int, Field(ge=0, le=MAX_SEED)] | None = None
    # 20 x 20 cases au plus, comme les bornes de largeur et de hauteur
    cells: Annotated[list[GridCell], Field(max_length=400)]
    words: Annotated[list[GridPlacedWord], Field(max_length=200)] = Field(default_factory=list)
    fill_ratio: Annotated[float, Field(ge=0, le=1)] = 0.0
    wish_ratio: Annotated[float, Field(ge=0, le=1)] = 0.0
    must_words: Annotated[list[GridWord], Field(max_length=50)] = Field(default_factory=list)


class SaveGridRequest(ApiModel):
    """Conserver une grille produite. Sans nom, la route en compose un à partir du format et de la date."""
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=DICTIONARY_NAME_PATTERN)
    ] | None = None
    grid: GridPayload


# Clé d'une définition : le mot, sa position et son sens — « PIANO-1-2-across »
DEFINITION_KEY_PATTERN = rf"^[{LETTERS}'’ -]{{2,30}}-\d{{1,2}}-\d{{1,2}}-(across|down)$"

DefinitionKey = Annotated[str, StringConstraints(strip_whitespace=True, pattern=DEFINITION_KEY_PATTERN)]
# Une définition de mots fléchés est courte par nature : elle doit tenir dans une demi-case
DefinitionText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]


class GridUpdateRequest(ApiModel):
    """Renommer une grille conservée, ou écrire ses définitions."""
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=DICTIONARY_NAME_PATTERN)
    ] | None = None
    # Envoyées en bloc : l'écran connaît toujours l'état complet de la grille qu'il affiche
    definitions: Annotated[dict[DefinitionKey, DefinitionText], Field(max_length=200)] | None = None


class DifficultyRequest(ApiModel):
    """Estimation de la difficulté d'une demande, sans générer : appelée à chaque frappe."""
    must_words: Annotated[list[GridWord], Field(max_length=50)] = Field(default_factory=list)
    # Facultatif : sans taille choisie, l'estimation agrège tous les formats
    size: GridSize | None = None


# --- Conversion des erreurs ---

FIELD_LABELS = {
    "grid": "grille",
    "cells": "cases",
    "words": "mots",
    "layout": "mise en page",
    "definitions": "définitions",
    "email": "e-mail",
    "password": "mot de passe",
    "name": "nom",
    "is_active": "actif",
    "mot": "mot",
    "definition": "définition",
    "mask": "motif",
    "limit": "limite",
    "size": "taille",
    "width": "largeur",
    "height": "hauteur",
    "seed": "seed",
    "use_global": "dictionnaire commun",
    "must_words": "mots obligatoires",
    "wish_words": "mots souhaités",
    "frequency_mode": "tri par fréquence",
    "wish_dictionary_ids": "dictionnaires thématiques",
}


def _field_label(location: tuple) -> str:
    names = [part for part in location if isinstance(part, str)]
    return FIELD_LABELS.get(names[-1], names[-1]) if names else "corps de la requête"


def _error_message(error: dict) -> str:
    """Traduit une erreur pydantic en message lisible, sans inclure la valeur reçue."""
    field = _field_label(error.get("loc", ()))
    context = error.get("ctx") or {}
    kind = error.get("type", "")

    if kind == "missing":
        return f"Le champ « {field} » est obligatoire."
    if kind == "string_too_short":
        return f"« {field} » doit contenir au moins {context.get('min_length')} caractère(s)."
    if kind == "string_too_long":
        return f"« {field} » doit contenir au plus {context.get('max_length')} caractères."
    if kind == "string_pattern_mismatch":
        return f"« {field} » contient des caractères non autorisés."
    if kind in ("int_parsing", "int_type", "int_from_float"):
        return f"« {field} » doit être un nombre entier."
    if kind == "greater_than_equal":
        return f"« {field} » doit être supérieur ou égal à {context.get('ge')}."
    if kind == "less_than_equal":
        return f"« {field} » doit être inférieur ou égal à {context.get('le')}."
    if kind in ("bool_type", "bool_parsing"):
        return f"« {field} » doit valoir vrai ou faux."
    if kind == "string_type":
        return f"« {field} » doit être un texte."
    if kind in ("model_type", "model_attributes_type", "dict_type"):
        return f"« {field} » doit être un objet."
    return f"« {field} » n'est pas valide."


T = TypeVar("T", bound=BaseModel)


def parse_body(model: type[T]) -> T:
    """Valide le corps JSON de la requête courante avec le schéma donné."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise RequestValidationError("Le corps de la requête doit être un objet JSON.")
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors(include_url=False, include_input=False)
        details = [
            {"field": ".".join(str(part) for part in err["loc"]), "message": _error_message(err)}
            for err in errors
        ]
        raise RequestValidationError(details[0]["message"], details) from None
