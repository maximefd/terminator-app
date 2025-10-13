# DANS backend/app.py

import os
import logging
import sys
import unicodedata
import random
from datetime import timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from sqlalchemy import func

# Imports depuis nos modules locaux
from trie_engine import DictionnaireTrie
from grid_generator import GridGenerator
from models import db, User, Dictionary, PersonalWord
from auth import auth_bp, bcrypt

# --- CONFIGURATION DE L'APPLICATION ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_for_local_dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///:memory:')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY', 'another-super-secret-key')
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)

# --- INITIALISATION DES SERVICES ---
# MODIFICATION ICI : On lit les origines depuis la variable d'environnement
cors_origins_str = os.environ.get('CORS_ORIGINS', 'http://localhost:3000')
cors_origins = cors_origins_str.split(',')
CORS(app, origins=cors_origins, supports_credentials=True)

db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)

# Enregistrement du Blueprint d'authentification
app.register_blueprint(auth_bp)

# --- GESTION DU DICTIONNAIRE GLOBAL (TRIE) ---
DELA_FILE_FULL = 'dela_clean.csv'
dela_trie = None

def get_dela_file_path():
    logger.info(f"Chargement du dictionnaire complet : '{DELA_FILE_FULL}'")
    return DELA_FILE_FULL

def initialize_trie():
    global dela_trie
    if dela_trie is None:
        try:
            file_path = get_dela_file_path()
            dela_trie = DictionnaireTrie()
            dela_trie.load_dela_csv(file_path)
            logger.info("Trie chargé avec succès.")
        except Exception as e:
            logger.critical(f"Erreur critique lors de l'initialisation du Trie: {e}", exc_info=True)
            dela_trie = None

# --- INITIALISATION DE LA BDD ET DU TRIE ---
with app.app_context():
    try:
        db.create_all()
        logger.info("Tables de la BDD vérifiées/créées.")
    except Exception as e:
        logger.critical(f"Échec de la création des tables BDD: {e}")
        if 'postgresql' in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
            sys.exit(1)
    initialize_trie()

# --- ROUTES API PRINCIPALES ---

@app.route('/api/status', methods=['GET'])
def status_check():
    word_count = len(dela_trie.words) if dela_trie and hasattr(dela_trie, 'words') else 0
    return jsonify({
        "status": "ok",
        "trie_loaded": dela_trie is not None,
        "word_count": word_count,
    }), 200

# --- ROUTES PROTÉGÉES ---

def get_current_user():
    """Fonction utilitaire pour récupérer l'objet User à partir de l'identité JWT."""
    user_id = get_jwt_identity()
    return db.session.get(User, user_id) if user_id else None

@app.route('/api/dictionaries', methods=['GET'])
@jwt_required()
def get_dictionaries():
    user = get_current_user()
    return jsonify([d.to_json() for d in user.dictionaries]), 200

@app.route('/api/dictionaries', methods=['POST'])
@jwt_required()
def create_dictionary():
    user = get_current_user()
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Le nom du dictionnaire est manquant.'}), 400
    
    existing = Dictionary.query.filter_by(user_id=user.id, name=name).first()
    if existing:
        return jsonify({'error': f"Un dictionnaire nommé '{name}' existe déjà."}), 409

    new_dict = Dictionary(name=name, user_id=user.id)
    db.session.add(new_dict)
    db.session.commit()
    return jsonify(new_dict.to_json()), 201

@app.route('/api/dictionaries/<int:dict_id>', methods=['PATCH'])
@jwt_required()
def update_dictionary(dict_id):
    user = get_current_user()
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=user.id).first_or_404()
    
    data = request.get_json()
    if 'name' in data:
        dictionary.name = data['name'].strip()
    
    if data.get('is_active') is True:
        Dictionary.query.filter(Dictionary.user_id == user.id).update({'is_active': False})
        dictionary.is_active = True
        
    db.session.commit()
    return jsonify(dictionary.to_json()), 200

@app.route('/api/dictionaries/<int:dict_id>', methods=['DELETE'])
@jwt_required()
def delete_dictionary(dict_id):
    user = get_current_user()
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=user.id).first_or_404()
    db.session.delete(dictionary)
    db.session.commit()
    return jsonify({'message': 'Dictionnaire supprimé avec succès.'}), 200

