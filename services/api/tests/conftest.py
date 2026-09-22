from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-please-change"
os.environ["ENVIRONMENT"] = "development"
os.environ["AUTO_MIGRATE"] = "true"
os.environ["FOUNDER_EMAIL"] = "founder@example.com"
os.environ["FOUNDER_PASSWORD"] = "founderpass1"
os.environ["EMAIL_BACKEND"] = "log"
os.environ["AI_PROVIDER"] = "heuristic"
os.environ["AI_API_KEY"] = ""
os.environ["AI_BASE_URL"] = ""
os.environ["AI_MODEL"] = ""
os.environ["OPENAI_API_KEY"] = ""

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.seed import seed_reference_data


@pytest.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await seed_reference_data(db)
        from app.models import InternalUser, new_id
        from orqelis_security.passwords import hash_password
        from sqlalchemy import select

        existing = (
            await db.execute(select(InternalUser).where(InternalUser.email == "founder@example.com"))
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                InternalUser(
                    id=new_id(),
                    email="founder@example.com",
                    password_hash=hash_password("founderpass1"),
                    display_name="Founder",
                    role="FOUNDER",
                )
            )
            await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac


async def register(client: AsyncClient, email: str, org: str = "Org") -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correcthorse",
            "display_name": email.split("@")[0],
            "organization_name": org,
            "accept_terms": True,
            "acknowledge_privacy": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()
