import json

def test_register(client):
    """
    Teste la création d'un nouvel utilisateur.
    'client' est fourni par notre fichier conftest.py.
    """
    # On envoie une requête POST à la route d'inscription
    response = client.post(
        '/api/auth/register',
        data=json.dumps({'email': 'testuser@example.com', 'password': 'password123'}),
        content_type='application/json'
    )
    
    # On vérifie que la réponse est un succès (201 Created)
    assert response.status_code == 201
    
    # On lit le JSON et on vérifie la valeur du message
    data = response.get_json()
    assert data['message'] == "Utilisateur testuser@example.com créé avec succès."

def test_login(client):
    """
    Teste la connexion d'un utilisateur existant.
    """
    # On doit d'abord créer l'utilisateur pour pouvoir le connecter
    client.post(
        '/api/auth/register',
        data=json.dumps({'email': 'loginuser@example.com', 'password': 'password123'}),
        content_type='application/json'
    )

    # On tente de se connecter avec les bons identifiants
    response = client.post(
        '/api/auth/login',
        data=json.dumps({'email': 'loginuser@example.com', 'password': 'password123'}),
        content_type='application/json'
    )
    
    # On vérifie que la réponse est un succès (200 OK)
    assert response.status_code == 200
    
    # On vérifie que la réponse contient bien nos tokens
    data = response.get_json()
    assert 'access_token' in data
    assert 'refresh_token' in data

def test_login_invalid_password(client):
    """
    Teste la connexion avec un mot de passe incorrect.
    """
    # On crée l'utilisateur
    client.post(
        '/api/auth/register',
        data=json.dumps({'email': 'invalidpass@example.com', 'password': 'password123'}),
        content_type='application/json'
    )

    # On tente de se connecter avec un mauvais mot de passe
    response = client.post(
        '/api/auth/login',
        data=json.dumps({'email': 'invalidpass@example.com', 'password': 'wrongpassword'}),
        content_type='application/json'
    )

    # On vérifie que le serveur renvoie bien une erreur 401 Unauthorized
    assert response.status_code == 401
    
    # On vérifie le message d'erreur dans le JSON
    data = response.get_json()
    assert data['error'] == "Identifiants invalides."

