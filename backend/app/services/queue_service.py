"""D5 queue: tokens, status changes, doctor assignment, care-team notes."""

import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.clock import local_today, now_utc
from app.core.enums import (
    DOCTOR_QUEUE_TRANSITIONS,
    QUEUE_ACTIVE,
    QUEUE_TRANSITIONS,
    QueueStatus,
    Role,
)
from app.database.models import (
    Department,
    IntakeRecord,
    Patient,
    QueueCounter,
    QueueEntry,
    QueueNote,
    User,
)
from app.services import audit_service, doctor_service, notification_service


class AlreadyQueued(Exception):
    def __init__(self, entry: QueueEntry):
        self.entry = entry


class InvalidTransition(Exception):
    pass


class InvalidDoctor(Exception):
    pass


class InactiveDepartment(Exception):
    pass


class EntryClosed(Exception):
    pass


def token_prefix(code: str) -> str:
    parts = [p for p in code.split("_") if p]
    return "".join(p[0] for p in parts).upper() if len(parts) > 1 else code[:3].upper()


def token_label(entry: QueueEntry) -> str:
    return f"{token_prefix(entry.department.code)}-{entry.token_number:03d}"


def _next_token(db: Session, department_id: uuid.UUID, day: date) -> int:
    """Atomic per-department, per-day counter (safe with concurrent requests)."""
    stmt = insert(QueueCounter).values(department_id=department_id, day=day, last_number=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=["department_id", "day"],
        set_={"last_number": QueueCounter.last_number + 1},
    ).returning(QueueCounter.last_number)
    return db.execute(stmt).scalar_one()


def active_entry_today(db: Session, patient_id: uuid.UUID) -> QueueEntry | None:
    return db.scalar(select(QueueEntry).where(
        QueueEntry.patient_id == patient_id, QueueEntry.day == local_today(),
        QueueEntry.status.in_([s.value for s in QUEUE_ACTIVE])))


def _check_doctor(db: Session, doctor_user_id: uuid.UUID | None) -> User | None:
    if doctor_user_id is None:
        return None
    doctor = db.get(User, doctor_user_id)
    if doctor is None or not doctor.is_active or not doctor_service.is_verified(doctor):
        raise InvalidDoctor
    return doctor


def create_entry(db: Session, *, patient: Patient, department: Department, actor: User,
                 intake: IntakeRecord | None = None, doctor_user_id: uuid.UUID | None = None,
                 commit: bool = True) -> QueueEntry:
    if not department.is_active:
        raise InactiveDepartment
    existing = active_entry_today(db, patient.id)
    if existing is not None:
        raise AlreadyQueued(existing)
    doctor = _check_doctor(db, doctor_user_id)
    day = local_today()
    entry = QueueEntry(patient_id=patient.id, intake_id=intake.id if intake else None,
                       department_id=department.id, doctor_user_id=doctor.id if doctor else None,
                       day=day, token_number=_next_token(db, department.id, day),
                       status=QueueStatus.WAITING.value, created_by_user_id=actor.id)
    db.add(entry)
    db.flush()
    db.refresh(entry)
    label = token_label(entry)
    audit_service.record(db, "queue.created", actor_user_id=actor.id, target_type="queue_entry",
                         target_id=entry.id, details={"token": label, "department": department.code})
    notification_service.notify(db, patient.user_id, "queue.token", "Your visit token",
                                f"Your token is {label} for {department.name}. Please wait to be called.")
    if doctor:
        notification_service.notify(db, doctor.id, "queue.assigned", "New patient assigned",
                                    f"Token {label} ({department.name}) has been assigned to you.")
    if commit:
        db.commit()
        db.refresh(entry)
    return entry


def list_entries(db: Session, *, day: date, department_id: uuid.UUID | None = None,
                 status: QueueStatus | None = None, q: str | None = None,
                 doctor: User | None = None) -> list[QueueEntry]:
    stmt = select(QueueEntry).join(Patient, Patient.id == QueueEntry.patient_id).where(QueueEntry.day == day)
    if doctor is not None:  # doctors only ever see patients assigned to them
        stmt = stmt.where(QueueEntry.doctor_user_id == doctor.id)
    if department_id:
        stmt = stmt.where(QueueEntry.department_id == department_id)
    if status:
        stmt = stmt.where(QueueEntry.status == status.value)
    if q and q.strip():
        term = q.strip()
        conds = [Patient.full_name.ilike(f"%{term.replace('%', '').replace('_', '')}%")]
        if term.isdigit():
            conds.append(QueueEntry.token_number == int(term))
        stmt = stmt.where(or_(*conds))
    return list(db.scalars(stmt.order_by(QueueEntry.department_id, QueueEntry.token_number)))


