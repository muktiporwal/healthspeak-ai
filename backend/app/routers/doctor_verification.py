"""Doctor self-registration (public) and administrator approval.

- POST /doctors/register          public: creates a PENDING doctor account (role is fixed by the server)
- GET  /doctors/me/verification   the signed-in doctor's own status (also usable while pending)
- GET  /admin/doctors             administrator: applications, filter by status
- POST /admin/doctors/{id}/approve | /reject   administrator only; both are audited
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.enums import DoctorVerification, Role
from app.core.permissions import require_roles
from app.database.models import User
from app.database.session import get_db
from app.schemas.auth import LoginResponse
from app.schemas.doctor import (
    DoctorApplicationList,
    DoctorApplicationOut,
    DoctorDecision,
    DoctorProfileOut,
    DoctorRegister,
    DoctorStatusOut,
)
from app.schemas.user import UserOut
from app.services import auth_service, doctor_service, user_service

router = APIRouter(tags=["doctor-verification"])

admin_only = require_roles(Role.ADMIN)
# The one doctor endpoint a not-yet-verified doctor may call: it only returns their own application.
any_doctor = require_roles(Role.DOCTOR, unverified_ok=True)


def _application(user: User) -> DoctorApplicationOut:
    return DoctorApplicationOut(user=UserOut.model_validate(user),
                                profile=DoctorProfileOut.model_validate(user.doctor_profile))


@router.post("/doctors/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register_doctor(body: DoctorRegister, db: Session = Depends(get_db)) -> LoginResponse:
    """Create a doctor account that is PENDING VERIFICATION. It cannot see any patient data until approved."""
    try:
        user = doctor_service.register(db, body)
    except user_service.DuplicateAccountError:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "An account with this email or phone already exists. Please log in.") from None
    except doctor_service.DuplicateRegistration:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "This medical registration number is already registered.") from None
    token, session = auth_service.start_session(db, user)
    return LoginResponse(access_token=token, expires_at=session.expires_at, user=UserOut.model_validate(user))


@router.get("/doctors/me/verification", response_model=DoctorStatusOut)
def my_verification(user: User = Depends(any_doctor)) -> DoctorStatusOut:
    profile = user.doctor_profile
    return DoctorStatusOut(
        user_id=user.id,
        status=DoctorVerification(user.verification_status),
        profile=DoctorProfileOut.model_validate(profile) if profile else None,
    )


@router.get("/admin/doctors", response_model=DoctorApplicationList)
def list_applications(status_: DoctorVerification | None = Query(None, alias="status"),
                      limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                      _: User = Depends(admin_only), db: Session = Depends(get_db)) -> DoctorApplicationList:
    users, total = doctor_service.list_applications(db, status=status_, limit=limit, offset=offset)
    return DoctorApplicationList(items=[_application(u) for u in users], total=total)


def _decide(user_id: uuid.UUID, body: DoctorDecision, admin: User, db: Session, *, approve: bool):
    if not approve and not (body.note and len(body.note.strip()) >= 3):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Give a short reason for rejecting.")
    try:
        user = doctor_service.decide(db, user_id, admin, approve=approve,
                                     note=body.note.strip() if body.note else None)
    except doctor_service.NotADoctor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor application not found") from None
    except doctor_service.AlreadyDecided:
        raise HTTPException(status.HTTP_409_CONFLICT, "This application has already been decided.") from None
    return _application(user)


@router.post("/admin/doctors/{user_id}/approve", response_model=DoctorApplicationOut)
def approve_doctor(user_id: uuid.UUID, body: DoctorDecision | None = None, admin: User = Depends(admin_only),
                   db: Session = Depends(get_db)):
    return _decide(user_id, body or DoctorDecision(), admin, db, approve=True)


@router.post("/admin/doctors/{user_id}/reject", response_model=DoctorApplicationOut)
def reject_doctor(user_id: uuid.UUID, body: DoctorDecision, admin: User = Depends(admin_only),
                  db: Session = Depends(get_db)):
    return _decide(user_id, body, admin, db, approve=False)
