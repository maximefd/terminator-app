# DANS backend/routes.py

import unicodedata
from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_current_user

# On importe depuis nos modules centraux
from models import db, Dictionary, PersonalWord
from grid_generator import GridGenerator, LayoutNotFoundError
from layout_catalog import available_formats, catalog
from schemas import (
    DictionaryCreateRequest,
    DictionaryUpdateRequest,
    GenerateRequest,
    SearchRequest,
    WordCreateRequest,
    parse_body,
)

# On crée un nouveau Blueprint pour les routes principales
main_bp = Blueprint('main', __name__, url_prefix='/api')

# --- FONCTIONS UTILITAIRES ---
def normalize_pattern(text):
    if not isinstance(text, str): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', text.upper()) if unicodedata.category(c) != 'Mn').strip()

def escape_like(value: str) -> str:
    """Échappe les jokers SQL (%, _) et le caractère d'échappement pour une clause LIKE."""
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

def get_owned_dictionary(user, dict_id):
    """Dictionnaire de l'utilisateur, ou 404 (on ne révèle pas l'existence des dictionnaires des autres)."""
    return Dictionary.query.filter_by(id=dict_id, user_id=user.id).first_or_404()

# Note : sur les routes @jwt_required(), get_current_user() ne renvoie jamais None.
# Un jeton dont le compte n'existe plus est rejeté en 401 (voir security.register_jwt_callbacks).

# --- ROUTES API ---

@main_bp.route('/status', methods=['GET'])
def status_check():
    dela_trie = current_app.dela_trie
    word_count = len(dela_trie.words) if dela_trie and hasattr(dela_trie, 'words') else 0
    manager = getattr(current_app, 'lexicon', None)
    lexicon = manager.info.as_dict() if manager and manager.info else None
    return jsonify({"status": "ok", "trie_loaded": dela_trie is not None, "word_count": word_count, "lexicon": lexicon}), 200

@main_bp.route('/dictionaries', methods=['GET'])
@jwt_required()
def get_dictionaries():
    user = get_current_user()

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
    payload = parse_body(DictionaryCreateRequest)

    max_dictionaries = current_app.config['MAX_DICTIONARIES_PER_USER']
    if len(user.dictionaries) >= max_dictionaries:
        return jsonify({'error': f"Limite atteinte : {max_dictionaries} dictionnaires maximum."}), 400
    if Dictionary.query.filter_by(user_id=user.id, name=payload.name).first():
        return jsonify({'error': f"Un dictionnaire nommé '{payload.name}' existe déjà."}), 409

    Dictionary.query.filter_by(user_id=user.id).update({'is_active': False})

    new_dict = Dictionary(name=payload.name, user_id=user.id, is_active=True)
    db.session.add(new_dict)
    db.session.commit()
    return jsonify(new_dict.to_json()), 201

@main_bp.route('/dictionaries/<int:dict_id>', methods=['PATCH'])
@jwt_required()
def update_dictionary(dict_id):
    user = get_current_user()
    dictionary = get_owned_dictionary(user, dict_id)
    payload = parse_body(DictionaryUpdateRequest)

    if payload.name is not None and payload.name != dictionary.name:
        if Dictionary.query.filter_by(user_id=user.id, name=payload.name).first():
            return jsonify({'error': f"Un dictionnaire nommé '{payload.name}' existe déjà."}), 409
        dictionary.name = payload.name

    if payload.is_active is True:
        Dictionary.query.filter(Dictionary.user_id == user.id).update({'is_active': False})
        dictionary.is_active = True

    db.session.commit()
    return jsonify(dictionary.to_json()), 200

@main_bp.route('/dictionaries/<int:dict_id>', methods=['DELETE'])
@jwt_required()
def delete_dictionary(dict_id):
    dictionary = get_owned_dictionary(get_current_user(), dict_id)
    db.session.delete(dictionary)
    db.session.commit()
    return jsonify({'message': 'Dictionnaire supprimé avec succès.'}), 200

@main_bp.route('/dictionaries/<int:dict_id>/words', methods=['GET'])
@jwt_required()
def get_words_in_dictionary(dict_id):
    dictionary = get_owned_dictionary(get_current_user(), dict_id)
    words = PersonalWord.query.filter_by(dictionary_id=dictionary.id).order_by(PersonalWord.id.desc()).all()
    return jsonify([word.to_json() for word in words]), 200

@main_bp.route('/dictionaries/<int:dict_id>/words', methods=['POST'])
@jwt_required()
def add_word_to_dictionary(dict_id):
    dictionary = get_owned_dictionary(get_current_user(), dict_id)
    payload = parse_body(WordCreateRequest)

    max_words = current_app.config['MAX_WORDS_PER_DICTIONARY']
    if PersonalWord.query.filter_by(dictionary_id=dictionary.id).count() >= max_words:
        return jsonify({'error': f"Limite atteinte : {max_words} mots maximum par dictionnaire."}), 400

    mot_upper = normalize_pattern(payload.mot)
    if PersonalWord.query.filter_by(dictionary_id=dictionary.id, mot=mot_upper).first():
        return jsonify({'error': f"Le mot '{payload.mot}' existe déjà."}), 409
    new_word = PersonalWord(mot=mot_upper, mot_affiche=payload.mot, definition=payload.definition or '', dictionary_id=dictionary.id)
    db.session.add(new_word)
    db.session.commit()
    return jsonify(new_word.to_json()), 201

