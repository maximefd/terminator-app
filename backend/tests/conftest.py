import pytest
from app import create_app
from models import db

@pytest.fixture(scope='module')
def test_app():
    """Crée une instance de l'application Flask pour les tests."""
    # On configure l'application pour utiliser une base de données de test en mémoire (SQLite)
    # C'est beaucoup plus rapide et ça n'affecte pas notre BDD de développement.
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret-key' # On utilise une clé de test
    })

    with app.app_context():
        db.create_all()
        yield app  # "fournit" l'application au test
        db.drop_all() # Nettoie la base de données après les tests

@pytest.fixture()
def client(test_app):
    """Crée un client de test pour envoyer des requêtes à l'application."""
    return test_app.test_client()

@pytest.fixture()
def runner(test_app):
    """Crée un 'runner' pour exécuter des commandes CLI si besoin."""
    return test_app.test_cli_runner()
