# DANS backend/monitoring.py
"""
Suivi des erreurs avec Sentry ([ADR 0013](../docs/adr/0013-cible-hebergement-production.md)).

Inactif sans `SENTRY_DSN` : rien ne part en développement ni dans les tests. En production, seules les
erreurs sont envoyées (pas de mesure de performance : l'offre gratuite a un quota), et rien de ce qui
identifie un utilisateur ou ouvre son compte : ni cookies, ni en-têtes d'authentification, ni corps de
requête (mots de passe, jetons des liens reçus par e-mail), ni variables locales, ni adresse IP.
"""

import sentry_sdk
from flask import Flask
from sentry_sdk.integrations.flask import FlaskIntegration

# En-têtes gardés dans un rapport d'erreur : ceux qui aident à comprendre, aucun qui authentifie
KEPT_HEADERS = {"content-type", "content-length", "user-agent", "accept", "accept-language", "origin", "referer"}


def scrub(event: dict, _hint: dict) -> dict:
    """Retire d'un rapport ce qui pourrait identifier un utilisateur ou ouvrir son compte."""
    request = event.get("request")
    if request:
        request.pop("cookies", None)
        request.pop("data", None)
        request.pop("env", None)
        headers = request.get("headers") or {}
        request["headers"] = {k: v for k, v in headers.items() if k.lower() in KEPT_HEADERS}
    event.pop("user", None)
    return event


def init_sentry(app: Flask) -> bool:
    """Active Sentry si `SENTRY_DSN` est défini. Renvoie True s'il l'est."""
    dsn = app.config.get("SENTRY_DSN")
    if not dsn:
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=app.config.get("APP_ENV", "development"),
        release=app.config.get("RELEASE") or None,
        integrations=[FlaskIntegration()],
        send_default_pii=False,
        max_request_body_size="never",
        # Les variables locales d'une fonction qui plante peuvent contenir un mot de passe (le corps d'une
        # connexion validé dans `payload`, par exemple) : le filtre de Sentry ne les reconnaît qu'à leur nom
        include_local_variables=False,
        traces_sample_rate=0,
        before_send=scrub,
    )
    return True


def report_exception(error: BaseException) -> None:
    """Signale une exception gérée par l'API.

    Le gestionnaire d'erreurs de security.py intercepte toutes les exceptions pour renvoyer un 500 propre :
    Flask ne les voit plus passer, et l'intégration Sentry non plus. Sans Sentry actif, ne fait rien.
    """
    sentry_sdk.capture_exception(error)
