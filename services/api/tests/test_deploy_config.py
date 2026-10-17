from app.config import Settings
from app.main import _assert_production_secrets


def test_cookie_secure_forced_in_production():
    s = Settings(environment="production", cookie_secure=False, app_base_url="http://localhost:3000")
    assert s.resolved_cookie_secure is True


def test_cookie_secure_on_https_app_url():
    s = Settings(environment="development", cookie_secure=False, app_base_url="https://orqelis.example")
    assert s.resolved_cookie_secure is True


def test_cookie_not_forced_on_local_http():
    s = Settings(environment="development", cookie_secure=False, app_base_url="http://localhost:3000")
    assert s.resolved_cookie_secure is False


def test_cors_includes_app_base_url():
    s = Settings(cors_origins="http://localhost:3000", app_base_url="https://orqelis.example", admin_base_url="https://admin.orqelis.example")
    assert "https://orqelis.example" in s.cors_origin_list
    assert "https://admin.orqelis.example" in s.cors_origin_list


def test_public_api_url_defaults_to_railway_in_production():
    s = Settings(environment="production", public_api_url="", next_public_api_url="")
    assert s.resolved_public_api_url == "https://orqelis-api-production.up.railway.app"


def test_public_api_url_keeps_local_default_and_honors_override():
    local = Settings(
        environment="development",
        api_host="127.0.0.1",
        api_port=8000,
        public_api_url="",
        next_public_api_url="",
    )
    configured = Settings(environment="production", public_api_url="https://api.example.test")
    assert local.resolved_public_api_url == "http://127.0.0.1:8000"
    assert configured.resolved_public_api_url == "https://api.example.test"


def test_production_secrets_reject_placeholders(monkeypatch):
    from app import main as main_mod

    monkeypatch.setattr(main_mod.settings, "environment", "production")
    monkeypatch.setattr(main_mod.settings, "jwt_secret", "CHANGE_ME")
    monkeypatch.setattr(main_mod.settings, "encryption_key", "long-enough-not-the-issue")
    try:
        _assert_production_secrets()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "JWT_SECRET" in str(exc)
