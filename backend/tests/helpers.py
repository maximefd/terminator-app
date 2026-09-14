import uuid

TEST_PASSWORD = "password123"


def unique_email() -> str:
    return f"{uuid.uuid4().hex}@exemple.fr"


def send(client, method, url, body=None, headers=None):
    kwargs = {"method": method.upper(), "headers": headers or {}}
    if body is not None:
        kwargs["json"] = body
    return client.open(url, **kwargs)


def register(client, email=None, password=TEST_PASSWORD):
    """Inscrit un utilisateur et renvoie (email, tokens)."""
    email = email or unique_email()
    response = send(client, "post", "/api/auth/register", {"email": email, "password": password})
    assert response.status_code == 201, response.get_json()
    return email, response.get_json()


def auth_headers(client, email=None, password=TEST_PASSWORD) -> dict:
    _, tokens = register(client, email, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def default_dictionary_id(client, headers) -> int:
    return client.get("/api/dictionaries", headers=headers).get_json()[0]["id"]
