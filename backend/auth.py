import base64
import hashlib
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token, decode_token, get_current_user, get_jwt, get_jwt_identity,
    jwt_required, set_access_cookies, set_refresh_cookies, unset_jwt_cookies, verify_jwt_in_request,
)
from sqlalchemy import func

from account_links import (
    frontend_link, reset_token, user_from_reset, user_from_verification, verification_token,
)
from extensions import db, bcrypt
from mailer import send_email
from models import RevokedToken, User
import usage
from schemas import (
    EmailLinkRequest, ForgotPasswordRequest, LoginRequest, RegisterRequest, ResetPasswordRequest, parse_body,
)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

_dummy_password_hash = None


def _get_dummy_password_hash() -> str:
    """Hash factice, calculé une fois, pour vérifier un mot de passe même si le compte n'existe pas."""
    global _dummy_password_hash
    if _dummy_password_hash is None:
        _dummy_password_hash = hash_password("mot-de-passe-factice")
    return _dummy_password_hash


# bcrypt ne lit que les 72 premiers octets d'un mot de passe, et depuis sa version 5 il refuse le reste (erreur
# 500 à l'inscription). Au-delà, on lui passe l'empreinte du mot de passe entier : chaque caractère compte, et
# les mots de passe plus courts, ceux de tous les comptes existants, sont traités exactement comme avant.
BCRYPT_MAX_BYTES = 72


def _bcrypt_input(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) <= BCRYPT_MAX_BYTES:
        return password
    return base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii")


def hash_password(password: str) -> str:
    return bcrypt.generate_password_hash(_bcrypt_input(password)).decode("utf-8")


def password_matches(password_hash: str, password: str) -> bool:
    try:
        return bcrypt.check_password_hash(password_hash, _bcrypt_input(password))
    except ValueError:
        # Hash illisible (ex : anciens comptes anonymisés avec la valeur "deleted")
        return False


def _find_user_by_email(email: str):
    # Comparaison insensible à la casse : les anciens comptes ont pu être créés avec des majuscules
    return User.query.filter(func.lower(User.email) == email).first()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _session_response(user: User, message: str, status: int):
    """Ouvre une session : les jetons partent en cookies httpOnly, jamais dans le corps ([ADR 0015](../docs/adr/0015-session-en-cookies.md)).

    Un jeton dans le corps serait lisible par le JavaScript de la page, donc par une faille XSS : c'est
    précisément ce que les cookies httpOnly évitent.
    """
    response = jsonify({"message": message})
    set_access_cookies(response, create_access_token(identity=str(user.id)))
    set_refresh_cookies(response, create_refresh_token(identity=str(user.id)))
    return response, status


def _revoke(jwt_data: dict) -> None:
    """Refuse désormais ce jeton, jusqu'à son expiration."""
    if db.session.get(RevokedToken, jwt_data["jti"]) is None:
        expires_at = datetime.fromtimestamp(jwt_data["exp"], timezone.utc).replace(tzinfo=None)
        db.session.add(RevokedToken(jti=jwt_data["jti"], expires_at=expires_at))


@auth_bp.route('/register', methods=['POST'])
def register():
    payload = parse_body(RegisterRequest)

    if _find_user_by_email(payload.email):
        return jsonify({"error": "Cet email est déjà utilisé."}), 409

    hashed_password = hash_password(payload.password)

    new_user = User(email=payload.email, password=hashed_password, last_login_at=_utcnow())
    db.session.add(new_user)
    db.session.commit()
    usage.describe("account", "register", user=new_user)
    # Un envoi raté n'empêche pas l'inscription : le lien se redemande depuis « Mon compte »
    send_verification_email(new_user)

    return _session_response(new_user, "Compte créé.", 201)


