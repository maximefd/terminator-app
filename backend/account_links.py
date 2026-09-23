# DANS backend/account_links.py
"""
Liens signés envoyés par e-mail : confirmer son adresse, changer son mot de passe
([ADR 0014](../docs/adr/0014-emails-du-compte.md)).

Pas de table en base : le lien porte l'identifiant du compte, signé avec `SECRET_KEY` (itsdangerous) et daté.
- **Confirmation d'adresse** : valable 7 jours, et seulement pour l'adresse qu'il nomme.
- **Mot de passe** : valable une heure, et une seule fois. Il porte une empreinte du mot de passe actuel, qui
  change dès qu'on s'en sert : le même lien ne peut pas servir deux fois, ni après un autre changement.
"""

import hashlib

from flask import current_app
from itsdangerous import BadSignature, URLSafeTimedSerializer

from models import User, db

VERIFICATION_SALT = "confirmation-adresse"
RESET_SALT = "mot-de-passe-oublie"
VERIFICATION_MAX_AGE_S = 7 * 24 * 3600
RESET_MAX_AGE_S = 3600


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=salt)


def _fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def _load(salt: str, token: str, max_age: int) -> dict | None:
    try:
        data = _serializer(salt).loads(token, max_age=max_age)
    except BadSignature:  # signature fausse, lien tronqué ou expiré (SignatureExpired en hérite)
        return None
    return data if isinstance(data, dict) and isinstance(data.get("u"), int) else None


def verification_token(user: User) -> str:
    return _serializer(VERIFICATION_SALT).dumps({"u": user.id, "e": user.email})


def reset_token(user: User) -> str:
    return _serializer(RESET_SALT).dumps({"u": user.id, "p": _fingerprint(user.password)})


def user_from_verification(token: str) -> User | None:
    data = _load(VERIFICATION_SALT, token, VERIFICATION_MAX_AGE_S)
    user = db.session.get(User, data["u"]) if data else None
    return user if user and user.email == data.get("e") else None


def user_from_reset(token: str) -> User | None:
    data = _load(RESET_SALT, token, RESET_MAX_AGE_S)
    user = db.session.get(User, data["u"]) if data else None
    return user if user and _fingerprint(user.password) == data.get("p") else None


def frontend_link(path: str, token: str) -> str:
    """Lien vers une page du frontend : c'est elle qui renvoie le jeton à l'API."""
    return f"{current_app.config['FRONTEND_URL'].rstrip('/')}{path}?token={token}"
