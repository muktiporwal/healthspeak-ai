"""Phase 9 hardening: access-control sweep, headers, size limit, log scrubbing,
production safety checks and maintenance tasks."""

import logging
import re
from datetime import timedelta

import pytest

from app.core.clock import now_utc
from app.core.config import Settings
from app.core.enums import Role
from app.core.hardening import StripQueryFromAccessLog, UnsafeProductionConfig, check_production
from app.database.models import AuthSession
from app.main import app
from app import maintenance

# Endpoints that are deliberately reachable without a login.
PUBLIC = {
    ("GET", "/api/health"), ("GET", "/api/health/db"), ("POST", "/api/auth/login"),
    ("GET", "/api/consent/current"), ("POST", "/api/patients/register"),
    # Doctor sign-up is public by nature, but it only ever creates a PENDING doctor with no access
    # (tests/test_doctor_verification.py); an administrator must approve before any doctor endpoint opens.
    ("POST", "/api/doctors/register"),
    ("POST", "/api/kiosks/heartbeat"),  # needs a kiosk key instead of a login
    # Forgot-password by SMS code: the caller is by definition logged out. Safety lives in the
    # service (same answer for every number, attempt limits, resend limits, patients only).
    ("POST", "/api/auth/password-reset/request"), ("POST", "/api/auth/password-reset/confirm"),
}
DUMMY_ID = "00000000-0000-0000-0000-000000000000"


def _operations():
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            yield method.upper(), path


def test_public_endpoint_list_is_exactly_as_intended():
    unsecured = {(m, p) for m, p in _operations()
                 if not app.openapi()["paths"][p][m.lower()].get("security")}
    assert unsecured == PUBLIC


@pytest.mark.parametrize("method,path", sorted(set(_operations()) - PUBLIC))
def test_every_protected_endpoint_rejects_anonymous_callers(client, method, path):
    url = re.sub(r"\{[^}]+\}", DUMMY_ID, path)
    r = client.request(method, url, json={} if method in ("POST", "PATCH") else None)
    assert r.status_code == 401, (method, path, r.status_code, r.text[:200])


def test_security_headers_and_no_store(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"


def test_oversized_request_refused_before_reading(client, auth_headers):
    h = auth_headers(Role.PATIENT)
    r = client.post(f"/api/conversations/{DUMMY_ID}/transcriptions",
                    headers={**h, "Content-Length": str(50 * 1024 * 1024), "Content-Type": "audio/webm"},
                    content=b"x")
    assert r.status_code == 413


def test_cors_allows_configured_origin_only(client):
    ok = client.options("/api/health", headers={"Origin": "http://localhost:5173",
                                                "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options("/api/health", headers={"Origin": "http://evil.example",
                                                 "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_access_log_query_strings_removed():
    rec = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                            ("127.0.0.1:5000", "GET", "/api/patients?q=Some%20Name", "1.1", 200), None)
    StripQueryFromAccessLog().filter(rec)
    assert "Some" not in rec.getMessage() and "/api/patients?[removed]" in rec.getMessage()


@pytest.mark.parametrize("override,problem", [
    ({}, "example password"),
    ({"database_url": "postgresql+psycopg://u:strong@db/x", "seed_demo_password": "x" * 10}, "SEED_DEMO_PASSWORD"),
    ({"database_url": "postgresql+psycopg://u:strong@db/x"}, "localhost"),
])
def test_production_refuses_unsafe_settings(override, problem):
    s = Settings(_env_file=None, app_env="production", **override)
    with pytest.raises(UnsafeProductionConfig, match=problem):
        check_production(s)


def test_production_accepts_safe_settings():
    s = Settings(_env_file=None, app_env="production", database_url="postgresql+psycopg://u:strong@db/x",
                 cors_origins="https://healthspeak.hospital.example")
    check_production(s)  # does not raise


def test_purge_sessions_removes_only_old_expired_or_revoked(db, make_user, login, client):
    make_user(Role.PATIENT, email="purge@example.com")
    login("purge@example.com")  # an active session that must survive
    old = now_utc() - timedelta(days=40)
    user_id = db.query(AuthSession).first().user_id
    db.add_all([AuthSession(user_id=user_id, token_hash="a" * 64, expires_at=old),
                AuthSession(user_id=user_id, token_hash="b" * 64, expires_at=now_utc() + timedelta(hours=1),
                            revoked_at=old)])
    db.commit()
    assert maintenance.purge_sessions(db, 30) == 2
    assert db.query(AuthSession).count() == 1
