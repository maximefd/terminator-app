import os
import logging
import sys
import unicodedata
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from sqlalchemy import or_, func # Nécessaire pour les requêtes combinées
from grid_generator import GridGenerator
import random


# Importation de votre module
from trie_engine import DictionnaireTrie

# Définir le niveau de log au plus bas pour s'assurer que Render affiche nos messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration des fichiers DELA ---
DELA_FILE_FULL = 'dela_clean.csv'
DELA_FILE_LITE = 'dela_clean_lite.csv'

# --- CONFIGURATION DU LOGGING ---
# On ajoute un format pour avoir des logs plus clairs (date, niveau, message)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# --------------------------------

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

def is_match(pattern, word):
    """Vérifie si un mot correspond à un motif (normalisé, sans casse/accent)."""
    # Suggestion 1: Normalisation systématique
    normalized_pattern = normalize_pattern(pattern)
    normalized_word = normalize_pattern(word)

    if len(normalized_pattern) != len(normalized_word):
        return False

    # Utilise une expression génératrice plus concise
    return all(p == '?' or p == w for p, w in zip(normalized_pattern, normalized_word))

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
        user = User.query.filter_by(email=email).first() # <-- CORRIGÉ ICI
        
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
# ROUTES DE GESTION DES MOTS (CRUD)
# =======================================================

@app.route('/api/dictionaries/<int:dict_id>/words', methods=['GET'])
@login_required
def get_words_in_dictionary(dict_id):
    """Récupère tous les mots d'un dictionnaire spécifique."""
    
    # On vérifie que le dictionnaire demandé existe et appartient bien à l'utilisateur
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=current_user.id).first()
    if not dictionary:
        return jsonify({'error': 'Dictionnaire non trouvé.'}), 404
        
    # Grâce à lazy='selectin', les mots sont chargés efficacement
    return jsonify([word.to_json() for word in dictionary.words]), 200

@app.route('/api/dictionaries/<int:dict_id>/words', methods=['POST'])
@login_required
def add_word_to_dictionary(dict_id):
    """Ajoute un nouveau mot à un dictionnaire spécifique."""
    
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=current_user.id).first()
    if not dictionary:
        return jsonify({'error': 'Dictionnaire non trouvé.'}), 404
        
    data = request.get_json()
    mot_affiche = data.get('mot')
    if not mot_affiche or not mot_affiche.strip():
        return jsonify({'error': 'Le mot est obligatoire.'}), 400

    mot_upper = normalize_pattern(mot_affiche)
    definition = data.get('definition', '')

    # Création du nouveau mot, lié directement au dictionnaire
    new_word = PersonalWord(
        mot=mot_upper,
        mot_affiche=mot_affiche,
        definition=definition,
        dictionary_id=dictionary.id
    )
    db.session.add(new_word)
    db.session.commit()
    
    logger.info(f"Mot '{mot_upper}' ajouté au dictionnaire {dict_id} pour l'utilisateur {current_user.id}.")

    return jsonify(new_word.to_json()), 201

@app.route('/api/dictionaries/<int:dict_id>/words/<int:word_id>', methods=['PATCH'])
@login_required
def update_word_in_dictionary(dict_id, word_id):
    """Met à jour un mot dans un dictionnaire spécifique."""
    
    # On vérifie que le dictionnaire appartient bien à l'utilisateur
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=current_user.id).first()
    if not dictionary:
        return jsonify({'error': 'Dictionnaire non trouvé.'}), 404
        
    # On cherche le mot DANS ce dictionnaire spécifique
    word = PersonalWord.query.filter_by(id=word_id, dictionary_id=dict_id).first()
    if not word:
        return jsonify({'error': 'Mot non trouvé dans ce dictionnaire.'}), 404

    data = request.get_json()
    if 'mot' in data:
        mot_affiche = data['mot'].strip()
        if not mot_affiche:
            return jsonify({'error': 'Le mot ne peut pas être vide.'}), 400
        word.mot_affiche = mot_affiche
        word.mot = normalize_pattern(mot_affiche)

    if 'definition' in data:
        word.definition = data['definition']
    
    db.session.commit()
    return jsonify(word.to_json()), 200

