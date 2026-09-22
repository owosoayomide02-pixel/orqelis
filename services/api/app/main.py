from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import InternalUser, new_id
from app.routers import (
    admin,
    agent,
    ai,
    alerts,
    approvals,
    auth,
    demo,
    devices,
    events,
    incidents,
    organizations,
    policies,
    reports,
    subscription,
    vulnerabilities,
)
from app.seed import seed_reference_data
from orqelis_security.passwords import hash_password
from orqelis_security.rate_limit import RateLimiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("orqelis.api")
api_limiter = RateLimiter(settings.rate_limit_per_minute)


def _assert_production_secrets() -> None:
    if settings.is_development:
        return
    weak = {"", "CHANGE_ME", "change-me-to-a-long-random-string", "dev-only-change-me", "dev-only-change-me-please"}
    if (settings.jwt_secret or "").strip() in weak or len(settings.jwt_secret) < 24:
        raise RuntimeError("Set a long JWT_SECRET before running in production.")
    if (settings.encryption_key or "").strip() in weak:
        raise RuntimeError("Set ENCRYPTION_KEY before running in production.")


async def bootstrap() -> None:
    _assert_production_secrets()
    if settings.auto_migrate:
        await init_db()
    async with SessionLocal() as db:
        await seed_reference_data(db)
        if settings.founder_email and settings.founder_password:
            existing = (
                await db.execute(select(InternalUser).where(InternalUser.email == settings.founder_email.lower()))
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    InternalUser(
                        id=new_id(),
                        email=settings.founder_email.lower(),
                        password_hash=hash_password(settings.founder_password),
                        display_name="Founder",
                        role="FOUNDER",
                    )
                )
                await db.commit()
                log.info("Bootstrapped founder account %s", settings.founder_email)
            else:
                await db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await bootstrap()
    log.info(
        "AI gateway provider=%s model=%s configured=%s",
        settings.resolved_ai_provider,
        settings.ai_model or "default",
        bool(settings.resolved_ai_key),
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Orqelis API",
        version="0.1.0",
        description="Security for the Intelligent World.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Organization-Id", "X-Orqelis-Device-Token"],
    )

    @app.middleware("http")
    async def security_and_limits(request: Request, call_next):
        if request.headers.get("content-length"):
            try:
                if int(request.headers["content-length"]) > 1_000_000:
                    return JSONResponse({"detail": "Request too large"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid content length"}, status_code=400)
        key = request.client.host if request.client else "unknown"
        if request.url.path.startswith("/api/") and not api_limiter.allow(key):
            return JSONResponse({"detail": "Too many requests"}, status_code=429)
        try:
            response = await call_next(request)
        except HTTPException:
            raise
        except Exception:
            log.exception("Unhandled error")
            return JSONResponse({"detail": "Internal error"}, status_code=500)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-Orqelis-Service"] = "api"
        return response

    @app.get("/health")
    async def health() -> dict:
        return {"ok": True, "service": "orqelis-api", "time": datetime.now(UTC).isoformat(), "version": "0.1.0"}

    app.include_router(auth.router)
    app.include_router(organizations.router)
    app.include_router(devices.router)
    app.include_router(agent.router)
    app.include_router(events.router)
    app.include_router(alerts.router)
    app.include_router(incidents.router)
    app.include_router(vulnerabilities.router)
    app.include_router(ai.router)
    app.include_router(reports.router)
    app.include_router(approvals.router)
    app.include_router(policies.router)
    app.include_router(subscription.router)
    app.include_router(demo.router)
    app.include_router(admin.router)
    return app


app = create_app()
