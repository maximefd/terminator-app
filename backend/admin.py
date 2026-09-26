"""Espace d'administration : le poste de pilotage ([ADR 0016](../docs/adr/0016-mesure-d-usage-sans-cookie.md), point 6).

- Le rôle se pose en ligne de commande (`flask admin grant ADRESSE`), sur une adresse confirmée, jamais par l'API.
- Les routes `/api/admin/*` répondent à tout autre compte, et à tout visiteur, le même 404 qu'une adresse
  inconnue : un jeton absent, expiré ou forgé ne change rien à la réponse.
- Elles ne donnent que des agrégats, en lecture seule.
- Chaque accès est journalisé, accepté ou refusé.

Le contrôle est fait une fois pour tout le blueprint (`before_request`) : une route ajoutée plus tard est protégée
d'office, et les tests d'autorisation l'énumèrent d'eux-mêmes.
"""

import logging

import click
from flask import Blueprint, abort, jsonify, request
from flask.cli import AppGroup
from flask_jwt_extended import get_current_user, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError
from sqlalchemy import func

import stats
from extensions import db
from models import User

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
logger = logging.getLogger(__name__)


@admin_bp.before_request
def admin_only():
    """L'administrateur passe ; tous les autres reçoivent le 404 d'une adresse inconnue."""
    # La requête préliminaire CORS ne porte ni session ni donnée : flask-cors y répond
    if request.method == "OPTIONS":
        return None
    try:
        verify_jwt_in_request()
        user = get_current_user()
    except (JWTExtendedException, PyJWTError):  # pas de session, jeton expiré, révoqué ou forgé
        user = None
    if user is None or not user.is_admin:
        logger.warning("Administration : accès refusé à %s %s (compte %s)", request.method, request.path,
                       user.id if user else "aucun")
        abort(404)
    logger.info("Administration : %s %s (compte %s)", request.method, request.path, user.id)
    return None


@admin_bp.get("/stats")
def usage_stats():
    """Les chiffres de `flask stats` : visiteurs, générations, comptes, erreurs, seuils de l'ADR 0013."""
    return jsonify(stats.as_json(stats.compute()))


# --- Le rôle, en ligne de commande seulement ---

admin_cli = AppGroup("admin", help="Rôle d'administrateur (ADR 0016) : posé ici, jamais par l'API.")


def _account(email: str) -> User:
    user = User.query.filter(func.lower(User.email) == email.strip().lower()).first()
    if user is None:
        raise click.ClickException(f"Aucun compte avec l'adresse {email}.")
    return user


@admin_cli.command("grant")
@click.argument("email")
def grant_command(email):
    """Donne le rôle à un compte dont l'adresse est confirmée."""
    user = _account(email)
    if user.email_verified_at is None:
        raise click.ClickException("Adresse non confirmée : le rôle ne se pose que sur une adresse confirmée "
                                   "(le lien reçu par e-mail).")
    user.is_admin = True
    db.session.commit()
    logger.warning("Administration : rôle donné au compte %s", user.id)
    click.echo(f"{user.email} est administrateur.")


@admin_cli.command("revoke")
@click.argument("email")
def revoke_command(email):
    """Retire le rôle."""
    user = _account(email)
    user.is_admin = False
    db.session.commit()
    logger.warning("Administration : rôle retiré au compte %s", user.id)
    click.echo(f"{user.email} n'est plus administrateur.")


@admin_cli.command("list")
def list_command():
    """Les comptes qui ont le rôle."""
    admins = User.query.filter_by(is_admin=True).order_by(User.id).all()
    if not admins:
        click.echo("Aucun administrateur.")
    for user in admins:
        click.echo(user.email)


def init_admin_cli(app) -> None:
    app.cli.add_command(admin_cli)
