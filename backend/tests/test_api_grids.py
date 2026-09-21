import json
from typing import get_args

import pytest
import routes
from engine.grid_solver import FREQUENCY_MODES
from schemas import GenerateRequest

from tests.helpers import auth_headers, default_dictionary_id
from tests.paths import FIXTURE_LAYOUTS_DIR

FIXTURE_FORMATS = [{"width": 5, "height": 5, "layouts": 1}]


@pytest.fixture
def grid_app(test_app, small_trie, monkeypatch):
    """Application avec un petit dictionnaire et les layouts de test."""
    monkeypatch.setattr(test_app, "dela_trie", small_trie)
    monkeypatch.setitem(test_app.config, "LAYOUTS_DIR", FIXTURE_LAYOUTS_DIR)
    return test_app


def post_generate(client, body, headers=None):
    return client.post("/api/grids/generate", data=json.dumps(body), content_type="application/json",
                       headers=headers or {})


def test_formats_endpoint_lists_available_formats(grid_app, client):
    response = client.get("/api/grids/formats")

    assert response.status_code == 200
    assert response.get_json()["formats"] == FIXTURE_FORMATS


def test_layouts_endpoint_lists_the_catalog(grid_app, client):
    response = client.get("/api/layouts")

    assert response.status_code == 200
    formats = response.get_json()["formats"]
    assert [(f["width"], f["height"]) for f in formats] == [(5, 5)]
    layout = formats[0]["layouts"][0]
    assert (layout["id"], layout["rows"][0]) == ("5x5-001", "x-x-x")
    assert layout["stats"]["words"] > 0


def test_generate_returns_a_filled_grid(grid_app, client):
    response = post_generate(client, {"size": {"width": 5, "height": 5}, "seed": 42})

    assert response.status_code == 200, response.get_json()
    grid = response.get_json()["grid"]
    assert grid["fill_ratio"] == 1.0
    assert len(grid["cells"]) == 25
    assert grid["words"]


def test_generated_grid_says_where_each_definition_goes(grid_app, client):
    """#26 : sans les flèches, l'auteur ne sait pas quelle case porte quelle définition."""
    response = post_generate(client, {"size": {"width": 5, "height": 5}, "seed": 42})

    grid = response.get_json()["grid"]
    assert len(grid["clues"]) == len(grid["words"])
    for clue in grid["clues"]:
        assert clue["arrow"] in ("droite", "bas", "coudee_bas_droite", "coudee_droite_bas")
        assert clue["exit"] in ("right", "bottom")
        # La case qui porte la définition est bien une case noire de cette grille
        noire = next(c for c in grid["cells"] if c["x"] == clue["cell_x"] and c["y"] == clue["cell_y"])
        assert noire["is_black"]


def test_the_active_personal_dictionary_feeds_the_wished_pool(grid_app, client, monkeypatch):
    """#17 : les mots personnels étaient mélangés au lexique commun, donc ignorés à l'indexation."""
    headers = auth_headers(client)
    dict_id = default_dictionary_id(client, headers)
    assert client.post(f"/api/dictionaries/{dict_id}/words", json={"mot": "Zorgl"},
                       headers=headers).status_code == 201

    generators = []
    real_generator = routes.GridGenerator

    def spy(*args, **kwargs):
        generators.append((args[2], kwargs["wish_words"], real_generator(*args, **kwargs)))
        return generators[-1][2]

    monkeypatch.setattr(routes, "GridGenerator", spy)

    response = post_generate(client, {"size": {"width": 5, "height": 5}, "seed": 42}, headers)

    assert response.status_code == 200, response.get_json()
    common_words, wish_words, generator = generators[0]
    assert wish_words == ["ZORGL"] and "ZORGL" not in common_words
    assert generator.repository.source_of("ZORGL") == "wish"
    assert "wish_ratio" in response.get_json()["grid"]


def test_a_must_word_too_long_is_refused_before_solving(grid_app, client):
    """#18 : un mot de 9 lettres n'entre dans aucun emplacement d'un 5x5, inutile de chercher 20 s."""
    response = post_generate(client, {"size": {"width": 5, "height": 5}, "must_words": ["Zorglubes"]})

    assert response.status_code == 422
    body = response.get_json()
    assert body["reason"] == "must_words"
    assert body["details"][0]["word"] == "ZORGLUBES"
    assert "9 lettres" in body["details"][0]["problem"]
    assert body["suggested_layouts"] == []  # aucun layout du catalogue de test n'a d'emplacement si long


