"""E-mails du compte (ADR 0014) : confirmer son adresse, changer un mot de passe oublié."""

import re

import pytest

import account_links
from mailer import send_email
from tests.helpers import TEST_PASSWORD, register, send, unique_email

FRONTEND = "https://terminator.example"


@pytest.fixture
def outbox(test_app, monkeypatch):
    """Les e-mails partis pendant le test, dans l'ordre."""
    monkeypatch.setitem(test_app.config, "MAIL_BACKEND", "memory")
    monkeypatch.setitem(test_app.config, "FRONTEND_URL", FRONTEND)
    sent = test_app.extensions["sent_emails"] = []
    return sent


def link_token(message, path):
    """Le jeton du lien de l'e-mail, après avoir vérifié que le lien mène à la bonne page du frontend."""
    match = re.search(rf"{re.escape(FRONTEND + path)}\?token=(\S+)", message.get_content())
    assert match, message.get_content()
    return match.group(1)


def account(client, tokens):
    return client.get("/api/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}).get_json()


def login_status(client, email, password):
    return send(client, "post", "/api/auth/login", {"email": email, "password": password}).status_code


# --- Confirmation de l'adresse ---

def test_registering_sends_a_confirmation_link(client, outbox):
    email, tokens = register(client)

    assert [m["To"] for m in outbox] == [email]
    assert "/verify-email?token=" in outbox[0].get_content()
    assert account(client, tokens)["email_verified"] is False


def test_the_confirmation_link_confirms_the_address(client, outbox):
    _, tokens = register(client)
    token = link_token(outbox[0], "/verify-email")

    response = send(client, "post", "/api/auth/email/verify", {"token": token})

    assert response.status_code == 200
    assert account(client, tokens)["email_verified"] is True


@pytest.mark.parametrize("token", ["pas-un-jeton", ""])
def test_a_forged_or_empty_confirmation_link_is_refused(client, token):
    response = send(client, "post", "/api/auth/email/verify", {"token": token})

    assert response.status_code == 400


def test_a_tampered_confirmation_link_is_refused(client, outbox):
    register(client)
    token = link_token(outbox[0], "/verify-email")

    response = send(client, "post", "/api/auth/email/verify", {"token": token[:-3] + "abc"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Ce lien n'est plus valable. Demandez-en un nouveau."


def test_the_confirmation_link_can_be_asked_again_from_the_account(client, outbox):
    _, tokens = register(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    again = send(client, "post", "/api/auth/email/resend", None, headers)
    assert again.status_code == 200 and len(outbox) == 2

    send(client, "post", "/api/auth/email/verify", {"token": link_token(outbox[1], "/verify-email")})
    confirmed = send(client, "post", "/api/auth/email/resend", None, headers)

    assert confirmed.get_json() == {"message": "Votre adresse est déjà confirmée."}
    assert len(outbox) == 2  # rien de plus n'est parti


def test_asking_the_confirmation_link_again_requires_an_account(client):
    assert send(client, "post", "/api/auth/email/resend").status_code == 401


# --- Mot de passe oublié ---

def test_forgot_password_answers_the_same_whether_the_account_exists_or_not(client, outbox):
    email, _ = register(client)
    outbox.clear()

    known = send(client, "post", "/api/auth/password/forgot", {"email": email})
    unknown = send(client, "post", "/api/auth/password/forgot", {"email": unique_email()})

    assert known.status_code == unknown.status_code == 200
    assert known.get_json() == unknown.get_json()
    assert [m["To"] for m in outbox] == [email]  # seul le compte existant reçoit un lien


def test_the_reset_link_changes_the_password_once(client, outbox):
    email, tokens = register(client)
    send(client, "post", "/api/auth/password/forgot", {"email": email.upper()})
    token = link_token(outbox[-1], "/reset-password")

    first = send(client, "post", "/api/auth/password/reset", {"token": token, "password": "NouveauSecret42"})
    second = send(client, "post", "/api/auth/password/reset", {"token": token, "password": "EncoreUnAutre42"})

    assert first.status_code == 200
    assert second.status_code == 400  # le mot de passe a changé : le lien ne vaut plus
    assert login_status(client, email, "NouveauSecret42") == 200
    assert login_status(client, email, TEST_PASSWORD) == 401
    # Le lien est arrivé par e-mail : l'adresse est prouvée
    assert account(client, tokens)["email_verified"] is True


def test_an_expired_reset_link_is_refused(client, outbox, monkeypatch):
    email, _ = register(client)
    send(client, "post", "/api/auth/password/forgot", {"email": email})
    monkeypatch.setattr(account_links, "RESET_MAX_AGE_S", -1)

    response = send(client, "post", "/api/auth/password/reset",
                    {"token": link_token(outbox[-1], "/reset-password"), "password": "NouveauSecret42"})

    assert response.status_code == 400
    assert login_status(client, email, TEST_PASSWORD) == 200


def test_a_confirmation_link_cannot_change_the_password(client, outbox):
    """Deux usages, deux signatures : le lien reçu à l'inscription ne donne pas la main sur le mot de passe."""
    email, _ = register(client)

    response = send(client, "post", "/api/auth/password/reset",
                    {"token": link_token(outbox[0], "/verify-email"), "password": "NouveauSecret42"})

    assert response.status_code == 400
    assert login_status(client, email, TEST_PASSWORD) == 200


def test_the_new_password_follows_the_registration_rules(client, outbox):
    email, _ = register(client)
    send(client, "post", "/api/auth/password/forgot", {"email": email})

    response = send(client, "post", "/api/auth/password/reset",
                    {"token": link_token(outbox[-1], "/reset-password"), "password": "court"})

    assert response.status_code == 400


# --- Envoi ---

def test_a_failed_sending_does_not_reveal_anything_nor_block_registration(client, test_app, monkeypatch):
    monkeypatch.setitem(test_app.config, "MAIL_BACKEND", "smtp")
    monkeypatch.setitem(test_app.config, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setitem(test_app.config, "SMTP_PORT", 9)  # rien n'écoute : connexion refusée
    email, tokens = register(client)

    forgot = send(client, "post", "/api/auth/password/forgot", {"email": email})
    resend = send(client, "post", "/api/auth/email/resend", None,
                  {"Authorization": f"Bearer {tokens['access_token']}"})

    assert forgot.status_code == 200  # même réponse que d'habitude
    assert resend.status_code == 503  # ici l'auteur attend un e-mail : il doit savoir qu'il ne viendra pas


class FakeSMTP:
    """Tient lieu de smtplib.SMTP : note ce qu'on lui demande."""

    calls: list = []

    def __init__(self, host, port, timeout):
        FakeSMTP.calls.append(("connect", host, port))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        FakeSMTP.calls.append(("starttls",))

    def login(self, user, password):
        FakeSMTP.calls.append(("login", user))

    def send_message(self, message):
        FakeSMTP.calls.append(("send", message["To"], message["Subject"]))


def test_smtp_sending_uses_tls_and_credentials_when_configured(test_app, monkeypatch):
    monkeypatch.setattr("mailer.smtplib.SMTP", FakeSMTP)
    FakeSMTP.calls = []
    for key, value in {"MAIL_BACKEND": "smtp", "SMTP_HOST": "smtp-relay.example", "SMTP_PORT": 587,
                       "SMTP_STARTTLS": True, "SMTP_USER": "relais", "SMTP_PASSWORD": "secret"}.items():
        monkeypatch.setitem(test_app.config, key, value)

    with test_app.app_context():
        assert send_email("auteur@example.com", "Sujet", "Corps")

    assert FakeSMTP.calls == [("connect", "smtp-relay.example", 587), ("starttls",), ("login", "relais"),
                              ("send", "auteur@example.com", "Sujet")]


# --- Configuration ---

def test_an_unknown_mail_backend_refuses_to_start(monkeypatch):
    from app import _load_config_from_env

    monkeypatch.setenv("MAIL_BACKEND", "pigeon")
    with pytest.raises(RuntimeError, match="MAIL_BACKEND"):
        _load_config_from_env()


def test_email_links_point_to_the_frontend_by_default(monkeypatch):
    from app import _load_config_from_env

    monkeypatch.setenv("CORS_ORIGINS", "https://terminator.fr,https://www.terminator.fr")
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    assert _load_config_from_env()["FRONTEND_URL"] == "https://terminator.fr"
