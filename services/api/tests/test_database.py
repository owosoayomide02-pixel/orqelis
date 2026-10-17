from app.database import _normalize_async_database_url


def test_render_postgres_url_is_converted_to_asyncpg():
    assert (
        _normalize_async_database_url("postgres://user:pass@host/db")
        == "postgresql+asyncpg://user:pass@host/db"
    )


def test_postgresql_url_is_converted_to_asyncpg():
    assert (
        _normalize_async_database_url("postgresql://user:pass@host/db")
        == "postgresql+asyncpg://user:pass@host/db"
    )


def test_existing_asyncpg_url_is_unchanged():
    url = "postgresql+asyncpg://user:pass@host/db"
    assert _normalize_async_database_url(url) == url


def test_sqlite_url_is_unchanged():
    url = "sqlite+aiosqlite:///./orqelis.db"
    assert _normalize_async_database_url(url) == url
