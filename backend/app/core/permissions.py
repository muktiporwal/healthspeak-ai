"""FastAPI dependencies for authentication (401) and role checks (403).

Usage in a router:
    @router.get("/thing")
    def thing(user: User = Depends(get_current_user)): ...

    @router.get("/admin-thing", dependencies=[Depends(require_roles(Role.ADMIN))])
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.enums import DoctorVerification, Role
from app.database.models import AuthSession, User
from app.database.session import get_db
from app.services import auth_service

_bearer = HTTPBearer(auto_error=False, description="Token from POST /api/auth/login")

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_session(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> AuthSession:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise _UNAUTHENTICATED
    session = auth_service.resolve_session(db, creds.credentials)
    if session is None:
        raise _UNAUTHENTICATED
    return session


def get_current_user(session: AuthSession = Depends(get_current_session)) -> User:
    return session.user


def require_roles(*roles: Role, unverified_ok: bool = False) -> Callable[..., User]:
    """`unverified_ok` is only for the pending doctor's own status page; everything else keeps the check."""
    allowed = {Role(r).value for r in roles}

    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")
        # A self-registered doctor has NO doctor access until an administrator approves the account.
        if (user.role == Role.DOCTOR.value and not unverified_ok
                and user.verification_status != DoctorVerification.APPROVED.value):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Doctor account is not verified yet")
        return user

    return _check
