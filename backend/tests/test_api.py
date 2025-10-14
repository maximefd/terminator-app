import json

def get_auth_headers(client, email='test@example.com', password='password123'):
    """Fonction utilitaire pour s'inscrire, se connecter et retourner les en-têtes d'authentification."""
    client.post(
        '/api/auth/register',
        data=json.dumps({'email': email, 'password': password}),
        content_type='application/json'
    )
    response = client.post(
        '/api/auth/login',
        data=json.dumps({'email': email, 'password': password}),
        content_type='application/json'
    )
    token = response.get_json()['access_token']
    return {
        'Authorization': f'Bearer {token}'
    }

def test_get_dictionaries_new_user(client):
    """Teste si un nouvel utilisateur obtient bien un dictionnaire par défaut."""
    headers = get_auth_headers(client, email='newuser1@example.com')
    
    response = client.get('/api/dictionaries', headers=headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['name'] == 'Dictionnaire par défaut'

def test_create_dictionary(client):
    """Teste la création d'un nouveau dictionnaire."""
    headers = get_auth_headers(client, email='newuser2@example.com')

    # CORRECTION : On fait un premier appel pour déclencher la création du dictionnaire par défaut.
    response = client.get('/api/dictionaries', headers=headers)
    assert response.status_code == 200
    assert len(response.get_json()) == 1

    # Maintenant, on crée le nouveau dictionnaire
    response = client.post(
        '/api/dictionaries',
        headers=headers,
        data=json.dumps({'name': 'Mon Dico Test'}),
        content_type='application/json'
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'Mon Dico Test'

    # Vérifie que la liste contient maintenant bien deux dictionnaires
    response = client.get('/api/dictionaries', headers=headers)
    data = response.get_json()
    assert len(data) == 2

def test_add_word_to_dictionary(client):
    """Teste l'ajout d'un mot à un dictionnaire."""
    headers = get_auth_headers(client, email='newuser3@example.com')
    
    # CORRECTION : On fait un premier appel pour obtenir les dictionnaires et leur ID.
    response = client.get('/api/dictionaries', headers=headers)
    assert response.status_code == 200
    dictionaries = response.get_json()
    dict_id = dictionaries[0]['id'] # On récupère dynamiquement l'ID du dictionnaire par défaut

    response = client.post(
        f'/api/dictionaries/{dict_id}/words',
        headers=headers,
        data=json.dumps({'mot': 'TEST', 'definition': 'Un mot de test'}),
        content_type='application/json'
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data['mot'] == 'TEST'

    # On vérifie que le mot est bien dans la liste
    response = client.get(f'/api/dictionaries/{dict_id}/words', headers=headers)
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['mot'] == 'TEST'

