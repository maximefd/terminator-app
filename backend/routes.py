# DANS backend/routes.py

import unicodedata
from datetime import datetime

from flask import Blueprint, abort, jsonify, current_app, request
from flask_jwt_extended import jwt_required, get_current_user, unset_jwt_cookies

# On importe depuis nos modules centraux
from models import db, Dictionary, PersonalWord, SavedGrid
from engine.difficulty import request_difficulty
from engine.word_repository import WholeLexicon
from engine.grid_edit import (
    HOLE, allowed_letters, apply_letters, cells_of_slot, fill_ratio, letters_of, slot_at,
    words_from_cells,
)
from generation_slots import GenerationBusy, generation_slot
from grid_generator import GridGenerator, LayoutNotFoundError
from layout_catalog import available_formats, catalog, format_slot_count, suggest_layouts_for
from auth import password_matches
from schemas import (
    AccountDeletionRequest,
    DictionaryCreateRequest,
    DifficultyRequest,
    DictionaryUpdateRequest,
    GenerateRequest,
    GridUpdateRequest,
    SaveGridRequest,
    SlotRef,
    SearchRequest,
    WordCreateRequest,
    parse_body,
)
from security import client_ip

# On crée un nouveau Blueprint pour les routes principales
main_bp = Blueprint('main', __name__, url_prefix='/api')

# --- FONCTIONS UTILITAIRES ---
def normalize_pattern(text):
    if not isinstance(text, str): return ""
    return ''.join(c for c in unicodedata.normalize('NFD', text.upper()) if unicodedata.category(c) != 'Mn').strip()

def escape_like(value: str) -> str:
    """Échappe les jokers SQL (%, _) et le caractère d'échappement pour une clause LIKE."""
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

def get_owned_grid(user, grid_id):
    """Grille de l'utilisateur, ou 404 (même règle que pour les dictionnaires)."""
    return SavedGrid.query.filter_by(id=grid_id, user_id=user.id).first_or_404()

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

@main_bp.route('/grids/difficulty', methods=['POST'])
def grid_difficulty():
    """Ce que coûtent des mots imposés, **sans générer** : réponse immédiate, à chaque frappe.

    Les taux viennent de 4 700 générations mesurées (voir engine/difficulty.py). Donner ce chiffre
    avant de chercher vaut mieux que de laisser l'auteur attendre 20 s pour un échec.
    """
    payload = parse_body(DifficultyRequest)
    words = [normalize_pattern(word) for word in payload.must_words]
    slots = None
    if payload.size:
        slots = format_slot_count(payload.size.width, payload.size.height,
                                  current_app.config.get('LAYOUTS_DIR'))
    estimate = request_difficulty(words, slots)

    # Le moteur reste pur : c'est ici qu'on sait ce que contient le lexique chargé. Un mot qui n'y
    # figure pas se place quand même (le pool des mots imposés étend l'index), mais la mesure d'où
    # sort le taux a tiré ses mots **dans** le lexique : l'auteur doit savoir qu'il en sort.
    dela_trie = current_app.dela_trie
    known = dela_trie.words if dela_trie else set()
    for detail in estimate["words"]:
        detail["in_lexicon"] = detail["word"] in known
    estimate["unknown_words"] = [d["word"] for d in estimate["words"] if not d["in_lexicon"]]

    return jsonify(estimate), 200

