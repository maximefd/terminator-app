import os
import logging
from flask import Flask
from flask_cors import CORS
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix

from models import db
from auth import bcrypt, auth_bp
from routes import main_bp
from extensions import jwt
from security import init_rate_limiting, register_error_handlers, register_jwt_callbacks, register_security_headers
from lexicon_loader import LexiconManager

DEV_SECRET = 'default-secret-for-dev'
DEFAULT_CORS_ORIGINS = 'http://localhost:3000'

# Valeurs par défaut communes (application normale et tests), surchargeables
DEFAULT_SETTINGS = dict(
    MAX_CONTENT_LENGTH=64 * 1024,  # Corps de requête : 64 Ko maximum
    MAX_DICTIONARIES_PER_USER=20,
    MAX_WORDS_PER_DICTIONARY=5000,
    CORS_ORIGINS=DEFAULT_CORS_ORIGINS,
    TRUST_PROXY_HOPS=0,  # Nombre de proxys de confiance devant l'API (Render : 1)
    RATELIMIT_ENABLED=True,
    RATELIMIT_STORAGE_URI='memory://',
    RATELIMIT_HEADERS_ENABLED=True,
    RATELIMIT_LOGIN='10 per minute',
    RATELIMIT_REGISTER='5 per hour',
    RATELIMIT_REFRESH='30 per minute',
    RATELIMIT_SEARCH='120 per minute',
    RATELIMIT_GENERATE='10 per minute',
    LEXICON_PATH=None,  # Lexique curé ; à défaut, le DELA complet (backend/dela_clean.csv)
    LEXICON_RELOAD_INTERVAL_S=30,  # Vérification des changements du lexique (0 : pas de rechargement à chaud)
)


def parse_cors_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(',') if origin.strip()]


def _load_config_from_env() -> dict:
    """Construit la configuration depuis l'environnement.

    En production (APP_ENV=production), refuse de démarrer avec des secrets par défaut
    ou sans base de données persistante.
    """
    app_env = os.environ.get('APP_ENV', 'development')
    secret_key = os.environ.get('SECRET_KEY', DEV_SECRET)
    # JWT_SECRET_KEY dédié ; repli sur SECRET_KEY pour compatibilité avec les déploiements existants
    jwt_secret_key = os.environ.get('JWT_SECRET_KEY') or secret_key
    database_url = os.environ.get('DATABASE_URL')
    cors_origins = os.environ.get('CORS_ORIGINS', DEFAULT_CORS_ORIGINS)

    if app_env == 'production':
        problems = []
        if secret_key == DEV_SECRET:
            problems.append('SECRET_KEY')
        if jwt_secret_key == DEV_SECRET:
            problems.append('JWT_SECRET_KEY')
        if not database_url:
            problems.append('DATABASE_URL')
        if '*' in parse_cors_origins(cors_origins):
            problems.append('CORS_ORIGINS')
        if problems:
            raise RuntimeError(f"Configuration de production invalide, variables manquantes ou par défaut : {', '.join(problems)}")

    return dict(
        APP_ENV=app_env,
        SECRET_KEY=secret_key,
        JWT_SECRET_KEY=jwt_secret_key,
        SQLALCHEMY_DATABASE_URI=database_url or 'sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=7),
        JSON_AS_ASCII=False,
        GENERATION_TIME_BUDGET_S=float(os.environ.get('GENERATION_TIME_BUDGET_S', 20)),
        CORS_ORIGINS=cors_origins,
        TRUST_PROXY_HOPS=int(os.environ.get('TRUST_PROXY_HOPS', 0)),
        RATELIMIT_STORAGE_URI=os.environ.get('RATELIMIT_STORAGE_URI', 'memory://'),
        LEXICON_PATH=os.environ.get('LEXICON_PATH') or None,
        LEXICON_RELOAD_INTERVAL_S=float(os.environ.get('LEXICON_RELOAD_INTERVAL_S', 30)),
    )


def create_app(test_config=None):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    app = Flask(__name__)
    app.config.from_mapping(DEFAULT_SETTINGS)

    if test_config is None:
        app.config.from_mapping(_load_config_from_env())
    else:
        app.config.from_mapping(test_config)

    # Derrière un reverse proxy (Render), l'IP réelle du client est dans X-Forwarded-For :
    # indispensable pour que le rate limiting ne compte pas tout le monde comme une seule IP.
    if app.config['TRUST_PROXY_HOPS']:
        hops = app.config['TRUST_PROXY_HOPS']
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops)

    # L'authentification passe par l'en-tête Authorization (pas de cookie) : pas de credentials CORS
    CORS(
        app,
        resources={r"/api/*": {"origins": parse_cors_origins(app.config['CORS_ORIGINS'])}},
        methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        max_age=600,
    )

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    register_jwt_callbacks(jwt)
    register_error_handlers(app)
    register_security_headers(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    init_rate_limiting(app)

    # Le lexique n'est pas chargé en mode test (les tests fournissent un petit Trie)
    app.dela_trie = None
    app.lexicon = None
    if not app.config.get("TESTING", False):
        manager = LexiconManager(app.config['LEXICON_PATH'])
        try:
            manager.check()
        except Exception as e:
            logging.critical(f"Erreur critique lors du chargement du lexique : {e}", exc_info=True)
        app.dela_trie = manager.trie
        app.lexicon = manager
        # Rechargement à chaud : le curateur réexporte le lexique tous les 500 mots triés
        if app.config['LEXICON_RELOAD_INTERVAL_S'] > 0:
            manager.start_watching(
                app.config['LEXICON_RELOAD_INTERVAL_S'],
                on_reload=lambda m: setattr(app, 'dela_trie', m.trie),
            )

    with app.app_context():
        try:
            db.create_all()
            logging.info("Tables de la BDD vérifiées/créées.")
        except Exception as e:
            logging.critical(f"Échec de la création des tables BDD: {e}")

    return app