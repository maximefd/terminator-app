import os
import logging
import sys
import unicodedata
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from sqlalchemy import or_ # Nécessaire pour les requêtes combinées


# Importation de votre module
from trie_engine import DictionnaireTrie

# Définir le niveau de log au plus bas pour s'assurer que Render affiche nos messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration des fichiers DELA ---
DELA_FILE_FULL = 'dela_clean.csv'
DELA_FILE_LITE = 'dela_clean_lite.csv'

# --- Configuration de l'application Flask ---
app = Flask(__name__)
CORS(app)

FLASK_ENV = os.environ.get('FLASK_ENV', 'development')

# Charger la configuration depuis les variables d'environnement
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_for_local_dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')

# Gérer le cas où DATABASE_URL n'est pas défini
if not app.config['SQLALCHEMY_DATABASE_URI']:
    logger.error("DATABASE_URL n'est pas défini ! Utilisation d'une BDD en mémoire.")
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"

# La configuration des cookies peut aussi dépendre de l'environnement
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' 

db = SQLAlchemy(app)
login_manager = LoginManager(app)

# Initialisation du dictionnaire Trie
dela_trie = None

# =======================================================
# UTILITIES
# =======================================================

def normalize_pattern(text):
    """Normalise une chaîne de recherche (accentué -> sans accent, majuscules)."""
    if not isinstance(text, str):
        return ""
    text = text.upper()
    # Enlève les accents
    normalized = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
    return normalized.strip()

# =======================================================
# DÉFINITION DES MODÈLES (TABLES DE LA BDD)
# =======================================================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'user' # Nom de la table en anglais et minuscule
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=True) # On ajoutera le hash plus tard

    dictionaries = db.relationship('Dictionary', backref='user', lazy='selectin', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"

class Dictionary(db.Model):
    __tablename__ = 'dictionary'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    words = db.relationship('PersonalWord', backref='dictionary', lazy='selectin', cascade="all, delete-orphan")

    # Contrainte d'unicité : un utilisateur ne peut pas avoir deux dicos avec le même nom
    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uix_user_dico_name'),
    )

    def __repr__(self):
        return f"<Dictionary {self.name} (User {self.user_id})>"

    def to_json(self, include_words=False):
        data = {
            'id': self.id,
            'name': self.name,
            'is_active': self.is_active,
            'user_id': self.user_id
        }
        if include_words:
            data['words'] = [w.to_json() for w in self.words]
        return data

class PersonalWord(db.Model):
    __tablename__ = 'personal_word'
    id = db.Column(db.Integer, primary_key=True)
    mot = db.Column(db.String(50), nullable=False)
    mot_affiche = db.Column(db.String(50), nullable=False)
    definition = db.Column(db.String(255))
    date_ajout = db.Column(db.DateTime, default=datetime.utcnow)

    dictionary_id = db.Column(db.Integer, db.ForeignKey('dictionary.id'), nullable=False)

    def __repr__(self):
        return f"<PersonalWord '{self.mot_affiche}'>"

    def to_json(self):
        return {
            'id': self.id,
            'mot': self.mot,
            'mot_affiche': self.mot_affiche,
            'longueur': len(self.mot),
            'definition': self.definition,
            'source': 'PERSONNEL',
            'date_ajout': self.date_ajout.isoformat() if self.date_ajout else None
        }

# =======================================================
# FONCTIONS D'INITIALISATION
# =======================================================

def get_dela_file_path():
    """Détermine quel fichier DELA charger en fonction de l'environnement."""
    trie_mode = os.environ.get('TRIE_MODE', 'full').lower()

    if trie_mode == 'lite':
        file_path = DELA_FILE_LITE
    else:
        file_path = DELA_FILE_FULL
    
    logger.info(f"--- DÉBOGAGE TRIE ---")
    logger.info(f"TRIE_MODE détecté : '{trie_mode}'")
    logger.info(f"Chemin du fichier sélectionné : '{file_path}'")
    logger.info(f"--- DÉBOGAGE TRIE ---")
    
    return file_path

def initialize_trie():
    """Charge le dictionnaire Trie au démarrage de l'application."""
    global dela_trie
    
    if dela_trie is None:
        try:
            file_path = get_dela_file_path()
            logger.info(f"Démarrage du chargement du Trie depuis : {file_path}")

            dela_trie = DictionnaireTrie()
            dela_trie.load_dela_csv(file_path)
            
            logger.info(f"Trie chargé avec succès (le nombre de mots sera vérifié via /api/status).") 

        except FileNotFoundError:
            logger.error(f"Erreur: Fichier dictionnaire non trouvé à '{file_path}'. Tentative de chargement de la version FULL.")
            try:
                dela_trie = DictionnaireTrie()
                dela_trie.load_dela_csv(DELA_FILE_FULL)
            except Exception as fe:
                logger.critical(f"Échec du chargement du Trie de secours (FULL): {fe}")
                dela_trie = None
        except Exception as e:
            logger.critical(f"Erreur critique lors de l'initialisation du Trie: {e}")
            dela_trie = None 