@app.route('/api/dictionaries/<int:dict_id>/words/<int:word_id>', methods=['DELETE'])
@login_required
def delete_word_from_dictionary(dict_id, word_id):
    """Supprime un mot d'un dictionnaire spécifique."""
    
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=current_user.id).first()
    if not dictionary:
        return jsonify({'error': 'Dictionnaire non trouvé.'}), 404
        
    word = PersonalWord.query.filter_by(id=word_id, dictionary_id=dict_id).first()
    if not word:
        return jsonify({'error': 'Mot non trouvé.'}), 404

    db.session.delete(word)
    db.session.commit()
    
    return jsonify({'message': 'Mot supprimé avec succès.'}), 200

# =======================================================
# ROUTES DE GESTION DES DICTIONNAIRES (CRUD)
# =======================================================

@app.route('/api/dictionaries', methods=['GET'])
@login_required
def get_dictionaries():
    """Récupère tous les dictionnaires de l'utilisateur connecté."""
    
    # current_user est fourni par Flask-Login et est l'objet User actuellement connecté.
    # Grâce à notre relation `lazy='selectin'`, ceci est très performant.
    user_dictionaries = current_user.dictionaries
    
    # On utilise la méthode to_json() qu'on a définie sur le modèle Dictionary.
    return jsonify([d.to_json() for d in user_dictionaries]), 200

@app.route('/api/dictionaries', methods=['POST'])
@login_required
def create_dictionary():
    """Crée un nouveau dictionnaire pour l'utilisateur connecté."""
    data = request.get_json()
    if not data or 'name' not in data or not data['name'].strip():
        return jsonify({'error': 'Le nom du dictionnaire est manquant.'}), 400

    name = data['name'].strip()

    # On vérifie que le nom n'existe pas déjà (grâce à notre contrainte d'unicité)
    existing_dict = Dictionary.query.filter_by(user_id=current_user.id, name=name).first()
    if existing_dict:
        return jsonify({'error': f"Un dictionnaire nommé '{name}' existe déjà."}), 409 # 409 Conflict

    # Création du nouveau dictionnaire
    new_dict = Dictionary(
        name=name,
        user=current_user
    )
    db.session.add(new_dict)
    db.session.commit()

    logger.info(f"Dictionnaire '{name}' créé pour l'utilisateur {current_user.id}.")

    # On retourne le nouvel objet créé avec un statut 201 Created
    return jsonify(new_dict.to_json()), 201