@main_bp.route('/grids/generate', methods=['POST'])
@jwt_required(optional=True)
def generate_grid():
    user = get_current_user()
    dela_trie = current_app.dela_trie
    if not dela_trie: return jsonify({"error": "Dictionnaire principal non disponible."}), 503

    payload = parse_body(GenerateRequest)
    width, height = payload.size.width, payload.size.height

    longest = max(width, height)

    # Tous les mots de longueur utile : un échantillon (ex-30 000 mots, ~4 % du DELA) rendait presque
    # tous les croisements impossibles. Désignés sans être recopiés : trier 700 000 mots à chaque
    # requête coûtait jusqu'à 0,7 s avant la première lettre posée (ADR 0013).
    common_words = WholeLexicon(longest) if payload.use_global else ()

    # Pool « souhaité » : les mots saisis, plus ceux des dictionnaires **explicitement choisis**.
    # Le dictionnaire actif n'y entre plus de lui-même ([ADR 0011](docs/adr/0011-dictionnaires-choisis.md)) :
    # une grille thématique n'a aucune raison d'hériter du dictionnaire que la recherche utilise.
    # Ces mots sont essayés avant le lexique commun et restent valides aux croisements même s'ils
    # n'y figurent pas (#17).
    wish_words = [normalize_pattern(word) for word in payload.wish_words]

    # Ceux de l'utilisateur connecté, et eux seuls. Un dictionnaire qui ne lui appartient pas répond
    # 404 comme partout ailleurs — on ne révèle pas son existence (ADR 0007).
    for dictionary_id in payload.wish_dictionary_ids:
        if not user:
            abort(404)
        theme = get_owned_dictionary(user, dictionary_id)
        wish_words.extend(word.mot for word in theme.words if 2 <= len(word.mot) <= longest)

    # Un mot obligatoire est aussi souhaité : inutile de le répéter dans les deux listes (ADR 0007)
    must_words = sorted({normalize_pattern(word) for word in payload.must_words})

    if not payload.use_global and not wish_words and not must_words:
        return jsonify({"error": "Aucun mot de taille adéquate disponible."}), 400

    # Une génération occupe un cœur jusqu'à 20 s : au plus quelques-unes à la fois, une par visiteur
    # (ADR 0013). Un compte est un visiteur où qu'il se connecte ; un invité, une adresse.
    visitor = f"compte:{user.id}" if user else f"ip:{client_ip()}"
    try:
        with generation_slot(current_app.config['GENERATION_LOCK_DIR'], visitor,
                             current_app.config['GENERATION_MAX_CONCURRENT']):
            return run_generation(width, height, common_words, dela_trie, payload, wish_words, must_words)
    except GenerationBusy as busy:
        message = (
            "Une génération est déjà en cours pour vous : attendez son résultat avant d'en lancer une autre."
            if busy.reason == "visitor" else
            "Le générateur est occupé. Réessayez dans quelques secondes."
        )
        response = jsonify({"error": message, "reason": f"busy_{busy.reason}"})
        response.headers["Retry-After"] = "5"
        return response, 429


def run_generation(width, height, common_words, dela_trie, payload, wish_words, must_words):
    """Construit le générateur et résout la grille ; appelé une fois la place de génération obtenue."""
    layouts_dir = current_app.config.get('LAYOUTS_DIR')

    try:
        generator = GridGenerator(
            width, height, common_words,
            prebuilt_trie=dela_trie,
            seed=payload.seed,
            layouts_dir=layouts_dir,
            time_budget_s=current_app.config.get('GENERATION_TIME_BUDGET_S', 20),
            wish_words=sorted(set(wish_words)),
            must_words=must_words,
            frequency_mode=payload.frequency_mode,
        )
    except LayoutNotFoundError:
        formats = available_formats(layouts_dir)
        return jsonify({
            "error": f"Aucun layout disponible pour le format {width}x{height}.",
            "available_formats": formats,
        }), 400

    # Refus AVANT toute résolution : inutile de chercher 20 s un mot qui n'entre dans aucun layout
    # du format. Le générateur a examiné tous les candidats, pas seulement celui qu'il a tiré.
    problems = generator.must_word_problems
    if problems:
        return jsonify({
            "error": "Ces mots obligatoires n'entrent pas dans ce layout.",
            "reason": "must_words",
            "details": problems,
            "suggested_layouts": suggest_layouts_for(must_words, layouts_dir),
        }), 422

    if not generator.generate():
        if generator.unplaced_must_words:
            return jsonify({
                "error": "Impossible de placer tous les mots obligatoires dans le temps imparti.",
                "reason": "must_words_unplaced",
                "unplaced": generator.unplaced_must_words,
            }), 422
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

# --- GRILLES CONSERVÉES ---

@main_bp.route('/grids', methods=['POST'])
@jwt_required()
def save_grid():
    """Conserve une grille générée, telle qu'elle a été produite (voir SavedGrid)."""
    user = get_current_user()
    payload = parse_body(SaveGridRequest)

    maximum = current_app.config['MAX_GRIDS_PER_USER']
    if SavedGrid.query.filter_by(user_id=user.id).count() >= maximum:
        accord = "s" if maximum > 1 else ""
        return jsonify({'error': f"Limite atteinte : {maximum} grille{accord} conservée{accord} au maximum."}), 400

    grid = payload.grid
    # Sans nom choisi, un repère vaut mieux qu'« Grille 37 » : le format et le jour
    name = payload.name or f"{grid.width}×{grid.height} du {datetime.now():%d/%m/%Y}"

    saved = SavedGrid(
        name=name,
        layout_id=grid.layout,
        width=grid.width,
        height=grid.height,
        seed=grid.seed,
        payload=grid.model_dump(),
        user_id=user.id,
    )
    db.session.add(saved)
    db.session.commit()
    return jsonify(saved.summary()), 201


