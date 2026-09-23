import uuid

from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy import func

from models import User

TEST_PASSWORD = "password123"


def unique_email() -> str:
    return f"{uuid.uuid4().hex}@exemple.fr"


def send(client, method, url, body=None, headers=None):
    kwargs = {"method": method.upper(), "headers": headers or {}}
    if body is not None:
        kwargs["json"] = body
    return client.open(url, **kwargs)


def forget_cookies(client) -> None:
    """Le client de test redevient anonyme : il oublie les cookies de session reçus."""
    client._cookies.clear()


def tokens_for(client, email: str) -> dict:
    """Jetons d'un compte existant, pour l'en-tête Authorization.

    L'API ne met plus de jeton dans ses réponses : ils partent en cookies httpOnly (ADR 0015). L'en-tête reste
    accepté, et la plupart des tests s'en servent : on fabrique donc les jetons comme l'API le ferait.
    """
    with client.application.app_context():
        user = User.query.filter(func.lower(User.email) == email.lower()).one()
        return {"access_token": create_access_token(identity=str(user.id)),
                "refresh_token": create_refresh_token(identity=str(user.id))}


def register(client, email=None, password=TEST_PASSWORD):
    """Inscrit un utilisateur et renvoie (email, jetons) ; le client reste anonyme (pas de cookie)."""
    email = email or unique_email()
    response = send(client, "post", "/api/auth/register", {"email": email, "password": password})
    assert response.status_code == 201, response.get_json()
    forget_cookies(client)
    return email, tokens_for(client, email)


def auth_headers(client, email=None, password=TEST_PASSWORD) -> dict:
    _, tokens = register(client, email, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def default_dictionary_id(client, headers) -> int:
    return client.get("/api/dictionaries", headers=headers).get_json()[0]["id"]
