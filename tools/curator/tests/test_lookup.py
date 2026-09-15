import pytest

from tools.curator.lookup import SERPER_URL, LookupService, search_links

SERPER_RESPONSE = {
    "answerBox": {"title": "Abaca", "snippet": "L'<b>abaca</b> est un bananier des Philippines.",
                  "link": "https://fr.wikipedia.org/wiki/Abaca"},
    "organic": [
        {"title": "Abaca — Wikipédia", "link": "https://fr.wikipedia.org/wiki/Abaca", "snippet": "Musa textilis…"},
        {"title": "Lien piégé", "link": "javascript:alert(1)", "snippet": "à ignorer"},
        {"title": "ABACA : définition", "link": "https://www.cnrtl.fr/definition/abaca", "snippet": "Plante textile."},
    ],
}


class FakeFetch:
    def __init__(self, responses=None, failing=()):
        self.responses = responses or {}
        self.failing = failing
        self.calls = []

    def __call__(self, url, data=None, headers=None):
        self.calls.append({"url": url, "data": data, "headers": headers})
        for prefix in self.failing:
            if url.startswith(prefix):
                raise OSError("service indisponible")
        for prefix, response in self.responses.items():
            if url.startswith(prefix):
                return response
        raise AssertionError(f"appel inattendu : {url}")


FREE_RESPONSES = {
    "https://fr.wikipedia.org/w/api.php": ["abaca", ["Abaca"], [""], ["https://fr.wikipedia.org/wiki/Abaca"]],
    "https://fr.wikipedia.org/api/rest_v1/page/summary/": {
        "title": "Abaca", "extract": "L'abaca est une espèce de bananier.",
        "content_urls": {"desktop": {"page": "https://fr.wikipedia.org/wiki/Abaca"}},
    },
    "https://fr.wiktionary.org/w/api.php": ["abaca", ["abaca", "abacas"], ["", ""],
                                            ["https://fr.wiktionary.org/wiki/abaca", "https://fr.wiktionary.org/wiki/abacas"]],
}


def test_google_results_with_a_serper_key(tmp_path):
    fetch = FakeFetch({SERPER_URL: SERPER_RESPONSE})
    service = LookupService("cle-secrete", tmp_path / "cache.json", fetch=fetch)

    result = service.lookup("abaca")

    assert result["provider"] == "google"
    assert result["answer"]["text"] == "L'abaca est un bananier des Philippines."  # balises retirées
    assert [r["source"] for r in result["results"]] == ["fr.wikipedia.org", "cnrtl.fr"]  # lien javascript: ignoré
    call = fetch.calls[0]
    assert call["headers"] == {"X-API-KEY": "cle-secrete"}
    assert call["data"]["q"].startswith("abaca") and call["data"]["gl"] == "fr"
    assert "cle-secrete" not in str(result)  # la clé ne revient jamais vers le navigateur


def test_free_sources_without_a_key(tmp_path):
    fetch = FakeFetch(FREE_RESPONSES)
    service = LookupService(None, tmp_path / "cache.json", fetch=fetch)

    result = service.lookup("abaca")

    assert result["provider"] == "libre"
    assert result["answer"]["source"] == "Wikipédia"
    assert [r["title"] for r in result["results"]] == ["abaca", "abacas"]
    assert not any(call["url"] == SERPER_URL for call in fetch.calls)


def test_unrelated_wikipedia_article_is_not_shown_as_the_answer(tmp_path):
    responses = {
        **FREE_RESPONSES,
        "https://fr.wikipedia.org/w/api.php": ["à accus", ["À cause d'un assassinat"], [""], ["https://fr.wikipedia.org/wiki/X"]],
        "https://fr.wiktionary.org/w/api.php": ["à accus", ["à cause de"], [""], ["https://fr.wiktionary.org/wiki/%C3%A0_cause_de"]],
    }
    fetch = FakeFetch(responses)

    result = LookupService(None, tmp_path / "cache.json", fetch=fetch).lookup("à accus")

    assert result["answer"] is None
    assert not any("summary" in call["url"] for call in fetch.calls)
    assert result["results"][0]["snippet"] == "Article proche du Wiktionnaire"


def test_falls_back_to_free_sources_when_google_fails(tmp_path):
    fetch = FakeFetch(FREE_RESPONSES, failing=(SERPER_URL,))
    service = LookupService("cle", tmp_path / "cache.json", fetch=fetch)

    assert service.lookup("abaca")["provider"] == "libre"


def test_results_are_cached_on_disk(tmp_path):
    cache = tmp_path / "cache.json"
    LookupService("cle", cache, fetch=FakeFetch({SERPER_URL: SERPER_RESPONSE})).lookup("abaca")
    fetch = FakeFetch()

    result = LookupService("cle", cache, fetch=fetch).lookup("Abaca")

    assert result["cached"] is True
    assert fetch.calls == []


def test_empty_results_are_not_cached(tmp_path):
    empty = {"https://fr.wikipedia.org/w/api.php": ["zzz", [], [], []],
             "https://fr.wiktionary.org/w/api.php": ["zzz", [], [], []]}
    service = LookupService(None, tmp_path / "cache.json", fetch=FakeFetch(empty))

    result = service.lookup("zzzzz")

    assert (result["answer"], result["results"]) == (None, [])
    assert "Google" in result["links"]
    assert not (tmp_path / "cache.json").exists()


def test_everything_failing_still_offers_search_links(tmp_path):
    fetch = FakeFetch(failing=("https://",))
    service = LookupService("cle", tmp_path / "cache.json", fetch=fetch)

    result = service.lookup("abaca")

    assert (result["answer"], result["results"]) == (None, [])
    assert set(result["links"]) == {"Google", "Larousse", "CNRTL", "Wiktionnaire"}


def test_search_links_escape_the_word():
    links = search_links("à l'arrache")

    assert links["Google"] == "https://www.google.com/search?q=%C3%A0%20l%27arrache"


def test_corrupted_cache_is_ignored(tmp_path):
    cache = tmp_path / "cache.json"
    cache.write_text("{pas du json", encoding="utf-8")

    service = LookupService(None, cache, fetch=FakeFetch(FREE_RESPONSES))

    assert service.lookup("abaca")["provider"] == "libre"


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    """Garde-fou : aucun test ne doit sortir sur Internet."""
    import urllib.request

    def refuse(*_args, **_kwargs):
        raise AssertionError("appel réseau réel interdit dans les tests")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
