import json

def test_register(client):
    """
    Teste la création d'un nouvel utilisateur et vérifie qu'il reçoit bien des tokens.
    """
    response = client.post(
        '/api/auth/register',
        data=json.dumps({'email': 'testuser@example.com', 'password': 'password123'}),
        content_type='application/json'
    )
    
    assert response.status_code == 201
    
    # LA CORRECTION EST ICI : On vérifie que la réponse contient bien les tokens
    data = response.get_json()
    assert 'access_token' in data
    assert 'refresh_token' in data

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
    
    data = response.get_json()
    assert 'access_token' in data
    assert 'refresh_token' in data

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