# DANS backend/security.py
"""
Mesures de sécurité transverses de l'API :
- gestionnaires d'erreurs JSON (jamais de stack trace ni de détail interne) ;
- en-têtes de sécurité HTTP ;
- callbacks JWT (messages en français, utilisateur supprimé => 401) ;
- limitation de débit (rate limiting) des endpoints sensibles.

Voir docs/SECURITY.md pour le modèle de menace et les limites connues.
"""

import ipaddress
import logging

from flask import Flask, current_app, json, jsonify, request
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException

from models import User, db
from schemas import RequestValidationError

HTTP_ERROR_MESSAGES = {
    400: "Requête invalide.",
    401: "Authentification requise.",
    403: "Accès refusé.",
    404: "Ressource introuvable.",
    405: "Méthode non autorisée.",
    413: "Requête trop volumineuse.",
    415: "Type de contenu non supporté.",
    429: "Trop de requêtes. Réessayez dans quelques instants.",
    500: "Erreur interne du serveur.",
}

# L'API ne sert que du JSON : politique la plus stricte possible
API_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}

# Endpoint Flask -> clé de configuration contenant sa limite (ex: "10 per minute")
RATE_LIMITED_ENDPOINTS = {
    "auth.login": "RATELIMIT_LOGIN",
    # Vérifie un mot de passe, comme la connexion : même plafond contre la force brute
    "main.delete_self": "RATELIMIT_LOGIN",
    # Chaque appel envoie un e-mail : un plafond bas, sinon l'API sert à arroser une boîte
    "auth.forgot_password": "RATELIMIT_EMAIL_SEND",
    "auth.resend_verification": "RATELIMIT_EMAIL_SEND",
    "auth.reset_password": "RATELIMIT_LOGIN",
    "auth.verify_email": "RATELIMIT_LOGIN",
    "auth.register": "RATELIMIT_REGISTER",
    "auth.refresh": "RATELIMIT_REFRESH",
    "main.search_words": "RATELIMIT_SEARCH",
    "main.grid_difficulty": "RATELIMIT_DIFFICULTY",
    "main.generate_grid": "RATELIMIT_GENERATE",
}


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(RequestValidationError)
    def handle_validation_error(error: RequestValidationError):
        return jsonify({"error": error.message, "details": error.details}), 400

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        # On garde la réponse d'origine (en-têtes Allow, Retry-After...) avec un corps JSON en français
        response = error.get_response()
        code = error.code or 500
        response.set_data(json.dumps({"error": HTTP_ERROR_MESSAGES.get(code, error.name)}))
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        # Le détail part dans les logs serveur, jamais dans la réponse
        logging.exception("Erreur non gérée sur %s %s", request.method, request.path)
        return jsonify({"error": HTTP_ERROR_MESSAGES[500]}), 500


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def set_security_headers(response):
        for name, value in API_SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if app.config.get("APP_ENV") == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


def register_jwt_callbacks(jwt: JWTManager) -> None:
    @jwt.user_lookup_loader
    def load_user(_jwt_header, jwt_data):
        try:
            user_id = int(jwt_data["sub"])
        except (KeyError, TypeError, ValueError):
            return None
        return db.session.get(User, user_id)

    @jwt.user_lookup_error_loader
    def user_not_found(_jwt_header, _jwt_data):
        return jsonify({"error": "Compte introuvable. Veuillez vous reconnecter."}), 401

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return jsonify({"error": HTTP_ERROR_MESSAGES[401]}), 401

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return jsonify({"error": "Jeton d'authentification invalide."}), 401

    @jwt.expired_token_loader
    def expired_token(_jwt_header, _jwt_data):
        return jsonify({"error": "Session expirée. Veuillez vous reconnecter.", "code": "token_expired"}), 401


def client_ip() -> str:
    """Adresse du visiteur : clé du rate limiting et de la limite de générations simultanées.

    Derrière Cloudflare Tunnel, toutes les requêtes arrivent de cloudflared, donc de la même adresse :
    le limiteur bloquerait tous les visiteurs ensemble ([ADR 0013](../docs/adr/0013-cible-hebergement-production.md)).
    Cloudflare transmet la vraie adresse dans `CF-Connecting-IP`. L'en-tête n'est lu que si
    `CLIENT_IP_HEADER` le désigne : sans tunnel devant l'API, n'importe quel client pourrait
    l'inventer et changer d'adresse à chaque requête pour échapper aux limites.
    """
    header = current_app.config.get("CLIENT_IP_HEADER")
    if header:
        try:
            return str(ipaddress.ip_address(request.headers.get(header, "").strip()))
        except ValueError:
            pass  # En-tête absent ou malformé : l'adresse de la connexion, faute de mieux
    return get_remote_address()


def init_rate_limiting(app: Flask) -> Limiter:
    """Applique les limites de débit aux endpoints sensibles.

    À appeler après l'enregistrement des blueprints. Un limiteur par application
    (configuration et stockage isolés, utile pour les tests).
    """
    limiter = Limiter(client_ip, app=app)
    for endpoint, config_key in RATE_LIMITED_ENDPOINTS.items():
        view = app.view_functions[endpoint]
        app.view_functions[endpoint] = limiter.limit(app.config[config_key])(view)

    if app.config.get("APP_ENV") == "production" and app.config.get("RATELIMIT_STORAGE_URI", "").startswith("memory://"):
        logging.warning("Rate limiting en mémoire : compteurs non partagés entre processus (utiliser Redis en production multi-instance).")
    app.extensions["terminator_limiter"] = limiter
    return limiter
