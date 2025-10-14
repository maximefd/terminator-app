# DANS backend/routes.py

import random
import unicodedata
from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

# On importe depuis nos modules centraux
from models import db, User, Dictionary, PersonalWord
from grid_generator import GridGenerator

# On crée un nouveau Blueprint pour les routes principales
main_bp = Blueprint('main', __name__, url_prefix='/api')

# --- FONCTIONS UTILITAIRES ---
def normalize_pattern(text):
    if not isinstance(text, str): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', text.upper()) if unicodedata.category(c) != 'Mn').strip()

def get_current_user():
    user_id = get_jwt_identity()
    return db.session.get(User, user_id) if user_id else None

# --- ROUTES API ---

@main_bp.route('/status', methods=['GET'])
def status_check():
    dela_trie = current_app.dela_trie
    word_count = len(dela_trie.words) if dela_trie and hasattr(dela_trie, 'words') else 0
    return jsonify({"status": "ok", "trie_loaded": dela_trie is not None, "word_count": word_count}), 200

@main_bp.route('/dictionaries', methods=['GET'])
@jwt_required()
def get_dictionaries():
    user = get_current_user()
    if not user: return jsonify({"error": "Utilisateur non trouvé"}), 404
    
    # AMÉLIORATION : Si l'utilisateur n'a pas de dictionnaire, on lui en crée un.
    if not user.dictionaries:
        default_dict = Dictionary(name="Dictionnaire par défaut", user_id=user.id, is_active=True)
        db.session.add(default_dict)
        db.session.commit()
        # On rafraîchit l'objet 'user' pour qu'il contienne le nouveau dictionnaire
        db.session.refresh(user)

    return jsonify([d.to_json() for d in user.dictionaries]), 200

@main_bp.route('/dictionaries', methods=['POST'])
@jwt_required()
def create_dictionary():
    user = get_current_user()
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name: return jsonify({'error': 'Le nom du dictionnaire est manquant.'}), 400
    if Dictionary.query.filter_by(user_id=user.id, name=name).first():
        return jsonify({'error': f"Un dictionnaire nommé '{name}' existe déjà."}), 409
    
    Dictionary.query.filter_by(user_id=user.id).update({'is_active': False})
    
    new_dict = Dictionary(name=name, user_id=user.id, is_active=True)
    db.session.add(new_dict)
    db.session.commit()
    return jsonify(new_dict.to_json()), 201

@main_bp.route('/dictionaries/<int:dict_id>', methods=['PATCH'])
@jwt_required()
def update_dictionary(dict_id):
    user = get_current_user()
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=user.id).first_or_404()
    data = request.get_json()
    if 'name' in data: dictionary.name = data['name'].strip()
    
    if data.get('is_active') is True:
        Dictionary.query.filter(Dictionary.user_id == user.id).update({'is_active': False})
        dictionary.is_active = True
        
    db.session.commit()
    return jsonify(dictionary.to_json()), 200

@main_bp.route('/dictionaries/<int:dict_id>', methods=['DELETE'])
@jwt_required()
def delete_dictionary(dict_id):
    user = get_current_user()
    dictionary = Dictionary.query.filter_by(id=dict_id, user_id=user.id).first_or_404()
    db.session.delete(dictionary)
    db.session.commit()
    return jsonify({'message': 'Dictionnaire supprimé avec succès.'}), 200

@main_bp.route('/dictionaries/<int:dict_id>/words', methods=['GET'])
@jwt_required()
def get_words_in_dictionary(dict_id):
    user = get_current_user()
    Dictionary.query.filter_by(id=dict_id, user_id=user.id).first_or_404()
    words = PersonalWord.query.filter_by(dictionary_id=dict_id).order_by(PersonalWord.id.desc()).all()
    return jsonify([word.to_json() for word in words]), 200

