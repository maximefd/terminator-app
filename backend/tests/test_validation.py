"""Validation des entrées : toute donnée invalide est rejetée en 400 avec un message clair."""

import pytest

from tests.helpers import auth_headers, default_dictionary_id, register, send, unique_email


def assert_rejected(response):
    assert response.status_code == 400, response.get_json()
    body = response.get_json()
    assert isinstance(body["error"], str) and body["error"]
    return body


@pytest.mark.parametrize("body", [
    {},
    {"email": "pas-un-email", "password": "password123"},
    {"email": "marie@exemple.fr", "password": "court"},
    {"email": "marie@exemple.fr", "password": "x" * 129},
    {"email": 123, "password": "password123"},
    {"email": "x" * 250 + "@exemple.fr", "password": "password123"},
])
def test_register_rejects_invalid_payloads(client, body):
    assert_rejected(send(client, "post", "/api/auth/register", body))


def test_register_error_names_the_field(client):
    body = assert_rejected(send(client, "post", "/api/auth/register", {"email": unique_email(), "password": "court"}))
    assert "mot de passe" in body["error"]
    assert body["details"][0]["field"] == "password"


def test_validation_errors_never_echo_the_submitted_value(client):
    response = send(client, "post", "/api/auth/register", {"email": "a@exemple.fr", "password": "s3cr3"})
    assert_rejected(response)
    assert "s3cr3" not in response.get_data(as_text=True)


def test_non_json_body_is_rejected(client):
    response = client.post("/api/auth/login", data="email=a&password=b", content_type="application/x-www-form-urlencoded")
    body = assert_rejected(response)
    assert "JSON" in body["error"]


def test_email_is_case_insensitive(client):
    email = f"Marie.Curie.{unique_email()}".replace("@exemple.fr", "@Exemple.FR")
    register(client, email)

    login = send(client, "post", "/api/auth/login", {"email": email.lower(), "password": "password123"})
    assert login.status_code == 200

    duplicate = send(client, "post", "/api/auth/register", {"email": email.upper(), "password": "password123"})
    assert duplicate.status_code == 409


@pytest.mark.parametrize("name", ["", "   ", "x" * 101, "<script>alert(1)</script>", "nom; DROP TABLE"])
def test_dictionary_name_validation(client, name):
    headers = auth_headers(client)
    assert_rejected(send(client, "post", "/api/dictionaries", {"name": name}, headers))


def test_valid_dictionary_name_is_accepted(client):
    headers = auth_headers(client)
    response = send(client, "post", "/api/dictionaries", {"name": "  Thème : cuisine (2026)  "}, headers)
    assert response.status_code == 201
    assert response.get_json()["name"] == "Thème : cuisine (2026)"


def test_dictionary_is_active_must_be_a_boolean(client):
    headers = auth_headers(client)
    dict_id = default_dictionary_id(client, headers)
    assert_rejected(send(client, "patch", f"/api/dictionaries/{dict_id}", {"is_active": "true"}, headers))


@pytest.mark.parametrize("body", [
    {"mot": "a"},
    {"mot": "abc1"},
    {"mot": "<b>gras</b>"},
    {"mot": "x" * 31},
    {"mot": "-tiret"},
    {"mot": "valide", "definition": "x" * 256},
    {"definition": "sans mot"},
])
def test_word_validation(client, body):
    headers = auth_headers(client)
    dict_id = default_dictionary_id(client, headers)
    assert_rejected(send(client, "post", f"/api/dictionaries/{dict_id}/words", body, headers))


@pytest.mark.parametrize("mot", ["porte-clé", "aujourd'hui", "Œuvre", "pomme de terre"])
def test_valid_french_words_are_accepted(client, mot):
    headers = auth_headers(client)
    dict_id = default_dictionary_id(client, headers)
    response = send(client, "post", f"/api/dictionaries/{dict_id}/words", {"mot": mot, "definition": "ok"}, headers)
    assert response.status_code == 201, response.get_json()


@pytest.mark.parametrize("body", [
    {"mask": ""},
    {"mask": "A%"},
    {"mask": "A_B"},
    {"mask": "x" * 31},
    {"mask": "P??LE", "limit": 0},
    {"mask": "P??LE", "limit": 501},
    {"mask": "P??LE", "limit": "beaucoup"},
    {},
])
def test_search_validation(client, body):
    assert_rejected(send(client, "post", "/api/search", body))


@pytest.mark.parametrize("body", [
    {"size": {"width": 25, "height": 6}},
    {"size": {"width": 1, "height": 6}},
    {"size": "6x7"},
    {"size": {"width": 6, "height": 7}, "seed": -1},
    {"size": {"width": 6, "height": 7}, "seed": 1.5},
    {"size": {"width": 6, "height": 7}, "use_global": "oui"},
])
def test_generate_validation(client, test_app, small_trie, monkeypatch, body):
    monkeypatch.setattr(test_app, "dela_trie", small_trie)
    assert_rejected(send(client, "post", "/api/grids/generate", body))
