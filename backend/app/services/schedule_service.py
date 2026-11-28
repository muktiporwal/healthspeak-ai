"""D6: doctor schedules, bookable slots and appointments."""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import hospital_tz, local_day_bounds_utc, now_utc
from app.core.enums import AppointmentStatus, Role
from app.database.models import Appointment, Department, DoctorSchedule, Patient, User
from app.services import audit_service, doctor_service, notification_service


class InvalidDoctor(Exception):
    pass


class InactiveDepartment(Exception):
    pass


class SlotUnavailable(Exception):
    pass


class InvalidTransition(Exception):
    pass


def doctors(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(doctor_service.verified_doctor_clause())
                           .order_by(User.full_name)))


def _doctor(db: Session, doctor_user_id: uuid.UUID) -> User:
    d = db.get(User, doctor_user_id)
    if d is None or not d.is_active or not doctor_service.is_verified(d):
        raise InvalidDoctor
    return d


def _department(db: Session, department_id: uuid.UUID) -> Department:
    d = db.get(Department, department_id)
    if d is None or not d.is_active:
        raise InactiveDepartment
    return d


# ---------- schedules ----------

def list_schedules(db: Session, doctor_user_id: uuid.UUID | None = None) -> list[DoctorSchedule]:
    q = select(DoctorSchedule).order_by(DoctorSchedule.weekday, DoctorSchedule.start_time)
    if doctor_user_id:
        q = q.where(DoctorSchedule.doctor_user_id == doctor_user_id)
    return list(db.scalars(q))


def create_schedule(db: Session, data, actor: User) -> DoctorSchedule:
    _doctor(db, data.doctor_user_id)
    _department(db, data.department_id)
    s = DoctorSchedule(doctor_user_id=data.doctor_user_id, department_id=data.department_id,
                       weekday=data.weekday, start_time=data.start_time, end_time=data.end_time,
                       slot_minutes=data.slot_minutes, room=data.room)
    db.add(s)
    db.flush()
    audit_service.record(db, "schedule.created", actor_user_id=actor.id, target_type="schedule", target_id=s.id)
    db.commit()
    db.refresh(s)
    return s


def update_schedule(db: Session, s: DoctorSchedule, data, actor: User) -> DoctorSchedule:
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    for k, v in changes.items():
        setattr(s, k, v)
    if s.start_time >= s.end_time:
        raise SlotUnavailable
    audit_service.record(db, "schedule.updated", actor_user_id=actor.id, target_type="schedule",
                         target_id=s.id, details={"fields": sorted(changes)})
    db.commit()
    db.refresh(s)
    return s


# ---------- slots ----------

@dataclass
class Slot:
    starts_at: datetime
    ends_at: datetime
    schedule: DoctorSchedule


def slots(db: Session, doctor_user_id: uuid.UUID, day: date, *, include_booked: bool = False) -> list[Slot]:
    """Free slots for a doctor on a hospital-local day (past times excluded)."""
    tz = hospital_tz()
    schedules = [s for s in list_schedules(db, doctor_user_id)
                 if s.is_active and s.weekday == day.weekday() and s.department.is_active]
    start_utc, end_utc = local_day_bounds_utc(day)
    booked = set(db.scalars(select(Appointment.starts_at).where(
        Appointment.doctor_user_id == doctor_user_id, Appointment.status == AppointmentStatus.BOOKED.value,
        Appointment.starts_at >= start_utc, Appointment.starts_at < end_utc)))
    now = now_utc()
    out: list[Slot] = []
    for s in schedules:
        t = datetime.combine(day, s.start_time, tzinfo=tz)
        end = datetime.combine(day, s.end_time, tzinfo=tz)
        step = timedelta(minutes=s.slot_minutes)
        while t + step <= end:
            su = t.astimezone(UTC)
            if su > now and (include_booked or su not in booked):
                out.append(Slot(su, (t + step).astimezone(UTC), s))
            t += step
    return sorted(out, key=lambda x: x.starts_at)


# ---------- appointments ----------

def book(db: Session, *, patient: Patient, doctor_user_id: uuid.UUID, starts_at: datetime,
         reason: str | None, actor: User) -> Appointment:
    doctor = _doctor(db, doctor_user_id)
    starts_at = starts_at.astimezone(UTC)
    local_day = starts_at.astimezone(hospital_tz()).date()
    match = next((s for s in slots(db, doctor.id, local_day) if s.starts_at == starts_at), None)
    if match is None:
        raise SlotUnavailable
    appt = Appointment(patient_id=patient.id, doctor_user_id=doctor.id, department_id=match.schedule.department_id,
                       schedule_id=match.schedule.id, starts_at=match.starts_at, ends_at=match.ends_at,
                       room=match.schedule.room, status=AppointmentStatus.BOOKED.value, reason=reason,
                       created_by_user_id=actor.id)
    db.add(appt)
    try:
        db.flush()
    except IntegrityError:  # someone booked the same slot a moment earlier
        db.rollback()
        raise SlotUnavailable from None
    db.refresh(appt)
    local = appt.starts_at.astimezone(hospital_tz())
    audit_service.record(db, "appointment.booked", actor_user_id=actor.id, target_type="appointment",
                         target_id=appt.id)
    notification_service.notify(db, patient.user_id, "appointment.booked", "Appointment booked",
                                f"{appt.department.name} with {doctor.full_name} on "
                                f"{local:%d %b %Y at %H:%M}" + (f", {appt.room}" if appt.room else "") + ".")
    notification_service.notify(db, doctor.id, "appointment.booked", "New appointment",
                                f"{appt.department.name} on {local:%d %b %Y at %H:%M}.")
    db.commit()
    db.refresh(appt)
    return appt


def list_appointments(db: Session, *, day: date | None = None, days: int = 1,
                      doctor_user_id: uuid.UUID | None = None,
                      patient_id: uuid.UUID | None = None) -> list[Appointment]:
    """Appointments on `day`, or on `day` and the following `days - 1` days (hospital-local calendar days)."""
    q = select(Appointment)
    if day:
        start, _ = local_day_bounds_utc(day)
        _, end = local_day_bounds_utc(day + timedelta(days=max(days, 1) - 1))
        q = q.where(Appointment.starts_at >= start, Appointment.starts_at < end)
    if doctor_user_id:
        q = q.where(Appointment.doctor_user_id == doctor_user_id)
    if patient_id:
        q = q.where(Appointment.patient_id == patient_id)
    return list(db.scalars(q.order_by(Appointment.starts_at)))


def set_status(db: Session, appt: Appointment, new: AppointmentStatus, actor: User,
               reason: str | None) -> Appointment:
    if appt.status != AppointmentStatus.BOOKED.value or new == AppointmentStatus.BOOKED:
        raise InvalidTransition
    if actor.role == Role.DOCTOR.value and (appt.doctor_user_id != actor.id or new == AppointmentStatus.CANCELLED):
        raise InvalidTransition
    appt.status = new.value
    if new == AppointmentStatus.CANCELLED:
        appt.cancelled_reason = reason
        local = appt.starts_at.astimezone(hospital_tz())
        notification_service.notify(db, appt.patient.user_id, "appointment.cancelled", "Appointment cancelled",
                                    f"Your {appt.department.name} appointment on {local:%d %b %Y at %H:%M} "
                                    "was cancelled. Please contact the hospital to rebook.")
    audit_service.record(db, "appointment.status", actor_user_id=actor.id, target_type="appointment",
                         target_id=appt.id, details={"to": new.value})
    db.commit()
    db.refresh(appt)
    return appt
