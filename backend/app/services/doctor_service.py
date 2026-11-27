"""Doctor self-registration and administrator verification.

Registering never grants doctor access: the account starts PENDING. `require_roles` (core/permissions.py)
refuses every doctor-only endpoint until an administrator approves. The submitted details are claims that
the administrator must check; nothing here treats them as proof.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, exists, func, not_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import DoctorVerification, Role, UiLanguage
from app.database.models import DoctorProfile, User
from app.schemas.doctor import DoctorRegister
from app.services import audit_service, user_service


class NotADoctor(Exception):
    """The target account is not a self-registered doctor."""


class AlreadyDecided(Exception):
    """The application was already approved or rejected."""


class DuplicateRegistration(Exception):
    """That registration number is already used by another account."""


def verified_doctor_clause():
    """SQL condition: active doctor who is not waiting for / refused by verification."""
    unverified = exists().where(DoctorProfile.user_id == User.id,
                                DoctorProfile.verification_status != DoctorVerification.APPROVED.value)
    return and_(User.role == Role.DOCTOR.value, User.is_active.is_(True), not_(unverified))


def is_verified(user: User) -> bool:
    return user.role == Role.DOCTOR.value and user.verification_status == DoctorVerification.APPROVED.value


def register(db: Session, body: DoctorRegister) -> User:
    """Create a doctor account in PENDING state (the role is fixed here, never taken from the client)."""
    number = body.registration_number
    authority = body.registration_authority
    if db.scalar(select(func.count()).select_from(DoctorProfile).where(
            func.upper(DoctorProfile.registration_number) == number.upper(),
            func.upper(DoctorProfile.registration_authority) == authority.upper())):
        raise DuplicateRegistration
    user = user_service.create_user(
        db, full_name=body.full_name, password=body.password, role=Role.DOCTOR, email=body.email,
        phone=body.phone, ui_language=body.ui_language or UiLanguage.EN, commit=False,
    )
    db.add(DoctorProfile(
        user_id=user.id, qualification=body.qualification, specialization=body.specialization,
        registration_number=number, registration_authority=authority, hospital_name=body.hospital_name,
        years_experience=body.years_experience, verification_status=DoctorVerification.PENDING.value,
    ))
    audit_service.record(db, "doctor.registered", actor_user_id=user.id, target_type="user", target_id=user.id,
                         details={"status": DoctorVerification.PENDING.value})
    try:
        db.commit()
    except IntegrityError:  # same number registered at the same moment
        db.rollback()
        raise DuplicateRegistration from None
    db.refresh(user)
    return user


def list_applications(db: Session, *, status: DoctorVerification | None, limit: int, offset: int):
    q = select(User).join(DoctorProfile, DoctorProfile.user_id == User.id)
    if status:
        q = q.where(DoctorProfile.verification_status == status.value)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    users = list(db.scalars(q.order_by(DoctorProfile.created_at, User.id).limit(limit).offset(offset)))
    return users, total


def _application(db: Session, user_id: uuid.UUID) -> DoctorProfile:
    profile = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == user_id).with_for_update())
    if profile is None:
        raise NotADoctor
    return profile


def decide(db: Session, user_id: uuid.UUID, admin: User, *, approve: bool, note: str | None) -> User:
    profile = _application(db, user_id)
    if profile.verification_status != DoctorVerification.PENDING.value:
        raise AlreadyDecided
    new = DoctorVerification.APPROVED if approve else DoctorVerification.REJECTED
    profile.verification_status = new.value
    profile.reviewed_by_user_id = admin.id
    profile.reviewed_at = datetime.now(timezone.utc)
    profile.review_note = note
    audit_service.record(db, f"doctor.{new.value}", actor_user_id=admin.id, target_type="user",
                         target_id=user_id, details={"note": note} if note else None)
    db.commit()
    user = db.get(User, user_id)
    db.refresh(user)
    return user
