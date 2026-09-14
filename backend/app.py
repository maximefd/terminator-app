import os
import logging
from flask import Flask
from flask_cors import CORS
from datetime import timedelta

from models import db
from auth import bcrypt, auth_bp
from routes import main_bp
from extensions import jwt
from trie_engine import DictionnaireTrie

DEV_SECRET = 'default-secret-for-dev'


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

    if app_env == 'production':
        problems = []
        if secret_key == DEV_SECRET:
            problems.append('SECRET_KEY')
        if jwt_secret_key == DEV_SECRET:
            problems.append('JWT_SECRET_KEY')
        if not database_url:
            problems.append('DATABASE_URL')
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
    )


def create_app(test_config=None):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    app = Flask(__name__)

    if test_config is None:
        app.config.from_mapping(_load_config_from_env())
    else:
        app.config.from_mapping(test_config)
    
    cors_origins_str = os.environ.get('CORS_ORIGINS', 'http://localhost:3000')
    cors_origins = cors_origins_str.split(',')
    CORS(app, origins=cors_origins, supports_credentials=True)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # MODIFICATION ICI : On ne charge le Trie que si on n'est pas en mode test
    if not app.config.get("TESTING", False):
        DELA_FILE_FULL = 'dela_clean.csv'
        try:
            app.dela_trie = DictionnaireTrie()
            app.dela_trie.load_dela_csv(DELA_FILE_FULL)
            logging.info("Trie chargé avec succès.")
        except Exception as e:
            logging.critical(f"Erreur critique lors de l'initialisation du Trie: {e}", exc_info=True)
            app.dela_trie = None
    else:
        # En mode test, on met un placeholder pour éviter les erreurs
        app.dela_trie = None

    with app.app_context():
        try:
            db.create_all()
            logging.info("Tables de la BDD vérifiées/créées.")
        except Exception as e:
            logging.critical(f"Échec de la création des tables BDD: {e}")

    return app