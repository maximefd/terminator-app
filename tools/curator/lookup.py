"""Recherche d'un mot sur le web, affichée dans la bulle « Chercher ce mot » du curateur.

- Avec une clé Serper (`SERPER_API_KEY`) : résultats Google (réponse mise en avant, fiche, 5 premiers liens).
- Sans clé, ou si Google ne répond pas : résumé Wikipédia et articles du Wiktionnaire (gratuits, sans clé).

Les appels partent du serveur du curateur, uniquement vers ces services, à partir d'un mot du lexique :
la clé n'est jamais envoyée au navigateur. Les réponses sont nettoyées (texte seul, liens http(s) seulement)
et mises en cache sur disque pour ne pas dépenser deux fois une recherche.
"""

import json
import logging
import os
import re
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

from tools.lexicon.normalize import normalize_word

USER_AGENT = "TerminatorCurator/1.0 (outil personnel de curation de lexique)"
TIMEOUT_S = 6
MAX_RESULTS = 5
SERPER_URL = "https://google.serper.dev/search"
WIKIPEDIA_API = "https://fr.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY = "https://fr.wikipedia.org/api/rest_v1/page/summary/"
WIKTIONARY_API = "https://fr.wiktionary.org/w/api.php"
HTML_TAG = re.compile(r"<[^>]+>")


def http_json(url: str, data: dict | None = None, headers: dict | None = None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST" if body else "GET")
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        return json.loads(response.read().decode("utf-8"))


def _clean(text, limit: int = 300) -> str:
    cleaned = " ".join(HTML_TAG.sub("", str(text or "")).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0] + "…"


def _safe_link(url) -> str | None:
    return url if isinstance(url, str) and url.startswith(("https://", "http://")) else None


def _domain(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.removeprefix("www.")


def search_links(word: str) -> dict:
    """Recherches à ouvrir d'un appui, quand la bulle ne suffit pas."""
    quoted = urllib.parse.quote(word)
    return {
        "Google": f"https://www.google.com/search?q={quoted}",
        "Larousse": f"https://www.larousse.fr/dictionnaires/francais/{quoted}",
        "CNRTL": f"https://www.cnrtl.fr/definition/{quoted}",
        "Wiktionnaire": f"https://fr.wiktionary.org/wiki/{quoted}",
    }


class LookupService:
    def __init__(self, serper_api_key: str | None = None, cache_path=None, fetch: Callable = http_json):
        self.serper_api_key = serper_api_key or None
        self.cache_path = Path(cache_path) if cache_path else None
        self._fetch = fetch
        self._lock = threading.Lock()
        self._cache = self._read_cache()

    @classmethod
    def from_environment(cls, cache_path) -> "LookupService":
        return cls(os.environ.get("SERPER_API_KEY"), cache_path)

    # --- Cache ---

    def _read_cache(self) -> dict:
        if not self.cache_path or not self.cache_path.exists():
            return {}
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logging.warning("Cache de recherche illisible, ignoré : %s", self.cache_path)
            return {}

    def _write_cache(self) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.cache_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(self._cache, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_path, self.cache_path)

    # --- Recherche ---

    def lookup(self, word: str) -> dict:
        """`word` : forme affichée du mot (avec accents)."""
        key = word.lower()
        with self._lock:
            cached = self._cache.get(key)
        if cached:
            return {**cached, "cached": True}

        result = None
        if self.serper_api_key:
            try:
                result = self._google(word)
            except Exception:
                logging.warning("Recherche Google (Serper) indisponible pour %r", word, exc_info=True)
        if result is None or not (result["answer"] or result["results"]):
            result = self._free_sources(word)
        result["links"] = search_links(word)

        if result["answer"] or result["results"]:
            with self._lock:
                self._cache[key] = result
                self._write_cache()
        return {**result, "cached": False}

    def _google(self, word: str) -> dict:
        data = self._fetch(SERPER_URL, data={"q": f"{word} définition", "gl": "fr", "hl": "fr", "num": MAX_RESULTS},
                           headers={"X-API-KEY": self.serper_api_key})
        answer = None
        box = data.get("answerBox") or {}
        box_text = box.get("answer") or box.get("snippet")
        if box_text:
            answer = {"title": _clean(box.get("title"), 120), "text": _clean(box_text),
                      "link": _safe_link(box.get("link")), "source": "Google"}
        graph = data.get("knowledgeGraph") or {}
        if answer is None and graph.get("description"):
            answer = {"title": _clean(graph.get("title"), 120), "text": _clean(graph["description"]),
                      "link": _safe_link(graph.get("descriptionLink")),
                      "source": _clean(graph.get("descriptionSource") or "Google", 60)}

        results = []
        for item in data.get("organic") or []:
            link = _safe_link(item.get("link"))
            if not link:
                continue
            results.append({"title": _clean(item.get("title"), 120), "snippet": _clean(item.get("snippet"), 240),
                            "link": link, "source": _domain(link)})
            if len(results) == MAX_RESULTS:
                break
        return {"provider": "google", "answer": answer, "results": results}

    def _free_sources(self, word: str) -> dict:
        answer, results = None, []
        try:
            search = self._fetch(f"{WIKIPEDIA_API}?" + urllib.parse.urlencode(
                {"action": "opensearch", "search": word, "limit": 1, "namespace": 0, "format": "json"}))
            titles = search[1] if isinstance(search, list) and len(search) > 1 else []
            # Le résumé n'est affiché que pour l'article du mot lui-même (« à accus » ne doit pas
            # donner le résumé d'un film intitulé « À cause d'un assassinat »)
            if titles and normalize_word(titles[0]) == normalize_word(word):
                summary = self._fetch(WIKIPEDIA_SUMMARY + urllib.parse.quote(titles[0].replace(" ", "_"), safe=""))
                if summary.get("extract"):
                    page = ((summary.get("content_urls") or {}).get("desktop") or {}).get("page")
                    answer = {"title": _clean(summary.get("title"), 120), "text": _clean(summary["extract"]),
                              "link": _safe_link(page), "source": "Wikipédia"}
        except Exception:
            logging.warning("Wikipédia indisponible pour %r", word, exc_info=True)
        try:
            search = self._fetch(f"{WIKTIONARY_API}?" + urllib.parse.urlencode(
                {"action": "opensearch", "search": word, "limit": MAX_RESULTS, "namespace": 0, "format": "json"}))
            if isinstance(search, list) and len(search) > 3:
                for title, link in zip(search[1], search[3]):
                    link = _safe_link(link)
                    if link:
                        exact = normalize_word(title) == normalize_word(word)
                        results.append({"title": _clean(title, 120),
                                        "snippet": "Article du Wiktionnaire" if exact else "Article proche du Wiktionnaire",
                                        "link": link, "source": "fr.wiktionary.org"})
        except Exception:
            logging.warning("Wiktionnaire indisponible pour %r", word, exc_info=True)
        return {"provider": "libre", "answer": answer, "results": results}
