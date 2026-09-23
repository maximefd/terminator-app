"""Autorisation : un utilisateur n'accède jamais aux dictionnaires et mots d'un autre."""

import pytest

from tests.helpers import auth_headers, default_dictionary_id, send


@pytest.fixture
def owner_and_intruder(client):
    owner = auth_headers(client)
    intruder = auth_headers(client)
    dict_id = default_dictionary_id(client, owner)
    word = send(client, "post", f"/api/dictionaries/{dict_id}/words", {"mot": "secret"}, owner).get_json()
    intruder_dict_id = default_dictionary_id(client, intruder)
    return {
        "owner": owner,
        "intruder": intruder,
        "dict_id": dict_id,
        "word_id": word["id"],
        "intruder_dict_id": intruder_dict_id,
    }


@pytest.mark.parametrize("method, path, body", [
    ("get", "/api/dictionaries/{dict_id}/words", None),
    ("patch", "/api/dictionaries/{dict_id}", {"name": "Volé", "is_active": True}),
    ("delete", "/api/dictionaries/{dict_id}", None),
    ("post", "/api/dictionaries/{dict_id}/words", {"mot": "intrus"}),
    ("delete", "/api/dictionaries/{dict_id}/words/{word_id}", None),
    ("delete", "/api/dictionaries/{intruder_dict_id}/words/{word_id}", None),
])
def test_intruder_gets_404_and_owner_data_is_untouched(client, owner_and_intruder, method, path, body):
    ctx = owner_and_intruder
    url = path.format(**ctx)

    response = send(client, method, url, body, ctx["intruder"])

    assert response.status_code == 404
    owner_dictionaries = client.get("/api/dictionaries", headers=ctx["owner"]).get_json()
    assert [(d["id"], d["name"]) for d in owner_dictionaries] == [(ctx["dict_id"], "Dictionnaire par défaut")]
    owner_words = client.get(f"/api/dictionaries/{ctx['dict_id']}/words", headers=ctx["owner"]).get_json()
    assert [w["mot"] for w in owner_words] == ["SECRET"]


def test_search_only_returns_the_callers_personal_words(client, test_app, small_trie, monkeypatch, owner_and_intruder):
    monkeypatch.setattr(test_app, "dela_trie", small_trie)
    ctx = owner_and_intruder

    def personal_results(headers):
        results = send(client, "post", "/api/search", {"mask": "S?CRET"}, headers).get_json()["results"]
        return [r["mot"] for r in results if r.get("source") == "PERSONNEL"]

    assert personal_results(ctx["owner"]) == ["SECRET"]
    assert personal_results(ctx["intruder"]) == []
    assert personal_results(None) == []


@pytest.mark.parametrize("method, path", [
    ("get", "/api/dictionaries"),
    ("post", "/api/dictionaries"),
    ("get", "/api/dictionaries/1/words"),
    ("delete", "/api/users/me"),
    ("get", "/api/users/me"),
    ("post", "/api/auth/email/resend"),
])
def test_protected_routes_require_authentication(client, method, path):
    response = send(client, method, path)

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentification requise."