@app.route('/api/dictionaries/<int:dict_id>/words', methods=['GET'])
@jwt_required()
def get_words_in_dictionary(dict_id):
    user = get_current_user()
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=user.id).first_or_404()
    return jsonify([word.to_json() for word in dictionary.words]), 200

@app.route('/api/dictionaries/<int:dict_id>/words', methods=['POST'])
@jwt_required()
def add_word_to_dictionary(dict_id):
    user = get_current_user()
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=user.id).first_or_404()
    
    data = request.get_json()
    mot_affiche = data.get('mot', '').strip()
    if not mot_affiche:
        return jsonify({'error': 'Le mot est obligatoire.'}), 400

    mot_upper = normalize_pattern(mot_affiche)
    
    existing = PersonalWord.query.filter_by(dictionary_id=dict_id, mot=mot_upper).first()
    if existing:
        return jsonify({'error': f"Le mot '{mot_affiche}' existe déjà."}), 409

    new_word = PersonalWord(
        mot=mot_upper,
        mot_affiche=mot_affiche,
        definition=data.get('definition', ''),
        dictionary_id=dict_id
    )
    db.session.add(new_word)
    db.session.commit()
    return jsonify(new_word.to_json()), 201
    
@app.route('/api/dictionaries/<int:dict_id>/words/<int:word_id>', methods=['DELETE'])
@jwt_required()
def delete_word_from_dictionary(dict_id, word_id):
    user = get_current_user()
    Dictionary.query.filter_by(id=dict_id, user_id=user.id).first_or_404()
    
    word = PersonalWord.query.filter_by(id=word_id, dictionary_id=dict_id).first_or_404()
    db.session.delete(word)
    db.session.commit()
    return jsonify({'message': 'Mot supprimé avec succès.'}), 200

@app.route('/api/search', methods=['POST'])
@jwt_required(optional=True)
def search_words():
    user = get_current_user()
    data = request.json
    mask = data.get('mask', '')
    cleaned_mask = normalize_pattern(mask)
    
    personal_results_json = []
    if user:
        active_dict = Dictionary.query.filter_by(user_id=user.id, is_active=True).first()
        if active_dict:
            sql_mask = cleaned_mask.replace('?', '_')
            personal_words = PersonalWord.query.filter(
                PersonalWord.dictionary_id == active_dict.id,
                PersonalWord.mot.like(sql_mask)
            ).all()
            personal_results_json = [w.to_json() for w in personal_words]

    dela_results_raw = dela_trie.search_pattern(cleaned_mask)
    final_results = []
    final_results.extend(personal_results_json)
    personal_mots_set = {p['mot'] for p in personal_results_json}
    for mot_obj in dela_results_raw:
        if mot_obj.texte_normalise not in personal_mots_set:
            final_results.append(mot_obj.to_json())

    limit = min(int(data.get("limit", 200)), 500)
    return jsonify({"results": final_results[:limit]}), 200

@app.route('/api/grids/generate', methods=['POST'])
@jwt_required(optional=True)
def generate_grid():
    user = get_current_user()
    data = request.get_json()
    size = data.get('size', {})
    width = min(int(size.get('width', 10)), 20)
    height = min(int(size.get('height', 10)), 20)
    seed = data.get('seed')
    
    word_list = []
    
    if data.get('use_global', True):
        all_dela_words = list(dela_trie.words)
        dela_sample = random.sample(all_dela_words, min(30000, len(all_dela_words)))
        word_list.extend(w for w in dela_sample if len(w) >= 2 and len(w) <= max(width, height))
    
    if user:
      active_dict = Dictionary.query.filter_by(user_id=user.id, is_active=True).first()
      if active_dict:
          word_list.extend([word.mot for word in active_dict.words if len(word.mot) >= 2 and len(word.mot) <= max(width, height)])

    if not word_list:
        return jsonify({"error": "Aucun mot de taille adéquate disponible."}), 400

    unique_words = list(set(word_list))
    
    generator = GridGenerator(width, height, unique_words, seed=seed)
    success = generator.generate()

    if not success:
        return jsonify({"error": "Impossible de générer une grille avec les mots fournis."}), 500
        
    return jsonify({"grid": generator.get_grid_data()}), 200

# --- Lancement de l'application ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)