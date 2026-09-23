from datetime import datetime, timezone

from flask import Blueprint, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, get_current_user, get_jwt_identity, jwt_required,
)
from sqlalchemy import func

from account_links import (
    frontend_link, reset_token, user_from_reset, user_from_verification, verification_token,
)
from extensions import db, bcrypt
from mailer import send_email
from models import User
from schemas import (
    EmailLinkRequest, ForgotPasswordRequest, LoginRequest, RegisterRequest, ResetPasswordRequest, parse_body,
)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

_dummy_password_hash = None


def _get_dummy_password_hash() -> str:
    """Hash factice, calculé une fois, pour vérifier un mot de passe même si le compte n'existe pas."""
    global _dummy_password_hash
    if _dummy_password_hash is None:
        _dummy_password_hash = bcrypt.generate_password_hash("mot-de-passe-factice").decode('utf-8')
    return _dummy_password_hash


def password_matches(password_hash: str, password: str) -> bool:
    try:
        return bcrypt.check_password_hash(password_hash, password)
    except ValueError:
        # Hash illisible (ex : anciens comptes anonymisés avec la valeur "deleted")
        return False


def _find_user_by_email(email: str):
    # Comparaison insensible à la casse : les anciens comptes ont pu être créés avec des majuscules
    return User.query.filter(func.lower(User.email) == email).first()


def _tokens_for(user: User) -> dict:
    return {
        "access_token": create_access_token(identity=str(user.id)),
        "refresh_token": create_refresh_token(identity=str(user.id)),
    }


@auth_bp.route('/register', methods=['POST'])
def register():
    payload = parse_body(RegisterRequest)

    if _find_user_by_email(payload.email):
        return jsonify({"error": "Cet email est déjà utilisé."}), 409

    hashed_password = bcrypt.generate_password_hash(payload.password).decode('utf-8')

    new_user = User(email=payload.email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    # Un envoi raté n'empêche pas l'inscription : le lien se redemande depuis « Mon compte »
    send_verification_email(new_user)

    return jsonify(_tokens_for(new_user)), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    payload = parse_body(LoginRequest)
    user = _find_user_by_email(payload.email)

    # On vérifie un hash même quand le compte n'existe pas : le temps de réponse
    # ne révèle pas si l'adresse e-mail est inscrite.
    password_hash = user.password if user else _get_dummy_password_hash()
    if password_matches(password_hash, payload.password) and user:
        return jsonify(_tokens_for(user)), 200

    return jsonify({"error": "Identifiants invalides."}), 401


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Échange un refresh token valide contre un nouvel access token."""
    return jsonify(access_token=create_access_token(identity=get_jwt_identity())), 200


# --- E-mails du compte ([ADR 0014](../docs/adr/0014-emails-du-compte.md)) ---

INVALID_LINK = "Ce lien n'est plus valable. Demandez-en un nouveau."
FORGOT_MESSAGE = ("Si un compte existe pour cette adresse, un e-mail vient de lui être envoyé, "
                  "avec un lien valable une heure.")

VERIFICATION_EMAIL = """Bonjour,

Pour confirmer l'adresse de votre compte Terminator, ouvrez ce lien (valable 7 jours) :

{link}

Si vous n'avez pas créé de compte, ignorez ce message.
"""

RESET_EMAIL = """Bonjour,

Pour choisir un nouveau mot de passe pour votre compte Terminator, ouvrez ce lien (valable une heure, une seule fois) :

{link}

Si vous n'avez rien demandé, ignorez ce message : votre mot de passe ne change pas.
"""


def send_verification_email(user: User) -> bool:
    link = frontend_link("/verify-email", verification_token(user))
    return send_email(user.email, "Confirmez votre adresse — Terminator", VERIFICATION_EMAIL.format(link=link))


def _mark_verified(user: User) -> None:
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc).replace(tzinfo=None)


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
        send_email(user.email, "Nouveau mot de passe — Terminator", RESET_EMAIL.format(link=link))
    return jsonify({"message": FORGOT_MESSAGE}), 200


@auth_bp.route('/password/reset', methods=['POST'])
def reset_password():
    payload = parse_body(ResetPasswordRequest)
    user = user_from_reset(payload.token)
    if not user:
        return jsonify({"error": INVALID_LINK}), 400

    user.password = bcrypt.generate_password_hash(payload.password).decode('utf-8')
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
