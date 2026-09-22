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
