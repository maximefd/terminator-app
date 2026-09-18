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
