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

def create_app(test_config=None):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    app = Flask(__name__)

    if test_config is None:
        app.config.from_mapping(
            SECRET_KEY=os.environ.get('SECRET_KEY', 'default-secret-for-dev'),
            JWT_SECRET_KEY=os.environ.get('SECRET_KEY', 'default-secret-for-dev'),
            SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///:memory:'),
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
            JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=7),
            JSON_AS_ASCII=False
        )
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