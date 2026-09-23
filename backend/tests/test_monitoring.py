"""Suivi des erreurs (Sentry) : inactif sans DSN, et rien d'identifiant dans les rapports."""

import pytest
import sentry_sdk
from sentry_sdk.transport import Transport

import monitoring
from app import create_app

TEST_SETTINGS = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "JWT_SECRET_KEY": "test-secret-key-long-enough-for-hs256-signing",
    "RATELIMIT_ENABLED": False,
}
DSN = "https://clepublique@o0.ingest.de.sentry.io/0"
# Loin du code qui plante : Sentry joint au rapport les lignes voisines de l'erreur, et elles feraient
# apparaître ces valeurs sans que rien ne fuie vraiment
SECRETS = {"password": "motdepasse-secret", "bearer": "jeton-secret", "csrf": "csrf-secret",
           "cookie": "cookie-de-session-secret"}


class CaptureTransport(Transport):
    """Garde les rapports au lieu de les envoyer."""

    def __init__(self, options=None):
        super().__init__(options)
        self.events = []

    def capture_envelope(self, envelope):
        self.events += [item.payload.json for item in envelope.items if item.type == "event"]


@pytest.fixture
def sentry_events(monkeypatch):
    """Sentry réellement initialisé, mais ses rapports restent ici ; désactivé après le test."""
    transport = CaptureTransport()
    real_init = sentry_sdk.init
    monkeypatch.setattr(monitoring.sentry_sdk, "init", lambda **options: real_init(transport=transport, **options))
    yield transport.events
    real_init()  # sans DSN : client inactif


def test_without_dsn_nothing_is_initialised(monkeypatch):
    calls = []
    monkeypatch.setattr(monitoring.sentry_sdk, "init", lambda **options: calls.append(options))

    create_app(TEST_SETTINGS)

    assert calls == []


def test_with_dsn_only_errors_are_sent_without_personal_data(monkeypatch):
    calls = []
    monkeypatch.setattr(monitoring.sentry_sdk, "init", lambda **options: calls.append(options))

    create_app({**TEST_SETTINGS, "SENTRY_DSN": DSN, "APP_ENV": "production", "RELEASE": "abc123"})

    options = calls[0]
    assert (options["dsn"], options["environment"], options["release"]) == (DSN, "production", "abc123")
    assert options["send_default_pii"] is False
    assert options["max_request_body_size"] == "never"
    assert options["traces_sample_rate"] == 0
    assert options["include_local_variables"] is False


def test_an_unexpected_error_reaches_sentry_without_secrets(sentry_events):
    """Le gestionnaire d'erreurs intercepte tout : sans report_exception, Sentry ne verrait rien."""
    app = create_app({**TEST_SETTINGS, "SENTRY_DSN": DSN})

    @app.route("/api/panne", methods=["POST"])
    def panne():
        raise RuntimeError("panne de test")

    response = app.test_client().post(
        "/api/panne",
        json={"password": SECRETS["password"]},
        headers={"Authorization": f"Bearer {SECRETS['bearer']}", "Cookie": f"access_token_cookie={SECRETS['cookie']}",
                 "X-CSRF-TOKEN": SECRETS["csrf"], "User-Agent": "test"},
    )
    sentry_sdk.flush()

    assert response.status_code == 500
    assert len(sentry_events) == 1
    event = sentry_events[0]
    assert event["exception"]["values"][-1]["value"] == "panne de test"
    report = repr(event)
    for secret in SECRETS.values():
        assert secret not in report
    assert set(event["request"]["headers"]) <= {"User-Agent", "Content-Type", "Content-Length", "Host"}


def test_scrub_keeps_only_harmless_headers():
    event = {
        "request": {
            "url": "https://api.terminator.fr/api/auth/login",
            "headers": {"Authorization": "Bearer x", "Cookie": "a=b", "X-Csrf-Token": "y",
                        "Content-Type": "application/json", "User-Agent": "navigateur"},
            "cookies": {"a": "b"},
            "data": {"password": "secret"},
            "env": {"REMOTE_ADDR": "203.0.113.1"},
        },
        "user": {"ip_address": "203.0.113.1"},
    }

    scrubbed = monitoring.scrub(event, {})

    assert scrubbed["request"] == {"url": "https://api.terminator.fr/api/auth/login",
                                   "headers": {"Content-Type": "application/json", "User-Agent": "navigateur"}}
    assert "user" not in scrubbed
