from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


def _normalize_async_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return f"postgresql+asyncpg://{url.removeprefix('postgres://')}"
    if url.startswith("postgresql://"):
        return f"postgresql+asyncpg://{url.removeprefix('postgresql://')}"
    return url


def _engine_kwargs(url: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"echo": False, "future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        if ":memory:" in url:
            from sqlalchemy.pool import StaticPool

            kwargs["poolclass"] = StaticPool
    return kwargs


database_url = _normalize_async_database_url(settings.database_url)
engine: AsyncEngine = create_async_engine(database_url, **_engine_kwargs(database_url))
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def configure_engine(url: str) -> None:
    global engine, SessionLocal
    normalized_url = _normalize_async_database_url(url)
    engine = create_async_engine(normalized_url, **_engine_kwargs(normalized_url))
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _ensure_internal_user_columns(sync_conn) -> None:
            table_name = "internal_users"
            cols = {col["name"] for col in inspect(sync_conn).get_columns(table_name)}
            if "job_title" not in cols:
                sync_conn.execute(text("ALTER TABLE internal_users ADD COLUMN job_title VARCHAR(120) DEFAULT ''"))
            if "department" not in cols:
                sync_conn.execute(text("ALTER TABLE internal_users ADD COLUMN department VARCHAR(120) DEFAULT ''"))
            if "phone" not in cols:
                sync_conn.execute(text("ALTER TABLE internal_users ADD COLUMN phone VARCHAR(40) DEFAULT ''"))
            if "timezone" not in cols:
                sync_conn.execute(text("ALTER TABLE internal_users ADD COLUMN timezone VARCHAR(64) DEFAULT 'UTC'"))
            if "bio" not in cols:
                sync_conn.execute(text("ALTER TABLE internal_users ADD COLUMN bio TEXT DEFAULT ''"))
            if "onboarding_complete" not in cols:
                sync_conn.execute(text("ALTER TABLE internal_users ADD COLUMN onboarding_complete BOOLEAN DEFAULT FALSE"))

        await conn.run_sync(_ensure_internal_user_columns)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