@auth_bp.route('/login', methods=['POST'])
def login():
    payload = parse_body(LoginRequest)
    user = _find_user_by_email(payload.email)

    # On vérifie un hash même quand le compte n'existe pas : le temps de réponse
    # ne révèle pas si l'adresse e-mail est inscrite.
    password_hash = user.password if user else _get_dummy_password_hash()
    if password_matches(password_hash, payload.password) and user:
        user.last_login_at = _utcnow()
        db.session.commit()
        usage.describe("account", "login", user=user)
        return _session_response(user, "Connecté.", 200)

    return jsonify({"error": "Identifiants invalides."}), 401


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Échange un refresh token valide contre un nouvel access token (cookie).

    Pas de rotation du refresh token : deux onglets qui renouvellent en même temps se déconnecteraient
    l'un l'autre. La révocation à la déconnexion et au changement de mot de passe couvre le vol (ADR 0015).
    """
    # Une session renouvelée compte comme une connexion : un compte utilisé n'est pas inactif. Une écriture
    # par jour au plus.
    user = get_current_user()
    if user and (user.last_login_at is None or _utcnow() - user.last_login_at > timedelta(days=1)):
        user.last_login_at = _utcnow()
        db.session.commit()
    response = jsonify({"message": "Session renouvelée."})
    set_access_cookies(response, create_access_token(identity=get_jwt_identity()))
    return response, 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Ferme la session : révoque ses jetons, et efface les cookies.

    Réussit toujours, même avec des jetons expirés ou déjà révoqués : on doit pouvoir se déconnecter.
    """
    try:
        verify_jwt_in_request(refresh=True, optional=True)
        refresh_data = get_jwt()
    except Exception:  # jeton expiré, révoqué, CSRF manquant : rien à révoquer, on efface quand même
        refresh_data = {}
    if refresh_data:
        _revoke(refresh_data)
    access_cookie = request.cookies.get(current_app.config["JWT_ACCESS_COOKIE_NAME"])
    if access_cookie:
        try:
            _revoke(decode_token(access_cookie))
        except Exception:
            pass  # déjà expiré ou illisible : il ne sert plus à rien
    # Ménage : un jeton expiré est refusé de toute façon, inutile de le garder
    RevokedToken.query.filter(RevokedToken.expires_at < _utcnow()).delete()
    db.session.commit()

    response = jsonify({"message": "Déconnecté."})
    unset_jwt_cookies(response)
    return response, 200


# --- E-mails du compte ([ADR 0014](../docs/adr/0014-emails-du-compte.md)) ---

INVALID_LINK = "Ce lien n'est plus valable. Demandez-en un nouveau."
FORGOT_MESSAGE = ("Si un compte existe pour cette adresse, un e-mail vient de lui être envoyé, "
                  "avec un lien valable une heure.")

VERIFICATION_EMAIL = """Bonjour,

Pour confirmer l'adresse de votre compte {site}, ouvrez ce lien (valable 7 jours) :

{link}

Si vous n'avez pas créé de compte, ignorez ce message.
"""

RESET_EMAIL = """Bonjour,

Pour choisir un nouveau mot de passe pour votre compte {site}, ouvrez ce lien (valable une heure, une seule fois) :

{link}

Si vous n'avez rien demandé, ignorez ce message : votre mot de passe ne change pas.
"""


def send_verification_email(user: User) -> bool:
    link = frontend_link("/verify-email", verification_token(user))
    site = current_app.config["SITE_NAME"]
    return send_email(user.email, f"Confirmez votre adresse — {site}", VERIFICATION_EMAIL.format(site=site, link=link))


def _mark_verified(user: User) -> None:
    if user.email_verified_at is None:
        user.email_verified_at = _utcnow()


@auth_bp.route('/password/forgot', methods=['POST'])
def forgot_password():
    """Envoie un lien pour choisir un nouveau mot de passe.

    La réponse est la même que le compte existe ou non, et que l'envoi réussisse ou non : cette route ne
    doit pas servir à savoir si une adresse est inscrite.
    """
    payload = parse_body(ForgotPasswordRequest)
    user = _find_user_by_email(payload.email)
    if user:
        link = frontend_link("/reset-password", reset_token(user))
        site = current_app.config["SITE_NAME"]
        send_email(user.email, f"Nouveau mot de passe — {site}", RESET_EMAIL.format(site=site, link=link))
    return jsonify({"message": FORGOT_MESSAGE}), 200


@auth_bp.route('/password/reset', methods=['POST'])
def reset_password():
    payload = parse_body(ResetPasswordRequest)
    user = user_from_reset(payload.token)
    if not user:
        return jsonify({"error": INVALID_LINK}), 400

    user.password = hash_password(payload.password)
    # Qui a changé le mot de passe veut aussi fermer les sessions ouvertes avec l'ancien (ADR 0015)
    user.sessions_revoked_at = _utcnow()
    # Le lien est arrivé par e-mail : s'en servir prouve aussi que l'adresse est la bonne
    _mark_verified(user)
    db.session.commit()
    return jsonify({"message": "Mot de passe changé. Vous pouvez vous connecter."}), 200


@auth_bp.route('/email/verify', methods=['POST'])
def verify_email():
    payload = parse_body(EmailLinkRequest)
    user = user_from_verification(payload.token)
    if not user:
        return jsonify({"error": INVALID_LINK}), 400

    _mark_verified(user)
    db.session.commit()
    usage.describe("account", "verify", user=user)
    return jsonify({"message": "Adresse confirmée."}), 200


@auth_bp.route('/email/resend', methods=['POST'])
@jwt_required()
def resend_verification():
    user = get_current_user()
    if user.email_verified_at is not None:
        return jsonify({"message": "Votre adresse est déjà confirmée."}), 200
    if not send_verification_email(user):
        return jsonify({"error": "L'e-mail n'a pas pu partir. Réessayez dans quelques minutes."}), 503
    return jsonify({"message": f"E-mail envoyé à {user.email}."}), 200