def test_a_must_word_that_cannot_cross_is_named_in_the_failure(grid_app, client):
    """Sans lexique commun, le mot imposé est seul : les emplacements existent mais rien ne peut le croiser.

    La vérification préalable passe donc (la longueur convient), et c'est la résolution qui échoue :
    le cas ne dépend d'aucun hasard du lexique.
    """
    response = post_generate(client, {"size": {"width": 5, "height": 5}, "seed": 1,
                                      "use_global": False, "must_words": ["Zzzzz"]})

    assert response.status_code == 422
    body = response.get_json()
    assert body["reason"] == "must_words_unplaced"
    assert body["unplaced"] == ["ZZZZZ"]


def test_a_must_word_is_validated_like_any_other_input(grid_app, client):
    assert post_generate(client, {"size": {"width": 5, "height": 5}, "must_words": ["A"]}).status_code == 400
    assert post_generate(client, {"size": {"width": 5, "height": 5}, "must_words": "PORTE"}).status_code == 400
    assert post_generate(client, {"size": {"width": 5, "height": 5},
                                  "must_words": ["MOT"] * 51}).status_code == 400


def test_the_frequency_mode_can_be_chosen_per_request(grid_app, client):
    """Désactivé par défaut, activable à la demande : l'auteur arbitre qualité contre fiabilité."""
    assert post_generate(client, {"size": {"width": 5, "height": 5}, "seed": 42,
                                  "frequency_mode": "exact"}).status_code == 200
    assert post_generate(client, {"size": {"width": 5, "height": 5},
                                  "frequency_mode": "zorglub"}).status_code == 400


def test_the_schema_offers_exactly_the_modes_the_solver_knows():
    """Les deux listes doivent rester identiques : une valeur acceptée mais inconnue ferait une 500."""
    literal, _none = get_args(GenerateRequest.model_fields["frequency_mode"].annotation)

    assert set(get_args(literal)) == set(FREQUENCY_MODES)


# --- Dictionnaires thématiques (ADR 0007) ---

def wish_words_sent(client, monkeypatch, body, headers=None):
    """Mots souhaités réellement transmis au générateur pour cette requête."""
    captured = []
    real_generator = routes.GridGenerator

    def spy(*args, **kwargs):
        captured.append(kwargs["wish_words"])
        return real_generator(*args, **kwargs)

    monkeypatch.setattr(routes, "GridGenerator", spy)
    response = post_generate(client, body, headers)
    return response, captured


def test_a_themed_dictionary_feeds_the_wished_pool(grid_app, client, monkeypatch):
    headers = auth_headers(client)
    default_id = default_dictionary_id(client, headers)
    theme_id = client.post("/api/dictionaries", json={"name": "Cuisine"}, headers=headers).get_json()["id"]
    client.post(f"/api/dictionaries/{theme_id}/words", json={"mot": "Zorgl"}, headers=headers)
    # Le dictionnaire actif redevient celui par défaut : le mot ne peut venir que du thème demandé
    client.patch(f"/api/dictionaries/{default_id}", json={"is_active": True}, headers=headers)

    response, captured = wish_words_sent(
        client, monkeypatch,
        {"size": {"width": 5, "height": 5}, "seed": 42, "wish_dictionary_ids": [theme_id]}, headers)

    assert response.status_code == 200, response.get_json()
    assert captured[0] == ["ZORGL"]


def test_a_theme_that_is_not_asked_for_stays_out(grid_app, client, monkeypatch):
    headers = auth_headers(client)
    default_id = default_dictionary_id(client, headers)
    theme_id = client.post("/api/dictionaries", json={"name": "Cuisine"}, headers=headers).get_json()["id"]
    client.post(f"/api/dictionaries/{theme_id}/words", json={"mot": "Zorgl"}, headers=headers)
    client.patch(f"/api/dictionaries/{default_id}", json={"is_active": True}, headers=headers)

    response, captured = wish_words_sent(
        client, monkeypatch, {"size": {"width": 5, "height": 5}, "seed": 42}, headers)

    assert response.status_code == 200
    assert captured[0] == []


