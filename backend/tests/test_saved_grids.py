"""Grilles conservées (#24) : sauvegarde, relecture, suppression, et cloisonnement des comptes."""

import pytest

from tests.paths import FIXTURE_LAYOUTS_DIR
from tests.helpers import auth_headers, default_dictionary_id, send


@pytest.fixture
def grid_app(test_app, small_trie, monkeypatch):
    """Application avec un petit lexique : les mots corrigés doivent pouvoir être jugés."""
    monkeypatch.setattr(test_app, "dela_trie", small_trie)
    monkeypatch.setitem(test_app.config, "LAYOUTS_DIR", FIXTURE_LAYOUTS_DIR)
    return test_app


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


def test_a_saved_grid_comes_back_with_its_arrows(client):
    """#26 : les flèches ne sont pas stockées mais recalculées, donc les grilles d'avant en ont aussi."""
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]

    clues = client.get(f"/api/grids/{grid_id}", headers=headers).get_json()["grid"]["clues"]

    # AS commence en (1,0), juste à droite de la seule case noire : flèche vers la droite
    assert {clue["text"]: (clue["cell_x"], clue["cell_y"], clue["arrow"]) for clue in clues} == {
        "AS": (0, 0, "droite"),
        "ILE": (0, 0, "coudee_bas_droite"),
    }


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


def test_definitions_are_written_and_read_back(client):
    """#27 : les définitions s'écrivent au fil de la frappe, la grille elle-même ne bouge plus."""
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]

    response = send(client, "patch", f"/api/grids/{grid_id}",
                    {"definitions": {"1-0-across": "Champion", "0-1-across": "Terre entourée d'eau"}},
                    headers)

    assert response.status_code == 200
    assert response.get_json()["defined_count"] == 2
    relu = client.get(f"/api/grids/{grid_id}", headers=headers).get_json()
    assert relu["definitions"]["1-0-across"] == "Champion"


def test_an_emptied_definition_disappears(client):
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]
    send(client, "patch", f"/api/grids/{grid_id}", {"definitions": {"1-0-across": "Champion"}}, headers)

    send(client, "patch", f"/api/grids/{grid_id}", {"definitions": {"1-0-across": ""}}, headers)

    assert client.get(f"/api/grids/{grid_id}", headers=headers).get_json()["definitions"] == {}


def test_a_grid_can_be_renamed(client):
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]

    response = send(client, "patch", f"/api/grids/{grid_id}", {"name": "Spécial musique"}, headers)

    assert response.get_json()["name"] == "Spécial musique"


@pytest.mark.parametrize("body, expected_field", [
    ({"definitions": {"AS-1-0-across": "La clé portait le texte du mot"}}, "definitions"),
    ({"definitions": {"1-0-across": "x" * 121}}, "definitions.1-0-across"),
])
def test_a_malformed_definition_is_refused(client, body, expected_field):
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]

    response = send(client, "patch", f"/api/grids/{grid_id}", body, headers)

    assert response.status_code == 400
    assert expected_field in str(response.get_json()["details"]), response.get_json()


def test_another_account_cannot_write_definitions(client):
    owner = auth_headers(client)
    intruder = auth_headers(client)
    grid_id = save(client, owner, name="Privée").get_json()["id"]

    response = send(client, "patch", f"/api/grids/{grid_id}", {"definitions": {"1-0-across": "Volée"}}, intruder)

    assert response.status_code == 404
    assert client.get(f"/api/grids/{grid_id}", headers=owner).get_json()["definitions"] == {}


def test_a_letter_can_be_corrected_by_hand(grid_app, client):
    """ADR 0012 : l'auteur change un « O » en « E », et les deux mots concernés suivent."""
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]

    response = send(client, "patch", f"/api/grids/{grid_id}", {"cells": [{"x": 1, "y": 1, "char": "O"}]}, headers)

    assert response.status_code == 200, response.get_json()
    grid = response.get_json()["grid"]
    mots = {(w["x"], w["y"], w["direction"]): (w["text"], w["source"]) for w in grid["words"]}
    # ILE devient IOE, et le mot vertical qui traverse (1,1) suit
    assert mots[(0, 1, "across")] == ("IOE", "manuel")
    assert grid["cells"][4]["char"] == "O"


def test_a_definition_survives_a_letter_change(grid_app, client):
    """La clé est la position, pas le texte : c'est tout l'intérêt de la migration 0004."""
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]
    send(client, "patch", f"/api/grids/{grid_id}", {"definitions": {"0-1-across": "Terre entourée d'eau"}}, headers)

    send(client, "patch", f"/api/grids/{grid_id}", {"cells": [{"x": 1, "y": 1, "char": "O"}]}, headers)

    relu = client.get(f"/api/grids/{grid_id}", headers=headers).get_json()
    assert relu["definitions"]["0-1-across"] == "Terre entourée d'eau"


