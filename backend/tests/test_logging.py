"""Journaux : texte en développement, JSON en production, avec l'identifiant de la requête."""

import importlib.util
import json
import logging
import re
import sys

import pytest

from app import create_app
from logging_setup import JsonFormatter, RequestContextFilter

TEST_SETTINGS = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "JWT_SECRET_KEY": "test-secret-key-long-enough-for-hs256-signing",
    "RATELIMIT_ENABLED": False,
}


def json_line(message, **extra):
    """La ligne que produirait le journal JSON pour ce message, émis pendant une requête."""
    record = logging.LogRecord("app", logging.WARNING, __file__, 1, message, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    RequestContextFilter().filter(record)
    return json.loads(JsonFormatter().format(record))


def test_a_json_line_says_which_request_it_belongs_to():
    app = create_app(TEST_SETTINGS)
    with app.test_request_context("/api/grids/generate?secret=1", method="POST"):
        app.preprocess_request()
        line = json_line("Génération interrompue")

    assert line["message"] == "Génération interrompue" and line["level"] == "WARNING"
    assert (line["method"], line["path"]) == ("POST", "/api/grids/generate")  # sans la query string
    assert re.fullmatch(r"[0-9a-f]{16}", line["request_id"])
    assert line["time"].endswith("+00:00")


def test_an_exception_is_kept_in_the_json_line():
    try:
        raise ValueError("panne")
    except ValueError:
        record = logging.LogRecord("app", logging.ERROR, __file__, 1, "Erreur", None, sys.exc_info())
    line = json.loads(JsonFormatter().format(record))

    assert "ValueError: panne" in line["exception"]


def test_the_request_id_comes_from_cloudflare_when_there_is_one(client):
    response = client.get("/api/status", headers={"CF-Ray": "8c1f2a3b4c5d6e7f-CDG"})

    assert response.headers["X-Request-ID"] == "8c1f2a3b4c5d6e7f-CDG"


@pytest.mark.parametrize("ray", [None, "pas un identifiant ; <script>", "x" * 100])
def test_otherwise_the_request_id_is_generated(client, ray):
    response = client.get("/api/status", headers={"CF-Ray": ray} if ray else {})

    assert re.fullmatch(r"[0-9a-f]{16}", response.headers["X-Request-ID"])


@pytest.mark.parametrize("app_env, expected", [("production", "json"), ("development", "text")])
def test_production_logs_in_json_by_default(monkeypatch, app_env, expected):
    from app import _load_config_from_env

    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("SECRET_KEY", "une-cle-de-production-suffisamment-longue")
    monkeypatch.setenv("JWT_SECRET_KEY", "une-autre-cle-de-production-suffisamment-longue")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/terminator")
    monkeypatch.delenv("LOG_FORMAT", raising=False)

    assert _load_config_from_env()["LOG_FORMAT"] == expected


def test_an_unknown_log_format_refuses_to_start(monkeypatch):
    from app import _load_config_from_env

    monkeypatch.setenv("LOG_FORMAT", "xml")
    with pytest.raises(RuntimeError, match="LOG_FORMAT"):
        _load_config_from_env()


def test_recreating_the_app_does_not_duplicate_log_lines():
    create_app(TEST_SETTINGS)
    create_app(TEST_SETTINGS)

    ours = [h for h in logging.getLogger().handlers if getattr(h, "_terminator", False)]
    assert len(ours) == 1


def test_gunicorn_access_lines_are_valid_json_without_query_string(monkeypatch):
    monkeypatch.setenv("LOG_FORMAT", "json")
    spec = importlib.util.spec_from_file_location("gunicorn_conf", "gunicorn.conf.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Les valeurs que gunicorn substitue (voir sa documentation « access_log_format »)
    sample = {"t": "[24/Sep/2026:10:00:00 +0000]", "{cf-connecting-ip}i": "203.0.113.1", "m": "GET",
              "U": "/api/status", "s": "200", "B": "165", "M": "12", "{x-request-id}o": "abc"}
    line = json.loads(module.access_log_format % sample)

    assert line["path"] == "/api/status" and line["status"] == 200 and line["ip"] == "203.0.113.1"
    assert "%(q)s" not in module.access_log_format  # jamais la query string
    assert module.logconfig_dict["loggers"]["gunicorn.error"]["handlers"] == ["erreurs"]