@app.route('/api/dictionaries/<int:dict_id>', methods=['PATCH'])
@login_required
def update_dictionary(dict_id):
    """Met à jour le nom ou le statut actif d'un dictionnaire."""
    
    # 1. On cherche le dictionnaire en s'assurant qu'il appartient bien à l'utilisateur connecté
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=current_user.id).first()
    if not dictionary:
        return jsonify({'error': 'Dictionnaire non trouvé.'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Données manquantes.'}), 400

    # 2. On met à jour le nom s'il est fourni
    if 'name' in data:
        new_name = data['name'].strip()
        if not new_name:
            return jsonify({'error': 'Le nom ne peut pas être vide.'}), 400
        dictionary.name = new_name

    # 3. Logique spéciale pour 'is_active'
    if data.get('is_active') is True:
        # Si on active ce dictionnaire, on désactive tous les autres du même utilisateur
        Dictionary.query.filter(
            Dictionary.user_id == current_user.id,
            Dictionary.id != dict_id
        ).update({'is_active': False})
        dictionary.is_active = True
    
    db.session.commit()
    logger.info(f"Dictionnaire ID {dict_id} mis à jour pour l'utilisateur {current_user.id}.")
    
    return jsonify(dictionary.to_json()), 200

@app.route('/api/dictionaries/<int:dict_id>', methods=['DELETE'])
@login_required
def delete_dictionary(dict_id):
    """Supprime un dictionnaire."""
    
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=current_user.id).first()
    if not dictionary:
        return jsonify({'error': 'Dictionnaire non trouvé.'}), 404

    db.session.delete(dictionary)
    db.session.commit()
    
    logger.info(f"Dictionnaire ID {dict_id} supprimé pour l'utilisateur {current_user.id}.")

    return jsonify({'message': 'Dictionnaire supprimé avec succès.'}), 200

# =======================================================
# ROUTES DE RECHERCHE FINALE (DELA + Personnels)
# =======================================================

@app.route('/api/search', methods=['POST'])
def search_words():
    """Recherche de mots combinée, optimisée et sécurisée."""
    # Suggestion 5: Gestion globale des erreurs
    try:
        if dela_trie is None:
            return jsonify({"error": "Dictionnaire en cours de chargement."}), 503

        data = request.json
        mask = data.get('mask', '')
        limit = min(int(data.get("limit", 200)), 500) # Suggestion 4: Limite de résultats

        if not mask:
            return jsonify({"error": "Le paramètre 'mask' est obligatoire."}), 400

        cleaned_mask = normalize_pattern(mask)

        personal_results_json = []
        if current_user.is_authenticated:
            active_dict = Dictionary.query.filter_by(user_id=current_user.id, is_active=True).first()

            if active_dict:
                # Suggestion 2: Filtrage performant côté SQL
                sql_mask = cleaned_mask.replace('?', '_')
                personal_words = PersonalWord.query.filter(
                    PersonalWord.dictionary_id == active_dict.id,
                    PersonalWord.mot.like(sql_mask)
                ).all()
                personal_results_json = [w.to_json() for w in personal_words]

        # Recherche DELA
        dela_results_raw = dela_trie.search_pattern(cleaned_mask)

        # Combinaison et dédoublonnage
        final_results = []
        final_results.extend(personal_results_json)

        personal_mots_set = {p['mot'] for p in personal_results_json}

        for mot_obj in dela_results_raw:
            if mot_obj.texte_normalise not in personal_mots_set:
                final_results.append(mot_obj.to_json())

        # Suggestion 4: Application de la limite
        return jsonify({"results": final_results[:limit]}), 200

    except Exception as e:
        logger.error(f"Erreur critique dans /api/search: {e}", exc_info=True)
        return jsonify({"error": "Une erreur interne est survenue lors de la recherche."}), 500



# =======================================================
# ROUTE DE GÉNÉRATION DE GRILLE
# =======================================================

@app.route('/api/grids/generate', methods=['POST'])
@login_required
def generate_grid():
    """Génère une grille de mots fléchés remplie, de manière sécurisée et optimisée."""
    try:
        data = request.get_json()
        size = data.get('size', {})
        
        # Suggestion 5: Limiter la taille de la grille pour la sécurité
        width = min(int(size.get('width', 10)), 20)
        height = min(int(size.get('height', 10)), 20)
        
        seed = data.get('seed') # On récupère le seed optionnel

        word_list = []
        
        if data.get('use_global', True):
            all_dela_words = list(dela_trie.words)
            # Suggestion 1: Échantillonnage pour la performance
            dela_sample = random.sample(all_dela_words, min(30000, len(all_dela_words)))
            word_list.extend(w for w in dela_sample if 2 < len(w) <= max(width, height))
        
        active_dict = Dictionary.query.filter_by(user_id=current_user.id, is_active=True).first()
        if active_dict:
            word_list.extend([word.mot for word in active_dict.words if 2 < len(word.mot) <= max(width, height)])

        if not word_list:
            return jsonify({"error": "Aucun mot de taille adéquate disponible."}), 400

        # On s'assure qu'il n'y a pas de doublons
        unique_words = list(set(word_list))
        
        generator = GridGenerator(width, height, unique_words, seed=seed)
        success = generator.generate()

        if not success:
            return jsonify({"error": "Impossible de générer une grille avec les mots fournis."}), 500
            
        return jsonify({"grid": generator.get_grid_data()}), 200

    except Exception as e:
        # Suggestion 2: Gestion globale des erreurs
        logger.error(f"Erreur lors de la génération de la grille: {e}", exc_info=True)
        return jsonify({"error": "Une erreur interne est survenue lors de la génération."}), 500
    

if __name__ == '__main__':
    logger.info("Démarrage en mode développement local.")
    app.run(host='0.0.0.0', port=5000)