def initialize_demo_user_and_words():
    """Crée l'utilisateur de démo, son dictionnaire par défaut et des mots de démo."""
    demo_email = 'demo@terminator.com'
    
    with app.app_context():
        # MODIFIÉ ICI: Utilisateur -> User
        user = User.query.filter_by(email=demo_email).first()
        if not user:
            # MODIFIÉ ICI: Utilisateur -> User
            user = User(email=demo_email, password="password")
            db.session.add(user)
            db.session.commit()
            logger.info(f"Utilisateur de démo '{demo_email}' créé.")
        
        if not user.dictionaries:
            # MODIFIÉ ICI: utilisateur=user -> user=user
            default_dict = Dictionary(name="Dictionnaire par défaut", is_active=True, user=user)
            db.session.add(default_dict)
            
            demo_words_data = [
                ("CHAT", "Chat", "Animal de compagnie domestique."),
                ("PIZZA", "Pizza", "Plat italien populaire."),
            ]
            
            for upper_mot, display_mot, definition in demo_words_data:
                new_word = PersonalWord(
                    mot=upper_mot,
                    mot_affiche=display_mot,
                    definition=definition,
                    dictionary=default_dict
                )
                db.session.add(new_word)
            
            db.session.commit()
            logger.info(f"Dictionnaire par défaut et 2 mots de démo ajoutés pour l'utilisateur {user.id}.")
            
# =======================================================
# BLOC D'INITIALISATION CRITIQUE (Exécuté par Gunicorn)
# =======================================================
with app.app_context():
    # 1. Créer les tables BDD
    try:
        db.create_all()
        logger.info("Tables de la BDD vérifiées/créées.")
    except Exception as e:
        logger.critical(f"Échec de la création des tables BDD: {e}")
        if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
            sys.exit(1)
            
    # 2. Charger le dictionnaire Trie
    initialize_trie()
    
    # 3. Créer l'utilisateur de démo et les mots de démo
    initialize_demo_user_and_words()


# =======================================================
# ROUTES D'AUTHENTIFICATION ET DE STATUT
# =======================================================

@app.route('/api/login', methods=['POST'])
def login():
    """Connecte l'utilisateur de démo."""
    data = request.get_json()
    email = data.get('email', 'demo@terminator.com')
    
    with app.app_context():
        user = Utilisateur.query.filter_by(email=email).first()
        
        if user:
            login_user(user)
            return jsonify({"success": True, "message": f"Connecté en tant que {user.email}", "user_id": user.id})
            
        return jsonify({"success": False, "message": "Email non trouvé (utilisez demo@terminator.com)"}), 401


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """Déconnecte l'utilisateur actuellement connecté."""
    logout_user()
    return jsonify({"success": True, "message": "Déconnecté avec succès"})


@app.route('/api/status', methods=['GET'])
def status_check():
    """Vérifie l'état de l'API, du dictionnaire et de l'authentification."""
    # S'assurer que l'attribut 'words' existe avant de l'appeler
    word_count = len(dela_trie.words) if dela_trie and hasattr(dela_trie, 'words') else 0
    
    status = {
        "status": "ok",
        "env": FLASK_ENV,
        "trie_loaded": dela_trie is not None,
        "word_count": word_count,
        "is_authenticated": current_user.is_authenticated if current_user.is_authenticated else False,
        "email": current_user.email if current_user.is_authenticated else None,
        "db_configured": 'SQLALCHEMY_DATABASE_URI' in app.config and app.config['SQLALCHEMY_DATABASE_URI'] != "sqlite:///:memory:",
        "message": "Terminator est opérationnel."
    }
    return jsonify(status), 200

# =======================================================
# ROUTES DE GESTION DES MOTS PERSONNELS (CRUD)
# =======================================================

@app.route('/api/personal_words', methods=['GET'])
@login_required
def get_personal_words():
    """Récupère tous les mots personnels de l'utilisateur connecté."""
    try:
        words = [word.to_json() for word in current_user.mots_personnels]
        return jsonify({"results": words}), 200
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des mots personnels: {e}")
        return jsonify({"error": "Erreur interne lors de la récupération des mots personnels."}), 500