@main_bp.route('/dictionaries/<int:dict_id>/words/<int:word_id>', methods=['DELETE'])
@jwt_required()
def delete_word_from_dictionary(dict_id, word_id):
    dictionary = get_owned_dictionary(get_current_user(), dict_id)
    word = PersonalWord.query.filter_by(id=word_id, dictionary_id=dictionary.id).first_or_404()
    db.session.delete(word)
    db.session.commit()
    return jsonify({'message': 'Mot supprimé avec succès.'}), 200

@main_bp.route('/search', methods=['POST'])
@jwt_required(optional=True)
def search_words():
    user = get_current_user()  # None pour un invité
    dela_trie = current_app.dela_trie
    payload = parse_body(SearchRequest)
    cleaned_mask = normalize_pattern(payload.mask)

    personal_results_json = []
    if user:
        active_dict = Dictionary.query.filter_by(user_id=user.id, is_active=True).first()
        if active_dict:
            # Les jokers SQL saisis par l'utilisateur sont échappés : seul « ? » est un joker
            sql_mask = escape_like(cleaned_mask).replace('?', '_')
            personal_words = (
                PersonalWord.query
                .filter(PersonalWord.dictionary_id == active_dict.id, PersonalWord.mot.like(sql_mask, escape='\\'))
                .limit(payload.limit)
                .all()
            )
            personal_results_json = [w.to_json() for w in personal_words]

    if not dela_trie: return jsonify({"error": "Dictionnaire principal non disponible."}), 503

    # Le parcours du Trie s'arrête dès que la limite est atteinte (masques très larges comme « ?????? »)
    dela_results_raw = dela_trie.search_pattern(cleaned_mask, limit=payload.limit + len(personal_results_json))
    final_results = personal_results_json
    personal_mots_set = {p['mot'] for p in personal_results_json}

    for word in dela_results_raw:
        if word not in personal_mots_set:
            final_results.append({"mot": word, "definition": None})

    return jsonify({"results": final_results[:payload.limit]}), 200

@main_bp.route('/grids/formats', methods=['GET'])
def list_grid_formats():
    """Liste les formats de grille pour lesquels au moins un layout existe."""
    return jsonify({"formats": available_formats(current_app.config.get('LAYOUTS_DIR'))}), 200

@main_bp.route('/layouts', methods=['GET'])
def list_layouts():
    """Catalogue des layouts valides, par format : identifiant, grille (x / -) et statistiques."""
    return jsonify({"formats": catalog(current_app.config.get('LAYOUTS_DIR'))}), 200

@main_bp.route('/grids/generate', methods=['POST'])
@jwt_required(optional=True)
def generate_grid():
    user = get_current_user()
    dela_trie = current_app.dela_trie
    if not dela_trie: return jsonify({"error": "Dictionnaire principal non disponible."}), 503

    payload = parse_body(GenerateRequest)
    width, height = payload.size.width, payload.size.height

    word_list = []
    if payload.use_global:
        # Tous les mots de longueur utile : un échantillon (ex-30 000 mots, ~4 % du DELA)
        # rendait presque tous les croisements impossibles.
        word_list.extend(w for w in dela_trie.words if 2 <= len(w) <= max(width, height))

    if user:
      active_dict = Dictionary.query.filter_by(user_id=user.id, is_active=True).first()
      if active_dict:
          word_list.extend([word.mot for word in active_dict.words if len(word.mot) >= 2 and len(word.mot) <= max(width, height)])

    if not word_list: return jsonify({"error": "Aucun mot de taille adéquate disponible."}), 400

    # Tri : ordre stable des mots
    unique_words = sorted(set(word_list))
    layouts_dir = current_app.config.get('LAYOUTS_DIR')

    try:
        generator = GridGenerator(
            width, height, unique_words,
            prebuilt_trie=dela_trie,
            seed=payload.seed,
            layouts_dir=layouts_dir,
            time_budget_s=current_app.config.get('GENERATION_TIME_BUDGET_S', 20),
        )
    except LayoutNotFoundError:
        formats = available_formats(layouts_dir)
        return jsonify({
            "error": f"Aucun layout disponible pour le format {width}x{height}.",
            "available_formats": formats,
        }), 400

    if not generator.generate():
        if generator.budget_exceeded:
            return jsonify({
                "error": "La génération a dépassé le temps imparti. Réessayez (nouveau tirage) ou choisissez un autre format.",
                "reason": "timeout",
            }), 422
        return jsonify({
            "error": "Impossible de générer une grille avec les mots fournis.",
            "reason": "no_solution",
        }), 422

    return jsonify({"grid": generator.get_grid_data()}), 200

# ROUTE RGPD : droit à l'effacement
@main_bp.route('/users/me', methods=['DELETE'])
@jwt_required()
def delete_self():
    """Supprime définitivement le compte de l'utilisateur et toutes ses données."""
    user = get_current_user()
    # Suppression via l'ORM : la cascade User -> Dictionary -> PersonalWord efface aussi
    # dictionnaires et mots (une suppression SQL en masse laissait les mots orphelins).
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Votre compte et toutes vos données ont été supprimés avec succès."}), 200
