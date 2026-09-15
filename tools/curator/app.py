"""Application Flask de la mini-app de curation."""

import hmac
import secrets
import threading
import time
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, redirect, request, send_from_directory, session

from tools.lexicon.decisions import DELETE, KEEP, NORMALIZED_WORD

from .gamification import DEFAULT_DAILY_GOAL
from .repository import QUEUE_SUGGESTIONS, LexiconRepository
from .stats import curation_stats
from .store import DecisionStore

STATIC_DIR = Path(__file__).parent / "static"
MIN_PIN_LENGTH = 6
MAX_PIN_FAILURES = 5
LOCKOUT_SECONDS = 300
MAX_WORDS_PER_DECISION = 50
# En-tête exigé sur toute écriture : un site tiers ne peut pas l'envoyer sans CORS (protection CSRF)
CSRF_HEADER = "X-Curator"

PUBLIC_PATHS = {"/login", "/static/login.js", "/static/style.css", "/static/icon.svg", "/manifest.webmanifest"}

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


class PinGuard:
    """Limite les essais de code PIN par adresse IP."""

    def __init__(self, max_failures: int = MAX_PIN_FAILURES, lockout_seconds: int = LOCKOUT_SECONDS):
        self.max_failures = max_failures
        self.lockout_seconds = lockout_seconds
        self._failures: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def is_locked(self, ip: str) -> bool:
        with self._lock:
            count, since = self._failures.get(ip, (0, 0.0))
            if count >= self.max_failures and time.monotonic() - since < self.lockout_seconds:
                return True
            if count >= self.max_failures:
                self._failures.pop(ip, None)
            return False

    def fail(self, ip: str) -> None:
        with self._lock:
            count, _ = self._failures.get(ip, (0, 0.0))
            self._failures[ip] = (count + 1, time.monotonic())

    def reset(self, ip: str) -> None:
        with self._lock:
            self._failures.pop(ip, None)


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _int_arg(name: str, default: int, low: int, high: int) -> int:
    try:
        value = int(request.args.get(name, default))
    except ValueError:
        value = default
    return max(low, min(high, value))


def _word_list(value) -> list[str] | None:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_WORDS_PER_DECISION:
        return None
    if not all(isinstance(word, str) and NORMALIZED_WORD.fullmatch(word) for word in value):
        return None
    return value


def create_app(db_path, decisions_path, pin: str, secret_key: str | None = None, testing: bool = False,
               daily_goal: int = DEFAULT_DAILY_GOAL) -> Flask:
    if not isinstance(pin, str) or len(pin) < MIN_PIN_LENGTH:
        raise ValueError(f"CURATOR_PIN doit contenir au moins {MIN_PIN_LENGTH} caractères (à définir dans .env).")
    if not isinstance(daily_goal, int) or not 1 <= daily_goal <= 5000:
        raise ValueError("CURATOR_DAILY_GOAL doit être un nombre entier entre 1 et 5000.")
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Base du lexique absente ({db_path}) : lancez d'abord `make lexicon-build`.")

    app = Flask(__name__, static_folder=None)
    app.config.update(
        SECRET_KEY=secret_key or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        MAX_CONTENT_LENGTH=16 * 1024,
        TESTING=testing,
    )
    repository = LexiconRepository(db_path)
    store = DecisionStore(decisions_path)
    guard = PinGuard()

    @app.before_request
    def require_authentication():
        if request.path in PUBLIC_PATHS:
            return None
        if not session.get("authenticated"):
            if request.path.startswith("/api/"):
                return _error("Code PIN requis.", 401)
            return redirect("/login")
        if request.method == "POST" and request.path.startswith("/api/") and request.headers.get(CSRF_HEADER) != "1":
            return _error("Requête refusée.", 403)
        return None

    @app.after_request
    def set_security_headers(response):
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    @app.errorhandler(404)
    def not_found(_error_):
        return _error("Introuvable.", 404)

    @app.errorhandler(413)
    def too_large(_error_):
        return _error("Requête trop volumineuse.", 413)

    # --- Pages et fichiers ---

    @app.get("/login")
    def login_page():
        return send_from_directory(STATIC_DIR, "login.html")

    @app.post("/login")
    def login():
        ip = request.remote_addr or "inconnue"
        if guard.is_locked(ip):
            return _error("Trop d'essais. Réessayez dans quelques minutes.", 429)
        submitted = (request.get_json(silent=True) or {}).get("pin")
        if isinstance(submitted, str) and hmac.compare_digest(submitted.encode(), pin.encode()):
            guard.reset(ip)
            session.clear()
            session.permanent = True
            session["authenticated"] = True
            return jsonify({"ok": True})
        guard.fail(ip)
        return _error("Code PIN incorrect.", 401)

    @app.post("/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/manifest.webmanifest")
    def manifest():
        return send_from_directory(STATIC_DIR, "manifest.webmanifest", mimetype="application/manifest+json")

    @app.get("/static/<path:filename>")
    def static_files(filename):
        return send_from_directory(STATIC_DIR, filename)

    # --- API ---

    @app.get("/api/queue")
    def queue():
        suggestion = request.args.get("suggestion") or None
        if suggestion is not None and suggestion not in QUEUE_SUGGESTIONS:
            return _error("Suggestion inconnue.", 400)
        state = store.state()
        cards, next_after = repository.queue(
            after=_int_arg("after", -1, -1, 10**9),
            limit=_int_arg("limit", 30, 1, 50),
            min_length=_int_arg("min_length", 2, 2, 99),
            max_length=_int_arg("max_length", 99, 2, 99),
            suggestion=suggestion,
            is_decided=state.__contains__,
        )
        for card in cards:
            card["family_size"] = len(_family_to_delete(card["norm"], state))
        return jsonify({"cards": cards, "next_after": next_after})

    @app.get("/api/cards")
    def cards():
        words = [w for w in request.args.get("words", "").split(",") if NORMALIZED_WORD.fullmatch(w)]
        return jsonify({"cards": repository.cards(words[:MAX_WORDS_PER_DECISION])})

    @app.post("/api/decisions")
    def decide():
        body = request.get_json(silent=True) or {}
        words = _word_list(body.get("words"))
        if words is None:
            return _error("Liste de mots invalide.", 400)
        if body.get("decision") not in (KEEP, DELETE):
            return _error("Décision invalide.", 400)
        if repository.existing(words) != set(words):
            return _error("Mot inconnu du lexique.", 400)
        store.append(words, body["decision"])
        return jsonify({"words": words})

    def _family_to_delete(word: str, state: dict[str, str]) -> list[str]:
        """Le mot et ses formes, sauf les mots courants et ceux gardés ou déjà supprimés."""
        return [norm for norm, suggestion in repository.family(word)
                if suggestion != "keep" and state.get(norm) not in (KEEP, DELETE)]

    @app.post("/api/decisions/family")
    def delete_family():
        word = (request.get_json(silent=True) or {}).get("word")
        if not isinstance(word, str) or not NORMALIZED_WORD.fullmatch(word):
            return _error("Mot invalide.", 400)
        words = _family_to_delete(word, store.state())
        if not words:
            return _error("Aucun mot à supprimer dans cette famille.", 400)
        store.append(words, DELETE)
        return jsonify({"words": words})

    @app.post("/api/undo")
    def undo():
        words = store.undo()
        return jsonify({"words": words, "cards": repository.cards(words)})

    @app.get("/api/stats")
    def stats():
        return jsonify(curation_stats(repository, store, daily_goal=daily_goal))

    return app
