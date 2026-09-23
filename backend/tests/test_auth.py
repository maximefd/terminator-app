import json

import pytest


def assert_session_in_cookies_only(response):
    cookies = " ".join(response.headers.getlist("Set-Cookie"))
    assert "access_token_cookie=" in cookies and "refresh_token_cookie=" in cookies
    data = response.get_json()
    assert "access_token" not in data and "refresh_token" not in data

def test_register(client):
    """
    Teste la création d'un nouvel utilisateur : la session part en cookies, jamais dans le corps (ADR 0015).
    """
    response = client.post(
        '/api/auth/register',
        data=json.dumps({'email': 'testuser@example.com', 'password': 'password123'}),
        content_type='application/json'
    )
    
    assert response.status_code == 201
    
    assert_session_in_cookies_only(response)

def test_login(client):
    """
    Teste la connexion d'un utilisateur existant.
    """
    # On crée d'abord l'utilisateur
    client.post(
        '/api/auth/register',
        data=json.dumps({'email': 'loginuser@example.com', 'password': 'password123'}),
        content_type='application/json'
    )

    # On tente de se connecter
    response = client.post(
        '/api/auth/login',
        data=json.dumps({'email': 'loginuser@example.com', 'password': 'password123'}),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    assert_session_in_cookies_only(response)

def test_login_invalid_password(client):
    """
    Teste la connexion avec un mot de passe incorrect.
    """
    client.post(
        '/api/auth/register',
        data=json.dumps({'email': 'invalidpass@example.com', 'password': 'password123'}),
        content_type='application/json'
    )

    response = client.post(
        '/api/auth/login',
        data=json.dumps({'email': 'invalidpass@example.com', 'password': 'wrongpassword'}),
        content_type='application/json'
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data['error'] == "Identifiants invalides."


@pytest.mark.parametrize("password", ["a" * 100, "é" * 64, "x" * 128])
def test_passwords_longer_than_bcrypt_limit_work(client, password):
    """Audit ASVS : bcrypt 5 refuse plus de 72 octets. 100 lettres, ou 64 lettres accentuées (128 octets),
    faisaient échouer l'inscription en erreur 500, alors que l'API annonce 128 caractères."""
    from tests.helpers import send, unique_email

    email = unique_email()
    assert send(client, "post", "/api/auth/register", {"email": email, "password": password}).status_code == 201
    assert send(client, "post", "/api/auth/login", {"email": email, "password": password}).status_code == 200
    # Chaque caractère compte, même au-delà de 72 octets
    other = password[:-1] + ("b" if password[-1] != "b" else "c")
    assert send(client, "post", "/api/auth/login", {"email": email, "password": other}).status_code == 401


def test_existing_short_password_hashes_still_match():
    """Les mots de passe de 72 octets au plus sont hachés comme avant : les comptes existants restent valides."""
    from auth import password_matches
    from extensions import bcrypt

    legacy = bcrypt.generate_password_hash("motdepasse-historique").decode("utf-8")
    assert password_matches(legacy, "motdepasse-historique")
