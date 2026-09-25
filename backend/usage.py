"""Mesure d'usage côté serveur, sans cookie ni script tiers ([ADR 0016](../docs/adr/0016-mesure-d-usage-sans-cookie.md)).

Une requête écrit au plus un événement, à la fin (`after_request`) :
- une génération ou une recherche, quelle qu'en soit l'issue — rate limiting et requête invalide compris ;
- un fait de compte ou une grille conservée, que la vue décrit par `describe()` ;
- sinon, toute erreur (4xx, 5xx) sur une route connue : le compteur d'erreurs par route et par statut.

Le visiteur est une empreinte du jour : un hachage de l'adresse IP et du navigateur avec un sel tiré au
hasard chaque jour, gardé en base le temps de la journée puis détruit. Elle compte les visiteurs d'un jour
sans permettre de suivre personne d'un jour à l'autre. **L'adresse IP n'est jamais enregistrée.**

Mesurer ne doit jamais casser une requête : toute erreur ici est journalisée, puis oubliée.
"""

import hashlib
import logging
import secrets
import time
from datetime import date, datetime, timedelta, timezone

from flask import Flask, current_app, g, request
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import UsageEvent, VisitorSalt
from security import client_ip

# Durées de conservation (ADR 0016, page de confidentialité, docs/RGPD.md)
WORDS_RETENTION = timedelta(days=90)
EVENTS_RETENTION = timedelta(days=396)  # 13 mois

# Routes mesurées à chaque appel, quelle qu'en soit l'issue
ALWAYS_MEASURED = {"main.generate_grid": "generation", "main.search_words": "search"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def describe(kind: str, outcome: str | None = None, *, user=None, data: dict | None = None,
             words: dict | None = None) -> None:
    """Décrit l'événement de la requête en cours ; il est écrit à la fin, si la réponse est un succès
    ou si la route est toujours mesurée (génération, recherche)."""
    g.usage_event = {"kind": kind, "outcome": outcome, "user_id": user.id if user else None,
                     "data": data or {}, "words": words}


def add_details(**data) -> None:
    """Complète l'événement de la requête (format, mots imposés…), qu'il soit décrit ou déduit."""
    g.setdefault("usage_details", {}).update(data)


def _daily_salt(today: date) -> str:
    cached = current_app.extensions.get("usage_salt")
    if cached and cached[0] == today:
        return cached[1]
    row = db.session.get(VisitorSalt, today)
    if row is None:
        try:
            db.session.add(VisitorSalt(day=today, salt=secrets.token_hex(32)))
            _purge(today)
            db.session.commit()
        except IntegrityError:
            # Un autre worker l'a tiré au même instant : on prend le sien
            db.session.rollback()
        row = db.session.get(VisitorSalt, today)
    current_app.extensions["usage_salt"] = (today, row.salt)
    return row.salt


def _purge(today: date) -> None:
    """Ménage quotidien, fait par la première requête mesurée du jour : pas de tâche planifiée à oublier."""
    now = datetime.combine(today, datetime.min.time())
    # Le sel d'hier disparaît : plus personne ne peut relier une empreinte d'hier à une adresse
    VisitorSalt.query.filter(VisitorSalt.day < today).delete()
    (UsageEvent.query
     .filter(UsageEvent.created_at < now - WORDS_RETENTION, UsageEvent.words.isnot(None))
     .update({UsageEvent.words: None}, synchronize_session=False))
    UsageEvent.query.filter(UsageEvent.created_at < now - EVENTS_RETENTION).delete()


def purge() -> None:
    """Le même ménage, à la demande (`flask usage purge`)."""
    _purge(_utcnow().date())
    db.session.commit()


def visitor_fingerprint(today: date) -> str:
    salt = _daily_salt(today)
    source = f"{salt}\n{client_ip()}\n{request.headers.get('User-Agent', '')}"
    return hashlib.sha256(source.encode()).hexdigest()[:32]


def _country() -> str | None:
    # Posé par Cloudflare ; « XX » : inconnu, « T1 » : Tor
    country = request.headers.get("CF-IPCountry", "").strip().upper()[:2]
    return country if country and country != "XX" else None


def _reason(response) -> str | None:
    if not response.is_json:
        return None
    body = response.get_json(silent=True)
    return body.get("reason") if isinstance(body, dict) else None


def _deduced_outcome(kind: str, response) -> str:
    """L'issue d'une génération ou d'une recherche que la vue n'a pas décrite : erreur ou refus."""
    reason = _reason(response)
    if response.status_code == 200:
        return "grid" if kind == "generation" else "results"
    if reason:
        return reason
    if response.status_code == 429:
        return "rate_limited"  # Flask-Limiter : les refus « occupé » portent leur raison
    return {400: "invalid_request", 404: "not_found", 503: "unavailable"}.get(response.status_code,
                                                                             f"http_{response.status_code}")


def _event_for(response) -> dict | None:
    endpoint = request.endpoint
    described = g.get("usage_event")
    if endpoint in ALWAYS_MEASURED:
        kind = ALWAYS_MEASURED[endpoint]
        event = described or {"kind": kind, "outcome": None, "user_id": None, "data": {}, "words": None}
        event["outcome"] = event["outcome"] or _deduced_outcome(kind, response)
        return event
    if described and response.status_code < 400:
        return described
    if response.status_code >= 400 and request.url_rule is not None and request.method != "OPTIONS":
        return {"kind": "error", "outcome": None, "user_id": None, "data": {}, "words": None}
    return None


def record(response):
    try:
        _record(response)
    finally:
        # Rien ne passe à la requête suivante, même si le contexte d'application lui survit (tests, CLI)
        for key in ("usage_event", "usage_details", "usage_started"):
            g.pop(key, None)


def _record(response):
    event = _event_for(response)
    if event is None:
        return
    started = g.get("usage_started")
    now = _utcnow()
    try:
        if response.status_code >= 500:
            db.session.rollback()  # la vue a pu laisser la session dans un état d'échec
        data = {**event["data"], **g.get("usage_details", {})}
        db.session.add(UsageEvent(
            created_at=now,
            kind=event["kind"],
            outcome=event["outcome"],
            status=response.status_code,
            route=request.url_rule.rule if request.url_rule else None,
            site=current_app.config["SITE"],
            lang=current_app.config["SITE_LANG"],
            country=_country(),
            visitor=visitor_fingerprint(now.date()),
            user_id=event["user_id"],
            duration_ms=round((time.perf_counter() - started[0]) * 1000) if started else None,
            cpu_ms=round((time.process_time() - started[1]) * 1000) if started else None,
            data=data,
            words=event["words"],
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        logging.exception("Événement d'usage non enregistré (%s %s)", request.method, request.path)


def init_usage(app: Flask) -> None:
    @app.before_request
    def start_measure():
        # Durée et temps CPU de la requête : un worker synchrone ne traite qu'elle pendant ce temps
        g.usage_started = (time.perf_counter(), time.process_time())

    @app.after_request
    def record_usage(response):
        if app.config.get("USAGE_ENABLED", True):
            record(response)
        return response