def get_for(db: Session, entry_id: uuid.UUID, user: User) -> QueueEntry | None:
    entry = db.get(QueueEntry, entry_id)
    if entry is None:
        return None
    if user.role == Role.DOCTOR.value and entry.doctor_user_id != user.id:
        return None  # not assigned to this doctor: behave as if it does not exist
    return entry


def position(db: Session, entry: QueueEntry) -> int | None:
    """How many active patients are ahead in the same department today."""
    if entry.status not in (QueueStatus.WAITING.value, QueueStatus.CHECKED_IN.value):
        return None
    return db.scalar(select(func.count()).select_from(QueueEntry).where(
        QueueEntry.department_id == entry.department_id, QueueEntry.day == entry.day,
        QueueEntry.token_number < entry.token_number,
        QueueEntry.status.in_([QueueStatus.WAITING.value, QueueStatus.CHECKED_IN.value])))


def change_status(db: Session, entry: QueueEntry, new: QueueStatus, actor: User) -> QueueEntry:
    current = QueueStatus(entry.status)
    table = DOCTOR_QUEUE_TRANSITIONS if actor.role == Role.DOCTOR.value else QUEUE_TRANSITIONS
    if new not in table.get(current, set()):
        raise InvalidTransition
    now = now_utc()
    entry.status = new.value
    if new == QueueStatus.CHECKED_IN:
        entry.checked_in_at = now
    elif new == QueueStatus.IN_CONSULTATION:
        entry.called_at = now
        if actor.role == Role.DOCTOR.value and entry.doctor_user_id is None:
            entry.doctor_user_id = actor.id
    elif new == QueueStatus.COMPLETED:
        entry.completed_at = now
    else:
        entry.closed_at = now
    label = token_label(entry)
    audit_service.record(db, "queue.status", actor_user_id=actor.id, target_type="queue_entry",
                         target_id=entry.id, details={"from": current.value, "to": new.value})
    if new == QueueStatus.IN_CONSULTATION:
        notification_service.notify(db, entry.patient.user_id, "queue.called", "It's your turn",
                                    f"Token {label}: please go to {entry.department.name} now.")
    db.commit()
    db.refresh(entry)
    return entry


def assign(db: Session, entry: QueueEntry, actor: User, *, doctor_user_id=..., department_id=None) -> QueueEntry:
    """Change the assigned doctor and/or department of an active visit."""
    if entry.status not in [s.value for s in QUEUE_ACTIVE]:
        raise EntryClosed
    changes = {}
    if department_id is not None and department_id != entry.department_id:
        dept = db.get(Department, department_id)
        if dept is None or not dept.is_active:
            raise InactiveDepartment
        # A new department means a new token in that department's line.
        entry.department_id = dept.id
        entry.token_number = _next_token(db, dept.id, entry.day)
        db.flush()
        db.refresh(entry)
        changes["department"] = dept.code
    if doctor_user_id is not ...:
        doctor = _check_doctor(db, doctor_user_id)
        entry.doctor_user_id = doctor.id if doctor else None
        changes["doctor"] = str(doctor.id) if doctor else None
        if doctor:
            notification_service.notify(db, doctor.id, "queue.assigned", "New patient assigned",
                                        f"Token {token_label(entry)} ({entry.department.name}) has been "
                                        "assigned to you.")
    audit_service.record(db, "queue.assigned", actor_user_id=actor.id, target_type="queue_entry",
                         target_id=entry.id, details=changes)
    db.commit()
    db.refresh(entry)
    return entry


def add_note(db: Session, entry: QueueEntry, actor: User, text: str) -> QueueNote:
    note = QueueNote(entry=entry, author_user_id=actor.id, text=text)
    db.add(note)
    db.flush()
    audit_service.record(db, "queue.note_added", actor_user_id=actor.id, target_type="queue_entry",
                         target_id=entry.id)
    db.commit()
    db.refresh(note)
    return note


def for_patient(db: Session, patient: Patient) -> list[QueueEntry]:
    return list(db.scalars(select(QueueEntry).where(QueueEntry.patient_id == patient.id)
                           .order_by(QueueEntry.day.desc(), QueueEntry.created_at.desc()).limit(10)))