def known_words(user, words: set[str]) -> set[str]:
    """Parmi ces mots, ceux que l'auteur peut considérer comme connus : le lexique, plus les siens.

    Un mot qu'il a lui-même ajouté à un dictionnaire n'a pas à être signalé comme inconnu — c'est
    précisément là qu'il range ce que le lexique n'a pas.
    """
    dela_trie = current_app.dela_trie
    known = {word for word in words if dela_trie and word in dela_trie.words}
    reste = words - known
    if user and reste:
        personnels = (PersonalWord.query
                      .join(Dictionary, PersonalWord.dictionary_id == Dictionary.id)
                      .filter(Dictionary.user_id == user.id, PersonalWord.mot.in_(reste))
                      .all())
        known |= {word.mot for word in personnels}
    return known


def annotated_grid(user, grid: SavedGrid) -> dict:
    """La grille, ses flèches, et ce que le lexique dit de chacun de ses mots.

    Un mot **inachevé** — l'auteur a effacé des lettres pour retravailler la zone — n'est pas jugé :
    « P?RTE » n'est pas un mot inconnu, c'est un mot en cours.
    """
    data = grid.to_json()
    mots = data["grid"].get("words", [])
    termines = {word["text"] for word in mots if word.get("complete", HOLE not in word["text"])}
    connus = known_words(user, termines)
    for word in mots:
        word["in_lexicon"] = word["text"] in connus if word["text"] in termines else None
    data["grid"]["unknown_words"] = sorted(termines - connus)
    return data


@main_bp.route('/grids', methods=['GET'])
@jwt_required()
def list_grids():
    """Les grilles conservées, la plus récente d'abord, sans leurs cases.

    Les archivées sont écartées par défaut : elles restent en base, hors de la liste de travail.
    """
    user = get_current_user()
    query = SavedGrid.query.filter_by(user_id=user.id)
    archived = request.args.get('archived')
    if archived in ('true', 'false'):
        query = query.filter(SavedGrid.archived.is_(archived == 'true'))
    grids = query.order_by(SavedGrid.date_creation.desc(), SavedGrid.id.desc()).all()
    return jsonify([grid.summary() for grid in grids]), 200


@main_bp.route('/grids/<int:grid_id>', methods=['GET'])
@jwt_required()
def get_grid(grid_id):
    user = get_current_user()
    return jsonify(annotated_grid(user, get_owned_grid(user, grid_id))), 200


@main_bp.route('/grids/<int:grid_id>/suggestions', methods=['POST'])
@jwt_required()
def grid_suggestions(grid_id):
    """Les mots qui entreraient à cet emplacement **sans casser ses croisements** (ADR 0012).

    C'est la cohérence d'arc du solveur ramenée à un seul emplacement : on calcule d'abord, case par
    case, les lettres qui laissent le mot perpendiculaire valide, puis on ne garde que les mots du
    lexique qui les respectent toutes. Proposer un mot qui casse un croisement ne rendrait service
    à personne.
    """
    user = get_current_user()
    grid = get_owned_grid(user, grid_id)
    payload = parse_body(SlotRef)
    dela_trie = current_app.dela_trie
    if not dela_trie:
        return jsonify({"error": "Dictionnaire principal non disponible."}), 503

    cells = (grid.payload or {}).get("cells", [])
    slot = slot_at(cells, payload.x, payload.y, payload.direction)
    if slot is None:
        return jsonify({"error": "Aucun mot ne passe par cette case dans ce sens."}), 404

    allowed = allowed_letters(cells, slot, lambda word: word in dela_trie.words)
    # Par défaut on **comble les trous** : les lettres déjà posées restent, seules les cases vides
    # sont à remplir. C'est le geste de l'auteur qui efface deux lettres pour retravailler une zone.
    # `keep_letters: false` propose au contraire de remplacer le mot entier.
    posees = letters_of(cells)
    motif = ""
    for index, position in enumerate(cells_of_slot(slot)):
        lettre = posees.get(position) or ""
        if payload.keep_letters and lettre:
            motif += lettre
        elif len(allowed[index]) == 1:
            # Une case dont le croisement n'admet qu'une lettre : autant la fixer dans le motif
            motif += next(iter(allowed[index]))
        else:
            motif += "?"

    limite = current_app.config['MAX_SUGGESTIONS']
    candidats = dela_trie.search_pattern(motif, limit=limite * 20)
    retenus = [
        mot for mot in candidats
        if all(not lettres or mot[i] in lettres for i, lettres in enumerate(allowed))
    ]
    # Les mots les plus courants d'abord : ce sont ceux qu'un lecteur reconnaîtra
    retenus.sort(key=lambda mot: (-dela_trie.frequency(mot), mot))

    return jsonify({
        "pattern": motif,
        "allowed": ["".join(sorted(lettres)) for lettres in allowed],
        "words": retenus[:limite],
        "truncated": len(retenus) > limite,
        "current": "".join(posees.get(position) or HOLE for position in cells_of_slot(slot)),
        "keep_letters": payload.keep_letters,
    }), 200


