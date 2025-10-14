# DANS backend/app.py

import os
import logging
from flask import Flask
from flask_cors import CORS
from datetime import timedelta

# On importe les objets que nous allons initialiser
from models import db
from auth import bcrypt, auth_bp
from routes import main_bp
from extensions import jwt
from trie_engine import DictionnaireTrie

def create_app():
    """Crée et configure une instance de l'application Flask."""
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    app = Flask(__name__)
    
    # --- CONFIGURATION DE LA SÉCURITÉ ---
    # On définit UNE SEULE clé secrète.
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'une-cle-secrete-tres-longue-et-difficile-a-deviner')
    
    # LA CORRECTION DÉFINITIVE EST ICI :
    # On force la clé JWT à être la même que la clé principale de l'application.
    app.config["JWT_SECRET_KEY"] = app.config['SECRET_KEY']

    # --- AUTRES CONFIGURATIONS ---
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///:memory:')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

    # --- INITIALISATION DES SERVICES ---
    cors_origins_str = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://192.168.1.75:3000,http://192.0.0.2:3000')
    cors_origins = cors_origins_str.split(',')
    CORS(app, origins=cors_origins, supports_credentials=True)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # --- ENREGISTREMENT DES BLUEPRINTS ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # --- GESTION DU DICTIONNAIRE GLOBAL (TRIE) ---
    DELA_FILE_FULL = 'dela_clean.csv'
    try:
        app.dela_trie = DictionnaireTrie()
        app.dela_trie.load_dela_csv(DELA_FILE_FULL)
        logging.info("Trie chargé avec succès.")
    except Exception as e:
        logging.critical(f"Erreur critique lors de l'initialisation du Trie: {e}", exc_info=True)
        app.dela_trie = None

    with app.app_context():
        try:
            db.create_all()
            logging.info("Tables de la BDD vérifiées/créées.")
        except Exception as e:
            logging.critical(f"Échec de la création des tables BDD: {e}")

    return app