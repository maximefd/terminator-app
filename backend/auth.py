from flask import Blueprint, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required
from sqlalchemy import func

from extensions import db, bcrypt
from models import User
from schemas import LoginRequest, RegisterRequest, parse_body

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
