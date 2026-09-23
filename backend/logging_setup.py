# DANS backend/logging_setup.py
"""
Journaux de l'API : texte en développement, JSON en production (`LOG_FORMAT`).

En production, une ligne par événement, en JSON : horodatage UTC, niveau, message, et pour ce qui arrive
pendant une requête, sa méthode, son chemin et son identifiant. L'identifiant reprend `CF-Ray` (Cloudflare)
quand il est là : la même valeur se retrouve dans l'en-tête `X-Request-ID` de la réponse, dans le rapport
Sentry et dans le tableau de bord de Cloudflare. Le chemin est journalisé sans sa query string : un jeton n'y figure jamais.
"""

import json
import logging
import re
import sys
import uuid
from datetime import datetime, timezone

import sentry_sdk
from flask import Flask, g, has_request_context, request

LOG_FORMATS = ("text", "json")
TEXT_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
# CF-Ray ressemble à « 8c1f2a3b4c5d6e7f-CDG » : on n'accepte qu'un identifiant de cette forme
REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{1,64}$")


class RequestContextFilter(logging.Filter):
    """Ajoute à chaque ligne la requête en cours, s'il y en a une."""

    def filter(self, record: logging.LogRecord) -> bool:
        if has_request_context():
            record.request_id = g.get("request_id")
            record.method = request.method
            record.path = request.path
        return True


class JsonFormatter(logging.Formatter):
    """Une ligne JSON par événement."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "method", "path"):
            value = getattr(record, field, None)
            if value:
                entry[field] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(log_format: str) -> None:
    """Installe le gestionnaire de l'API sur le logger racine, une seule fois même si l'application est recréée.

    Les autres gestionnaires (celui de pytest, par exemple) restent en place.
    """
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, "_terminator", False)]:
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler._terminator = True
    handler.setFormatter(JsonFormatter() if log_format == "json" else logging.Formatter(TEXT_FORMAT))
    handler.addFilter(RequestContextFilter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def register_request_id(app: Flask) -> None:
    """Donne un identifiant à chaque requête, renvoyé dans `X-Request-ID`."""

    @app.before_request
    def assign_request_id():
        ray = request.headers.get("CF-Ray", "")
        g.request_id = ray if REQUEST_ID.match(ray) else uuid.uuid4().hex[:16]
        # Le même identifiant sur le rapport Sentry, s'il y en a un (sans Sentry actif : sans effet)
        sentry_sdk.set_tag("request_id", g.request_id)

    @app.after_request
    def expose_request_id(response):
        if g.get("request_id"):
            response.headers["X-Request-ID"] = g.request_id
        return response
