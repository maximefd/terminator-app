import json

import pytest

from tests.paths import FIXTURE_LAYOUTS_DIR

FIXTURE_FORMATS = [{"width": 5, "height": 5, "layouts": 1}]


@pytest.fixture
def grid_app(test_app, small_trie, monkeypatch):
    """Application avec un petit dictionnaire et les layouts de test."""
    monkeypatch.setattr(test_app, "dela_trie", small_trie)
    monkeypatch.setitem(test_app.config, "TEMPLATES_DIR", FIXTURE_LAYOUTS_DIR)
    return test_app


def post_generate(client, body):
    return client.post("/api/grids/generate", data=json.dumps(body), content_type="application/json")


def test_formats_endpoint_lists_available_formats(grid_app, client):
    response = client.get("/api/grids/formats")

    assert response.status_code == 200
    assert response.get_json()["formats"] == FIXTURE_FORMATS


def test_generate_returns_a_filled_grid(grid_app, client):
    response = post_generate(client, {"size": {"width": 5, "height": 5}, "seed": 42})

    assert response.status_code == 200, response.get_json()
    grid = response.get_json()["grid"]
    assert grid["fill_ratio"] == 1.0
    assert len(grid["cells"]) == 25
    assert grid["words"]


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
