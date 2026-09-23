# DANS backend/gunicorn.conf.py
"""
Configuration de gunicorn, le serveur de l'API en production ([ADR 0013](../docs/adr/0013-cible-hebergement-production.md)).

En développement, `python run.py` reste le serveur : un seul processus, qui recharge à chaud le
lexique exporté par le curateur.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Workers synchrones : une requête à la fois par processus. Une génération occupe un cœur, et des
# threads n'y changeraient rien : le GIL les sérialise (mesuré). Un worker de plus que de places de
# génération (GENERATION_MAX_CONCURRENT, 2 par défaut) garde de quoi répondre aux requêtes légères
# — connexion, recherche, grilles — pendant que les autres calculent. Les workers partagent le lexique
# chargé par le maître (voir preload_app) : mesuré, 830 Mo pour le maître et trois workers.
workers = int(os.environ.get("WEB_CONCURRENCY", 3))
worker_class = "sync"

# Au-delà du budget de génération (20 s) et de sa préparation : un worker n'est tué que s'il est bloqué
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 60))
graceful_timeout = 30

# Application créée une fois dans le processus maître, avant de créer les workers : le lexique n'est
# lu qu'une fois, et sa mémoire reste partagée tant qu'aucune requête ne le recopie. Les migrations ne
# sont jouées qu'une fois (trois workers les lanceraient ensemble).
preload_app = True

accesslog = "-"
errorlog = "-"

# Journaux en JSON en production, comme ceux de l'API (logging_setup.py). Le journal d'accès garde le chemin
# sans sa query string (%(U)s) : un jeton n'y figure jamais. L'adresse est celle du visiteur (CF-Connecting-IP),
# pas celle de cloudflared.
LOG_FORMAT = os.environ.get("LOG_FORMAT") or ("json" if os.environ.get("APP_ENV") == "production" else "text")
if LOG_FORMAT == "json":
    access_log_format = (
        '{"time": "%(t)s", "ip": "%({cf-connecting-ip}i)s", "method": "%(m)s", "path": "%(U)s", '
        '"status": %(s)s, "bytes": "%(B)s", "duration_ms": %(M)s, "request_id": "%({x-request-id}o)s"}'
    )
    logconfig_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {"()": "logging_setup.JsonFormatter"},
            # Le journal d'accès est déjà du JSON (access_log_format) : pas d'enveloppe de plus
            "brut": {"format": "%(message)s"},
        },
        "handlers": {
            "erreurs": {"class": "logging.StreamHandler", "formatter": "json", "stream": "ext://sys.stderr"},
            "acces": {"class": "logging.StreamHandler", "formatter": "brut", "stream": "ext://sys.stdout"},
        },
        # gunicorn complète cette configuration avec la sienne, dont le logger racine vise un gestionnaire
        # « console » qui n'existe plus ici : il faut le redéclarer. Sans gestionnaire : l'application pose le
        # sien (logging_setup.configure_logging), deux en même temps doubleraient chaque ligne
        "root": {"level": "INFO", "handlers": []},
        "loggers": {
            "gunicorn.error": {"level": "INFO", "handlers": ["erreurs"], "propagate": False},
            "gunicorn.access": {"level": "INFO", "handlers": ["acces"], "propagate": False},
        },
    }


def post_fork(server, worker):
    """Chaque worker ouvre ses propres connexions à la base.

    Le maître en a ouvert pour les migrations ; partagées entre processus, elles mêleraient leurs
    échanges avec PostgreSQL. `close=False` : les oublier sans les fermer, elles appartiennent au maître.
    """
    from models import db
    from run import app

    with app.app_context():
        db.engine.dispose(close=False)