def test_a_word_outside_the_lexicon_is_flagged_not_refused(grid_app, client):
    """L'auteur reste maître : le mot est posé, et signalé."""
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]

    response = send(client, "patch", f"/api/grids/{grid_id}", {"cells": [{"x": 1, "y": 1, "char": "Z"}]}, headers)

    grid = response.get_json()["grid"]
    assert "IZE" in grid["unknown_words"]
    assert next(w for w in grid["words"] if w["text"] == "IZE")["in_lexicon"] is False


def test_a_word_from_the_authors_dictionary_counts_as_known(grid_app, client):
    """Un mot qu'il a lui-même rangé n'a pas à être signalé comme inconnu."""
    headers = auth_headers(client)
    dict_id = default_dictionary_id(client, headers)
    client.post(f"/api/dictionaries/{dict_id}/words", json={"mot": "IZE"}, headers=headers)
    grid_id = save(client, headers).get_json()["id"]

    response = send(client, "patch", f"/api/grids/{grid_id}", {"cells": [{"x": 1, "y": 1, "char": "Z"}]}, headers)

    assert "IZE" not in response.get_json()["grid"]["unknown_words"]


def test_a_letter_on_a_definition_cell_is_refused(grid_app, client):
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]

    response = send(client, "patch", f"/api/grids/{grid_id}", {"cells": [{"x": 0, "y": 0, "char": "Z"}]}, headers)

    assert response.status_code == 400
    assert "case définition" in str(response.get_json()["details"])


def test_suggestions_keep_the_crossings_valid(grid_app, client):
    """On ne propose que des mots qui laissent les mots perpendiculaires valides."""
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]

    response = send(client, "post", f"/api/grids/{grid_id}/suggestions",
                    {"x": 0, "y": 1, "direction": "across"}, headers)

    body = response.get_json()
    assert response.status_code == 200, body
    assert body["current"] == "ILE"
    # Chaque mot proposé respecte les lettres autorisées case par case
    for mot in body["words"]:
        assert len(mot) == 3
        for index, lettres in enumerate(body["allowed"]):
            assert not lettres or mot[index] in lettres


def test_notes_and_archiving_are_kept(grid_app, client):
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]

    send(client, "patch", f"/api/grids/{grid_id}", {"notes": "Idée : thème musique", "archived": True}, headers)

    relu = client.get(f"/api/grids/{grid_id}", headers=headers).get_json()
    assert relu["notes"] == "Idée : thème musique"
    assert relu["archived"] is True
    # Archivée : hors de la liste de travail, mais toujours là
    assert client.get("/api/grids?archived=false", headers=headers).get_json() == []
    assert len(client.get("/api/grids?archived=true", headers=headers).get_json()) == 1
    assert len(client.get("/api/grids", headers=headers).get_json()) == 1


def test_a_letter_can_be_erased_and_the_word_keeps_its_length(grid_app, client):
    """Retour arrière : la case se vide, le mot garde sa longueur et n'est plus jugé (ADR 0012)."""
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]

    response = send(client, "patch", f"/api/grids/{grid_id}", {"cells": [{"x": 1, "y": 1, "char": ""}]}, headers)

    assert response.status_code == 200, response.get_json()
    grid = response.get_json()["grid"]
    mot = next(w for w in grid["words"] if (w["x"], w["y"], w["direction"]) == (0, 1, "across"))
    assert mot["text"] == "I?E" and mot["length"] == 3 and mot["complete"] is False
    # Un mot inachevé n'est pas un mot inconnu : il ne doit pas être signalé comme tel
    assert mot["in_lexicon"] is None
    assert "I?E" not in grid["unknown_words"]
    assert grid["fill_ratio"] < 1


def test_suggestions_fill_the_holes_by_default(grid_app, client):
    """Le geste de l'auteur : effacer deux lettres, puis voir ce qui vient les remplacer."""
    headers = auth_headers(client)
    grid_id = save(client, headers).get_json()["id"]
    send(client, "patch", f"/api/grids/{grid_id}", {"cells": [{"x": 1, "y": 1, "char": ""}]}, headers)

    garde = send(client, "post", f"/api/grids/{grid_id}/suggestions",
                 {"x": 0, "y": 1, "direction": "across"}, headers).get_json()

    assert garde["current"] == "I?E"
    # Les lettres restées en place sont gardées : le motif ne touche qu'au trou
    assert garde["pattern"][0] == "I" and garde["pattern"][2] == "E"
    assert all(mot[0] == "I" and mot[2] == "E" for mot in garde["words"])

    remplace = send(client, "post", f"/api/grids/{grid_id}/suggestions",
                    {"x": 0, "y": 1, "direction": "across", "keep_letters": False}, headers).get_json()

    # En remplacement, plus rien n'est imposé par les lettres en place
    assert remplace["pattern"].count("?") >= garde["pattern"].count("?")
