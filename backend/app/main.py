"""FastAPI application entry point.

Run from the backend/ folder:  uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.hardening import SecurityMiddleware, check_production, install_log_filter
from app.routers import (
    admin_users,
    ai_status,
    auth,
    departments,
    doctor_verification,
    health,
    intakes,
    kiosks,
    patients,
    users,
    visits,
)

settings = get_settings()
check_production(settings)  # refuses to start with development placeholders in production
install_log_filter()  # access logs never contain query strings (search terms may be names)

_prod = settings.app_env == "production"
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    # Interactive API docs are for development only.
    docs_url=None if _prod else "/docs",
    redoc_url=None if _prod else "/redoc",
    openapi_url=None if _prod else "/openapi.json",
)

# Security headers, no caching of API responses, early refusal of oversized bodies.
# (Added first so the CORS layer below wraps it: refusals still carry CORS headers.)
app.add_middleware(SecurityMiddleware, max_body_bytes=settings.audio_max_bytes + 1024 * 1024)

# Only the configured frontend origins may call the API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Kiosk-Key"],
)

# Every route lives under /api so it never collides with frontend paths.
for r in (health.router, auth.router, users.router, admin_users.router, patients.router,
          intakes.router, ai_status.router, departments.router, visits.router,
          kiosks.router, doctor_verification.router):
    app.include_router(r, prefix="/api")