@main_bp.route('/grids/<int:grid_id>', methods=['PATCH'])
@jwt_required()
def update_grid(grid_id):
    """Renomme une grille conservée, ou enregistre ses définitions."""
    grid = get_owned_grid(get_current_user(), grid_id)
    payload = parse_body(GridUpdateRequest)

    if payload.name is not None:
        grid.name = payload.name
    if payload.definitions is not None:
        # Une définition vidée disparaît : on ne garde pas de chaînes vides en base
        grid.definitions = {key: text for key, text in payload.definitions.items() if text}
    if payload.notes is not None:
        grid.notes = payload.notes
    if payload.archived is not None:
        grid.archived = payload.archived

    if payload.cells is not None:
        contenu = dict(grid.payload or {})
        cells, problemes = apply_letters(contenu.get("cells", []),
                                         [edit.model_dump() for edit in payload.cells])
        if problemes:
            return jsonify({"error": "Modification refusée.", "details": problemes}), 400
        contenu["cells"] = cells
        # Les mots se recalculent depuis les lettres : c'est la règle de l'ADR 0012
        contenu["words"] = words_from_cells(cells, contenu.get("words"))
        # Une grille trouée n'est plus pleine : le taux de remplissage doit le dire
        contenu["fill_ratio"] = fill_ratio(cells)
        grid.payload = contenu

    db.session.commit()
    if payload.cells is not None:
        return jsonify(annotated_grid(get_current_user(), grid)), 200
    return jsonify(grid.summary()), 200


@main_bp.route('/grids/<int:grid_id>', methods=['DELETE'])
@jwt_required()
def delete_grid(grid_id):
    grid = get_owned_grid(get_current_user(), grid_id)
    db.session.delete(grid)
    db.session.commit()
    return jsonify({'message': 'Grille supprimée.'}), 200


# --- COMPTE ---

@main_bp.route('/users/me', methods=['GET'])
@jwt_required()
def get_self():
    """Le compte connecté et ce qu'il contient : ce que sa suppression effacerait (#79)."""
    user = get_current_user()
    words = (db.session.query(db.func.count(PersonalWord.id))
             .join(Dictionary).filter(Dictionary.user_id == user.id).scalar())
    return jsonify({
        "email": user.email,
        "email_verified": user.email_verified_at is not None,
        "dictionaries": len(user.dictionaries),
        "words": words,
        "grids": len(user.grids),
    }), 200


# ROUTE RGPD : droit à l'effacement
@main_bp.route('/users/me', methods=['DELETE'])
@jwt_required()
def delete_self():
    """Supprime définitivement le compte de l'utilisateur et toutes ses données.

    Le mot de passe est redemandé : avec le jeton seul, quiconque l'aurait volé (le jeton vit dans le
    navigateur) pourrait effacer le compte. Un mauvais mot de passe répond 403 et non 401 : le frontend
    lit un 401 comme une session expirée et déconnecterait l'utilisateur.
    """
    user = get_current_user()
    payload = parse_body(AccountDeletionRequest)
    if not password_matches(user.password, payload.password):
        return jsonify({"error": "Mot de passe incorrect."}), 403
    # Suppression via l'ORM : la cascade User -> Dictionary -> PersonalWord efface aussi
    # dictionnaires et mots (une suppression SQL en masse laissait les mots orphelins).
    db.session.delete(user)
    db.session.commit()
    response = jsonify({"message": "Votre compte et toutes vos données ont été supprimés avec succès."})
    unset_jwt_cookies(response)  # les jetons d'un compte supprimé sont refusés : autant effacer les cookies
    return response, 200