@app.route('/api/personal_words', methods=['POST'])
@login_required
def add_personal_word():
    """Ajoute un mot personnel à l'utilisateur connecté."""
    data = request.get_json()
    mot_affiche = data.get('mot')
    definition = data.get('definition', '')
    
    if not mot_affiche:
        return jsonify({"error": "Le mot est obligatoire."}), 400

    # Normalisation pour le stockage dans la BDD et la recherche
    mot_upper = normalize_pattern(mot_affiche)

    try:
        # Vérification si le mot existe déjà
        existing_word = MotPersonnel.query.filter_by(mot=mot_upper, user_id=current_user.id).first()
        if existing_word:
            return jsonify({"error": f"Le mot '{mot_affiche}' existe déjà dans votre liste personnelle."}), 409

        new_word = MotPersonnel(
            mot=mot_upper,
            mot_affiche=mot_affiche,
            definition=definition,
            user_id=current_user.id
        )
        db.session.add(new_word)
        db.session.commit()
        
        logger.info(f"Mot personnel ajouté: {mot_upper} par utilisateur {current_user.id}")
        return jsonify(new_word.to_json()), 201

    except Exception as e:
        logger.error(f"Erreur lors de l'ajout d'un mot personnel: {e}")
        db.session.rollback()
        return jsonify({"error": "Erreur interne lors de l'ajout du mot personnel."}), 500

@app.route('/api/personal_words/<int:word_id>', methods=['DELETE'])
@login_required
def delete_personal_word(word_id):
    """Supprime un mot personnel de l'utilisateur connecté."""
    try:
        word = MotPersonnel.query.filter_by(id=word_id, user_id=current_user.id).first()
        
        if not word:
            return jsonify({"error": "Mot personnel non trouvé."}), 404

        db.session.delete(word)
        db.session.commit()
        logger.info(f"Mot personnel supprimé: ID {word_id} par utilisateur {current_user.id}")
        return jsonify({"success": True, "message": "Mot supprimé avec succès."}), 200

    except Exception as e:
        logger.error(f"Erreur lors de la suppression du mot personnel: {e}")
        db.session.rollback()
        return jsonify({"error": "Erreur interne lors de la suppression du mot personnel."}), 500


# =======================================================
# ROUTES DE RECHERCHE FINALE (DELA + Personnels)
# =======================================================

@app.route('/api/search', methods=['POST'])
def search_words():
    """Recherche de mots combinée (DELA + Mots Personnels)."""
    if dela_trie is None:
        return jsonify({"error": "Dictionnaire en cours de chargement ou a échoué.", "detail": "Réessayez plus tard."}), 503

    data = request.json
    letters = data.get('letters', '').upper()
    mask = data.get('mask', '').upper()

    cleaned_mask = normalize_pattern(mask)
    cleaned_letters = normalize_pattern(letters)

    if not cleaned_letters and not cleaned_mask:
        return jsonify({"error": "Veuillez fournir des lettres et/ou un masque."}), 400

    # 1. Recherche dans le DELA (via le Trie)
    try:
        dela_results_set = dela_trie.search_by_mask(cleaned_mask, cleaned_letters)
    except Exception as e:
        # Si la recherche Trie plante (ex: le chargement a échoué), on log et on continue
        logger.error(f"Erreur lors de la recherche dans le Trie: {e}")
        dela_results_set = set()


    # 2. Recherche dans les Mots Personnels (via la BDD)
    personal_results = []
    if current_user.is_authenticated:
        # Filtrer les mots personnels de l'utilisateur actuel
        # Le masque est un string de regex (e.g. R.O.) que nous ne pouvons pas directement utiliser en SQL.
        # Nous allons d'abord filtrer par longueur, puis laisser Python gérer le masque.
        
        word_length = len(cleaned_mask)
        
        # Récupère tous les mots personnels de la bonne longueur pour l'utilisateur
        personal_words_db = MotPersonnel.query.filter(
            MotPersonnel.user_id == current_user.id,
            db.func.length(MotPersonnel.mot) == word_length
        ).all()
        
        # Le filtrage fin par lettres disponibles est effectué dans la boucle
        
        # NOTE: Le front-end doit être responsable de filtrer le masque/lettres pour les mots personnels
        # Pour une implémentation complète ici, nous devrions répliquer la logique de validation du Trie.
        # Pour le moment, nous les récupérons par longueur et laissons le front-end gérer la validation.
        # Nous n'avons pas la logique pour vérifier les lettres disponibles sans la méthode du Trie.
        
        # Pour la démo, on utilise la méthode to_json pour le formatage
        for word in personal_words_db:
             # L'implémentation complète nécessiterait une méthode de validation complexe ici.
             # On inclut tous les mots de la bonne longueur en attendant la logique complète.
             personal_results.append(word.to_json())

    # 3. Combinaison et formatage des résultats DELA
    final_results = [
        {'mot': mot, 'longueur': len(mot), 'definition': "Définition DELA", 'source': 'DELA'}
        for mot in dela_results_set
    ]

    # 4. Ajout des résultats personnels
    final_results.extend(personal_results)
    
    # Éliminer les doublons si un mot personnel existe dans DELA (par mot et longueur)
    unique_mots = set()
    deduped_results = []
    for item in final_results:
        key = (item['mot'], item['longueur'])
        if key not in unique_mots:
            unique_mots.add(key)
            deduped_results.append(item)

    return jsonify({"results": deduped_results}), 200

if __name__ == '__main__':
    logger.info("Démarrage en mode développement local.")
    app.run(host='0.0.0.0', port=5000)
