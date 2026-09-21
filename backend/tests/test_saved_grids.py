"""Grilles conservées (#24) : sauvegarde, relecture, suppression, et cloisonnement des comptes."""

import pytest

from tests.helpers import auth_headers, send


def grid_payload(**overrides):
    """Une grille minuscule au format que renvoie /api/grids/generate."""
    grid = {
        "width": 3,
        "height": 2,
        "layout": "3x2-001",
        "seed": 42,
        "cells": [
            {"x": 0, "y": 0, "char": "", "is_black": True},
            {"x": 1, "y": 0, "char": "A", "is_black": False},
            {"x": 2, "y": 0, "char": "S", "is_black": False},
            {"x": 0, "y": 1, "char": "I", "is_black": False},
            {"x": 1, "y": 1, "char": "L", "is_black": False},
            {"x": 2, "y": 1, "char": "E", "is_black": False},
        ],
        "words": [
            {"text": "AS", "x": 1, "y": 0, "direction": "across", "source": "must"},
            {"text": "ILE", "x": 0, "y": 1, "direction": "across", "source": "common"},
        ],
        "fill_ratio": 1.0,
        "wish_ratio": 0.5,
        "must_words": ["AS"],
    }
    grid.update(overrides)
    return grid


def save(client, headers, name="Ma grille", **overrides):
    return send(client, "post", "/api/grids", {"name": name, "grid": grid_payload(**overrides)}, headers)


def test_saved_grid_comes_back_as_it_was(client):
    headers = auth_headers(client)

    created = save(client, headers)
    assert created.status_code == 201, created.get_json()
    summary = created.get_json()
    assert summary["name"] == "Ma grille"
    assert (summary["width"], summary["height"]) == (3, 2)
    assert summary["word_count"] == 2
    assert summary["must_words"] == ["AS"]

    listing = client.get("/api/grids", headers=headers).get_json()
    assert [g["id"] for g in listing] == [summary["id"]]
    # La liste ne transporte pas les cases : c'est tout l'intérêt d'un résumé
    assert "grid" not in listing[0]

    full = client.get(f"/api/grids/{summary['id']}", headers=headers).get_json()
    assert full["grid"]["cells"] == grid_payload()["cells"]
    assert full["grid"]["layout"] == "3x2-001"
    assert full["grid"]["seed"] == 42


def test_grid_without_a_name_gets_one(client):
    headers = auth_headers(client)

    response = send(client, "post", "/api/grids", {"grid": grid_payload()}, headers)

    assert response.status_code == 201
    # Un repère plutôt qu'un numéro : le format et le jour
    assert response.get_json()["name"].startswith("3×2 du ")


def test_most_recent_grid_comes_first(client):
    headers = auth_headers(client)

    first = save(client, headers, name="Ancienne").get_json()
    second = save(client, headers, name="Récente").get_json()

    listing = client.get("/api/grids", headers=headers).get_json()
    assert [g["id"] for g in listing] == [second["id"], first["id"]]


def test_deleted_grid_is_gone(client):
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]

    assert send(client, "delete", f"/api/grids/{grid_id}", None, headers).status_code == 200
    assert client.get(f"/api/grids/{grid_id}", headers=headers).status_code == 404
    assert client.get("/api/grids", headers=headers).get_json() == []


@pytest.mark.parametrize("method, body", [
    ("get", None),
    ("delete", None),
])
def test_another_account_never_sees_the_grid(client, method, body):
    owner = auth_headers(client)
    intruder = auth_headers(client)
    grid_id = save(client, owner, name="Privée").get_json()["id"]

    response = send(client, method, f"/api/grids/{grid_id}", body, intruder)

    # 404 et non 403 : l'existence d'une grille d'autrui ne se révèle pas
    assert response.status_code == 404
    assert client.get("/api/grids", headers=intruder).get_json() == []
    assert client.get(f"/api/grids/{grid_id}", headers=owner).status_code == 200


def test_saving_needs_an_account(client):
    assert send(client, "post", "/api/grids", {"grid": grid_payload()}).status_code == 401
    assert client.get("/api/grids").status_code == 401


@pytest.mark.parametrize("broken, expected_field", [
    ({"cells": [{"x": 0, "y": 0, "char": "A", "is_black": "oui"}]}, "grid.cells.0.is_black"),
    ({"words": [{"text": "AS", "x": 0, "y": 0, "direction": "diagonale", "source": "must"}]},
     "grid.words.0.direction"),
    ({"width": 99}, "grid.width"),
    ({"layout": ""}, "grid.layout"),
])
def test_a_malformed_grid_is_refused(client, broken, expected_field):
    headers = auth_headers(client)

    response = send(client, "post", "/api/grids", {"grid": grid_payload(**broken)}, headers)

    assert response.status_code == 400
    body = response.get_json()
    # Le refus désigne la case ou le mot fautif, et pas seulement « grille invalide »
    assert [detail["field"] for detail in body["details"]] == [expected_field], body


def test_quota_is_enforced(client, test_app):
    headers = auth_headers(client)
    previous = test_app.config["MAX_GRIDS_PER_USER"]
    test_app.config["MAX_GRIDS_PER_USER"] = 1
    try:
        assert save(client, headers, name="La première").status_code == 201
        refused = save(client, headers, name="La deuxième")
        assert refused.status_code == 400
        assert "1 grille conservée" in refused.get_json()["error"]
    finally:
        test_app.config["MAX_GRIDS_PER_USER"] = previous