@main_bp.route('/dictionaries/<int:dict_id>/words', methods=['POST'])
@jwt_required()
def add_word_to_dictionary(dict_id):
    user = get_current_user()
    Dictionary.query.filter_by(id=dict_id, user_id=user.id).first_or_404()
    data = request.get_json()
    mot_affiche = data.get('mot', '').strip()
    if not mot_affiche: return jsonify({'error': 'Le mot est obligatoire.'}), 400
    mot_upper = normalize_pattern(mot_affiche)
    if PersonalWord.query.filter_by(dictionary_id=dict_id, mot=mot_upper).first():
        return jsonify({'error': f"Le mot '{mot_affiche}' existe déjà."}), 409
    new_word = PersonalWord(mot=mot_upper, mot_affiche=mot_affiche, definition=data.get('definition', ''), dictionary_id=dict_id)
    db.session.add(new_word)
    db.session.commit()
    return jsonify(new_word.to_json()), 201
    
@main_bp.route('/dictionaries/<int:dict_id>/words/<int:word_id>', methods=['DELETE'])
@jwt_required()
def delete_word_from_dictionary(dict_id, word_id):
    user = get_current_user()
    Dictionary.query.filter_by(id=dict_id, user_id=user.id).first_or_404()
    word = PersonalWord.query.filter_by(id=word_id, dictionary_id=dict_id).first_or_404()
    db.session.delete(word)
    db.session.commit()
    return jsonify({'message': 'Mot supprimé avec succès.'}), 200

@main_bp.route('/search', methods=['POST'])
@jwt_required(optional=True)
def search_words():
    user = get_current_user()
    dela_trie = current_app.dela_trie
    data = request.json
    mask = data.get('mask', '')
    cleaned_mask = normalize_pattern(mask)
    
    personal_results_json = []
    if user:
        active_dict = Dictionary.query.filter_by(user_id=user.id, is_active=True).first()
        if active_dict:
            sql_mask = cleaned_mask.replace('?', '_')
            personal_words = PersonalWord.query.filter(PersonalWord.dictionary_id == active_dict.id, PersonalWord.mot.like(sql_mask)).all()
            personal_results_json = [w.to_json() for w in personal_words]

    if not dela_trie: return jsonify({"error": "Dictionnaire principal non disponible."}), 503

    dela_results_raw = dela_trie.search_pattern(cleaned_mask)
    final_results = personal_results_json
    personal_mots_set = {p['mot'] for p in personal_results_json}
    
    for mot_obj in dela_results_raw:
        if mot_obj.texte_normalise not in personal_mots_set:
            final_results.append(mot_obj.to_json())

    limit = min(int(data.get("limit", 200)), 500)
    return jsonify({"results": final_results[:limit]}), 200

@main_bp.route('/grids/generate', methods=['POST'])
@jwt_required(optional=True)
def generate_grid():
    user = get_current_user()
    dela_trie = current_app.dela_trie
    data = request.get_json()
    size = data.get('size', {})
    width = min(int(size.get('width', 10)), 20)
    height = min(int(size.get('height', 10)), 20)
    seed = data.get('seed')
    
    word_list = []
    if data.get('use_global', True) and dela_trie:
        all_dela_words = list(dela_trie.words)
        dela_sample = random.sample(all_dela_words, min(30000, len(all_dela_words)))
        word_list.extend(w for w in dela_sample if len(w) >= 2 and len(w) <= max(width, height))
    
    if user:
      active_dict = Dictionary.query.filter_by(user_id=user.id, is_active=True).first()
      if active_dict:
          word_list.extend([word.mot for word in active_dict.words if len(word.mot) >= 2 and len(word.mot) <= max(width, height)])

    if not word_list: return jsonify({"error": "Aucun mot de taille adéquate disponible."}), 400

    unique_words = list(set(word_list))
    
    generator = GridGenerator(width, height, unique_words, seed=seed)
    success = generator.generate()

    if not success: return jsonify({"error": "Impossible de générer une grille avec les mots fournis."}), 500
        
    return jsonify({"grid": generator.get_grid_data()}), 200