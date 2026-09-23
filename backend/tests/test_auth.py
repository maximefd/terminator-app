import json


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