import pytest

from app import DEV_SECRET, _load_config_from_env

ENV_VARS = ["APP_ENV", "SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "GENERATION_TIME_BUDGET_S", "SITE_NAME",
            "SITE", "SITE_LANG", "LEXICON_LOAD"]


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
    monkeypatch.setenv("SECRET_KEY", "cle-flask-de-production-longue-de-32-octets-au-moins")
    monkeypatch.setenv("JWT_SECRET_KEY", "cle-jwt-de-production-longue-de-32-octets-au-moins")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db/terminator")

    assert _load_config_from_env()["SQLALCHEMY_DATABASE_URI"] == "postgresql://u:p@db/terminator"


@pytest.mark.parametrize("secret_key, jwt_secret_key, refused", [
    ("court", "cle-jwt-de-production-longue-de-32-octets-au-moins", "SECRET_KEY"),
    ("cle-flask-de-production-longue-de-32-octets-au-moins", "court", "JWT_SECRET_KEY"),
    ("la-meme-cle-pour-les-deux-usages-32-octets", "la-meme-cle-pour-les-deux-usages-32-octets",
     "identique à SECRET_KEY"),
])
def test_production_refuses_short_or_shared_keys(monkeypatch, secret_key, jwt_secret_key, refused):
    """Audit ASVS : ces clés signent les sessions et les liens envoyés par e-mail (RFC 7518 : 32 octets au moins)."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", secret_key)
    monkeypatch.setenv("JWT_SECRET_KEY", jwt_secret_key)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db/terminator")

    with pytest.raises(RuntimeError, match=refused):
        _load_config_from_env()


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


def test_lexicon_hot_reload_is_adjustable_outside_production(monkeypatch):
    from app import _load_config_from_env

    monkeypatch.setenv('LEXICON_RELOAD_INTERVAL_S', '5')
    monkeypatch.setenv('APP_ENV', 'development')
    assert _load_config_from_env()['LEXICON_RELOAD_INTERVAL_S'] == 5


def test_lexicon_is_never_hot_reloaded_in_production(monkeypatch):
    """ADR 0013 : le lexique de production est livré avec l'application ; sous gunicorn, le recharger
    à chaud ne profiterait qu'au processus maître."""
    from app import _load_config_from_env

    monkeypatch.setenv('LEXICON_RELOAD_INTERVAL_S', '30')
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'une-cle-de-production-suffisamment-longue')
    monkeypatch.setenv('JWT_SECRET_KEY', 'une-autre-cle-de-production-suffisamment-longue')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/terminator')

    assert _load_config_from_env()['LEXICON_RELOAD_INTERVAL_S'] == 0


def test_the_visitor_header_is_read_from_the_environment(monkeypatch):
    from app import _load_config_from_env

    monkeypatch.setenv('CLIENT_IP_HEADER', ' CF-Connecting-IP ')
    assert _load_config_from_env()['CLIENT_IP_HEADER'] == 'CF-Connecting-IP'


def test_site_name_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("SITE_NAME", "Die Pfeilwerkstatt")

    assert _load_config_from_env()["SITE_NAME"] == "Die Pfeilwerkstatt"


def test_site_name_defaults_to_the_french_site():
    assert _load_config_from_env()["SITE_NAME"] == "Le Fléchoir"


def test_a_command_can_skip_the_lexicon(monkeypatch):
    """flask stats n'en a pas besoin : sur le serveur, le charger coûterait des centaines de Mo."""
    assert _load_config_from_env()["LEXICON_LOAD"] is True
    monkeypatch.setenv("LEXICON_LOAD", "0")
    assert _load_config_from_env()["LEXICON_LOAD"] is False


def test_the_site_and_its_language_come_from_the_environment(monkeypatch):
    assert (_load_config_from_env()["SITE"], _load_config_from_env()["SITE_LANG"]) == ("fr", "fr")
    monkeypatch.setenv("SITE", "de")
    monkeypatch.setenv("SITE_LANG", "de")
    assert (_load_config_from_env()["SITE"], _load_config_from_env()["SITE_LANG"]) == ("de", "de")
