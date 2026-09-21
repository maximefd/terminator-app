import os
import logging
from flask import Flask
from flask_cors import CORS
from datetime import timedelta
from werkzeug.middleware.proxy_fix import ProxyFix

from models import db
from auth import bcrypt, auth_bp
from routes import main_bp
from extensions import jwt, migrate
from security import init_rate_limiting, register_error_handlers, register_jwt_callbacks, register_security_headers
from lexicon_loader import LexiconManager

DEV_SECRET = 'default-secret-for-dev'
# Première migration : le schéma tel qu'il existait avant l'arrivée d'Alembic
BASELINE_REVISION = '0001_schema_initial'
DEFAULT_CORS_ORIGINS = 'http://localhost:3000'

# Valeurs par défaut communes (application normale et tests), surchargeables
DEFAULT_SETTINGS = dict(
    MAX_CONTENT_LENGTH=64 * 1024,  # Corps de requête : 64 Ko maximum
    MAX_DICTIONARIES_PER_USER=20,
    MAX_WORDS_PER_DICTIONARY=5000,
    # Garde-fou, pas quota d'usage : l'auteur ne doit jamais s'y heurter. Il existe pour le jour où
    # d'autres comptes écriront dans la même base.
    MAX_GRIDS_PER_USER=1000,
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
    # Appelé à chaque frappe de l'auteur, et sans génération : plafond de la recherche, pas de la génération
    RATELIMIT_DIFFICULTY='120 per minute',
    LEXICON_PATH=None,  # Lexique curé ; à défaut, le DELA complet (backend/dela_clean.csv)
    LEXICON_RELOAD_INTERVAL_S=30,  # Vérification des changements du lexique (0 : pas de rechargement à chaud)
    # Applique les migrations en attente au démarrage. Pratique en local ; à couper le jour où un
    # déploiement les jouera lui-même, avant de lancer l'application (Phase 6).
    AUTO_MIGRATE=True,
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
        # Desserrable pour les parcours end-to-end, qui créent un compte par exécution.
        # Jamais en production : le quota y protège de la création de comptes en masse.
        RATELIMIT_REGISTER=(
            os.environ.get('RATELIMIT_REGISTER') if app_env != 'production' else None
        ) or DEFAULT_SETTINGS['RATELIMIT_REGISTER'],
        # Même logique pour la génération : en local, l'auteur enchaîne les tentatives sur une
        # demande difficile, et un plafond conçu contre l'abus n'a rien à y faire.
        RATELIMIT_GENERATE=(
            os.environ.get('RATELIMIT_GENERATE') if app_env != 'production' else None
        ) or DEFAULT_SETTINGS['RATELIMIT_GENERATE'],
        MAX_GRIDS_PER_USER=int(os.environ.get('MAX_GRIDS_PER_USER') or DEFAULT_SETTINGS['MAX_GRIDS_PER_USER']),
        LEXICON_PATH=os.environ.get('LEXICON_PATH') or None,
        LEXICON_RELOAD_INTERVAL_S=float(os.environ.get('LEXICON_RELOAD_INTERVAL_S', 30)),
    )


def prepare_database(app: Flask) -> None:
    """Met le schéma à niveau au démarrage.

    Les tests tournent sur une base SQLite en mémoire, recréée à chaque session : y jouer les
    migrations coûterait du temps sans rien vérifier de plus, `db.create_all()` suffit.

    En développement, la base existait avant les migrations (créée par `db.create_all()`).
    Rejouer la première révision échouerait sur des tables déjà là : on la marque comme
    appliquée (`stamp`), puis on déroule les suivantes.
    """
    from sqlalchemy import inspect

    if app.config['TESTING']:
        db.create_all()
        return
    if not app.config['AUTO_MIGRATE']:
        return
    if not os.path.isdir(os.path.join(app.root_path, 'migrations')):
        logging.warning("Dossier migrations/ absent : schéma laissé en l'état.")
        return

    from flask_migrate import stamp, upgrade

    tables = set(inspect(db.engine).get_table_names())
    if tables and 'alembic_version' not in tables:
        logging.info("Base antérieure aux migrations : marquage de la révision initiale.")
        stamp(revision=BASELINE_REVISION)
    upgrade()
    logging.info("Schéma de la BDD à jour.")


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
    migrate.init_app(app, db)
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
            prepare_database(app)
        # SystemExit : la CLI d'Alembic quitte le processus quand une migration échoue.
        # L'API démarre quand même, pour que l'erreur se lise dans le journal et non dans un conteneur mort.
        except (Exception, SystemExit) as e:
            logging.critical(f"Échec de la préparation de la BDD: {e}")

    return app