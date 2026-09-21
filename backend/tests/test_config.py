import pytest

from app import DEV_SECRET, _load_config_from_env

ENV_VARS = ["APP_ENV", "SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "GENERATION_TIME_BUDGET_S"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_development_defaults():
    config = _load_config_from_env()

    assert config["APP_ENV"] == "development"
    assert config["JWT_SECRET_KEY"] == DEV_SECRET
    assert config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_jwt_secret_is_read_from_its_own_variable(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "flask-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "jwt-secret")

    assert _load_config_from_env()["JWT_SECRET_KEY"] == "jwt-secret"


def test_jwt_secret_falls_back_to_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "flask-secret")

    assert _load_config_from_env()["JWT_SECRET_KEY"] == "flask-secret"


def test_production_refuses_default_secrets_and_missing_database(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(RuntimeError, match="SECRET_KEY.*JWT_SECRET_KEY.*DATABASE_URL"):
        _load_config_from_env()


def test_production_with_complete_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "flask-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "jwt-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db/terminator")

    assert _load_config_from_env()["SQLALCHEMY_DATABASE_URI"] == "postgresql://u:p@db/terminator"


def test_register_quota_is_adjustable_outside_production(monkeypatch):
    """Les parcours end-to-end créent un compte par exécution : le quota doit pouvoir être desserré."""
    from app import _load_config_from_env

    monkeypatch.setenv('RATELIMIT_REGISTER', '1000 per hour')
    monkeypatch.setenv('APP_ENV', 'development')
    assert _load_config_from_env()['RATELIMIT_REGISTER'] == '1000 per hour'


def test_register_quota_stays_strict_in_production(monkeypatch):
    """En production, le quota protège de la création de comptes en masse : pas de contournement."""
    from app import _load_config_from_env

    monkeypatch.setenv('RATELIMIT_REGISTER', '1000 per hour')
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'une-cle-de-production-suffisamment-longue')
    monkeypatch.setenv('JWT_SECRET_KEY', 'une-autre-cle-de-production-suffisamment-longue')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/terminator')

    assert _load_config_from_env()['RATELIMIT_REGISTER'] == '5 per hour'


def test_generation_quota_is_adjustable_outside_production(monkeypatch):
    """L'auteur enchaîne les tentatives sur une demande difficile : le plafond ne doit pas le gêner."""
    from app import _load_config_from_env

    monkeypatch.setenv('RATELIMIT_GENERATE', '120 per minute')
    monkeypatch.setenv('APP_ENV', 'development')
    assert _load_config_from_env()['RATELIMIT_GENERATE'] == '120 per minute'


def test_generation_quota_stays_strict_in_production(monkeypatch):
    from app import _load_config_from_env

    monkeypatch.setenv('RATELIMIT_GENERATE', '120 per minute')
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'une-cle-de-production-suffisamment-longue')
    monkeypatch.setenv('JWT_SECRET_KEY', 'une-autre-cle-de-production-suffisamment-longue')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/terminator')

    assert _load_config_from_env()['RATELIMIT_GENERATE'] == '10 per minute'
