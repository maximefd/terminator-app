import pytest
from app import create_app
from models import db
from trie_engine import DictionnaireTrie

from tests.paths import FIXTURE_WORDS_FILE

@pytest.fixture(scope='module')
def test_app():
    """Crée une instance de l'application Flask pour les tests."""
    # On configure l'application pour utiliser une base de données de test en mémoire (SQLite)
    # C'est beaucoup plus rapide et ça n'affecte pas notre BDD de développement.
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'JWT_SECRET_KEY': 'test-secret-key-long-enough-for-hs256-signing' # Clé de test (>= 32 octets)
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

@pytest.fixture(scope='session')
def small_words():
    """~11 600 mots de 2 à 5 lettres extraits du DELA (évite de charger le fichier complet)."""
    with open(FIXTURE_WORDS_FILE, encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

@pytest.fixture(scope='session')
def small_trie(small_words):
    trie = DictionnaireTrie()
    for word in small_words:
        trie.insert(word)
    return trie