def test_the_dictionary_of_another_user_is_not_reachable(grid_app, client):
    """Autorisation : un dictionnaire qui n'est pas le sien répond 404, jamais 403."""
    owner = auth_headers(client)
    theme_id = client.post("/api/dictionaries", json={"name": "Cuisine"}, headers=owner).get_json()["id"]
    intruder = auth_headers(client)

    response = post_generate(client, {"size": {"width": 5, "height": 5},
                                      "wish_dictionary_ids": [theme_id]}, intruder)

    assert response.status_code == 404


def test_a_guest_cannot_ask_for_a_themed_dictionary(grid_app, client):
    assert post_generate(client, {"size": {"width": 5, "height": 5},
                                  "wish_dictionary_ids": [1]}).status_code == 404


def test_the_themed_dictionaries_are_validated(grid_app, client):
    assert post_generate(client, {"size": {"width": 5, "height": 5},
                                  "wish_dictionary_ids": list(range(1, 12))}).status_code == 400
    assert post_generate(client, {"size": {"width": 5, "height": 5},
                                  "wish_dictionary_ids": [0]}).status_code == 400
    assert post_generate(client, {"size": {"width": 5, "height": 5},
                                  "wish_dictionary_ids": "deux"}).status_code == 400


# --- Difficulté annoncée avant de générer (#73) ---

def post_difficulty(client, body):
    return client.post("/api/grids/difficulty", data=json.dumps(body), content_type="application/json")


def test_the_difficulty_is_told_before_generating(grid_app, client):
    """L'auteur doit voir le coût de ses mots en les tapant, pas après 20 s d'attente."""
    response = post_difficulty(client, {"must_words": ["Rue", "Bibliothèques"]})

    assert response.status_code == 200
    body = response.get_json()
    assert body["hardest"] == "BIBLIOTHEQUES"  # normalisé comme partout
    assert 0 < body["success_rate"] < 1
    assert body["level"] in ("facile", "moyen", "difficile", "très difficile")
    assert "souhaité" in body["advice"]


def test_the_chosen_grid_size_changes_the_estimate(grid_app, client):
    """Le pourcentage affiché doit dépendre de la taille choisie : c'est ce que l'auteur compare."""
    sans = post_difficulty(client, {"must_words": ["Rue", "Sel"]}).get_json()
    avec = post_difficulty(client, {"must_words": ["Rue", "Sel"],
                                    "size": {"width": 5, "height": 5}}).get_json()

    assert sans["size_class"] is None
    assert avec["size_class"] == "petite"  # le layout de test compte 8 emplacements


def test_no_word_is_no_difficulty(grid_app, client):
    body = post_difficulty(client, {"must_words": []}).get_json()

    assert body["success_rate"] == 1.0 and body["advice"] is None


def test_the_difficulty_request_is_validated(grid_app, client):
    assert post_difficulty(client, {"must_words": ["A"]}).status_code == 400
    assert post_difficulty(client, {"must_words": ["MOT"] * 51}).status_code == 400


def test_generate_unknown_format_returns_available_formats(grid_app, client):
    response = post_generate(client, {"size": {"width": 9, "height": 9}})

    assert response.status_code == 400
    assert response.get_json()["available_formats"] == FIXTURE_FORMATS


def test_generate_invalid_size_returns_400(grid_app, client):
    response = post_generate(client, {"size": {"width": "abc", "height": 5}})

    assert response.status_code == 400


def test_generate_timeout_returns_422(grid_app, client, monkeypatch):
    monkeypatch.setitem(grid_app.config, "GENERATION_TIME_BUDGET_S", -1)

    response = post_generate(client, {"size": {"width": 5, "height": 5}, "seed": 1})

    assert response.status_code == 422
    assert response.get_json()["reason"] == "timeout"


def test_generate_without_dictionary_returns_503(test_app, client, monkeypatch):
    monkeypatch.setattr(test_app, "dela_trie", None)

    response = post_generate(client, {"size": {"width": 5, "height": 5}})

    assert response.status_code == 503
