"""Queue (D5), schedules and appointments (D6), notifications and dashboards.

Access (least privilege):
- staff:   whole queue, schedules, appointments, staff dashboard
- doctor:  ONLY visits/appointments assigned to them (others look like 404),
           limited status changes, own dashboard
- admin:   schedules, doctor list, aggregate dashboard (no patient details)
- patient: own visit token/status, own appointments, own notifications
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.clock import local_today
from app.core.enums import AppointmentStatus, QueueStatus, Role
from app.core.permissions import get_current_user, require_roles
from app.database.models import Appointment, DoctorSchedule, IntakeRecord, Patient, QueueEntry, User
from app.database.session import get_db
from app.schemas.visit import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentStatusChange,
    DoctorOut,
    IntakeBrief,
    NoteCreate,
    NoteOut,
    NotificationList,
    NotificationOut,
    PatientAppointmentOut,
    PatientBrief,
    PatientVisitOut,
    QueueAssign,
    QueueCreate,
    QueueEntryDetail,
    QueueEntryOut,
    QueueStatusChange,
    Ref,
    ScheduleCreate,
    ScheduleOut,
    ScheduleUpdate,
    SlotOut,
)
from app.services import (
    audit_service,
    dashboard_service,
    department_service,
    notification_service,
    patient_service,
    queue_service,
    schedule_service,
)

router = APIRouter(tags=["visits"])

staff_only = require_roles(Role.STAFF)
staff_or_doctor = require_roles(Role.STAFF, Role.DOCTOR)
staff_or_admin = require_roles(Role.STAFF, Role.ADMIN)
workforce = require_roles(Role.STAFF, Role.DOCTOR, Role.ADMIN)
patient_only = require_roles(Role.PATIENT)
doctor_only = require_roles(Role.DOCTOR)
admin_only = require_roles(Role.ADMIN)


# ---------- converters ----------

def _brief(p: Patient) -> PatientBrief:
    return PatientBrief(id=p.id, full_name=p.full_name, age=patient_service.to_out(p).age, gender=p.gender,
                        preferred_language=p.preferred_language)


def _entry_out(db: Session, e: QueueEntry, cls=QueueEntryOut, **extra):
    intake = db.get(IntakeRecord, e.intake_id) if e.intake_id else None
    return cls(
        id=e.id, token=queue_service.token_label(e), token_number=e.token_number, day=e.day, status=e.status,
        department=Ref(id=e.department.id, name=e.department.name),
        doctor=Ref(id=e.doctor.id, name=e.doctor.full_name) if e.doctor else None,
        patient=_brief(e.patient), intake_id=e.intake_id,
        intake_review_status=intake.review_status if intake else None,
        priority=intake.priority if intake else None,
        position=queue_service.position(db, e), created_at=e.created_at, checked_in_at=e.checked_in_at,
        called_at=e.called_at, completed_at=e.completed_at, **extra,
    )


def _detail(db: Session, e: QueueEntry) -> QueueEntryDetail:
    intake = db.get(IntakeRecord, e.intake_id) if e.intake_id else None
    brief = IntakeBrief(original_language=intake.original_language, original_text=intake.original_text,
                        final_text=intake.final_text, review_status=intake.review_status,
                        confirmed_department=intake.confirmed_department_name) if intake else None
    notes = [NoteOut(id=n.id, text=n.text, author=n.author.full_name if n.author else None,
                     created_at=n.created_at) for n in e.notes]
    return _entry_out(db, e, QueueEntryDetail, notes=notes, intake=brief)


def _appt_out(a: Appointment) -> AppointmentOut:
    return AppointmentOut(id=a.id, patient=Ref(id=a.patient.id, name=a.patient.full_name),
                          doctor=Ref(id=a.doctor.id, name=a.doctor.full_name), department=a.department.name,
                          starts_at=a.starts_at, ends_at=a.ends_at, room=a.room, status=a.status, reason=a.reason)


def _schedule_out(s: DoctorSchedule) -> ScheduleOut:
    return ScheduleOut(id=s.id, doctor=Ref(id=s.doctor.id, name=s.doctor.full_name),
                       department=Ref(id=s.department.id, name=s.department.name), weekday=s.weekday,
                       start_time=s.start_time, end_time=s.end_time, slot_minutes=s.slot_minutes, room=s.room,
                       is_active=s.is_active)


def _err(code: int, msg: str):
    raise HTTPException(code, msg) from None


# ---------- queue ----------

def _entry_for(entry_id: uuid.UUID, user: User = Depends(staff_or_doctor),
               db: Session = Depends(get_db)) -> QueueEntry:
    entry = queue_service.get_for(db, entry_id, user)
    if entry is None:
        _err(status.HTTP_404_NOT_FOUND, "Visit not found")
    return entry


@router.post("/queue", response_model=QueueEntryOut, status_code=status.HTTP_201_CREATED)
def add_to_queue(body: QueueCreate, staff: User = Depends(staff_only), db: Session = Depends(get_db)):
    patient = patient_service.get(db, body.patient_id)
    if patient is None:
        _err(status.HTTP_404_NOT_FOUND, "Patient not found")
    dept = department_service.get_active(db, body.department_id)
    if dept is None:
        _err(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an active department")
    try:
        entry = queue_service.create_entry(db, patient=patient, department=dept, actor=staff,
                                           doctor_user_id=body.doctor_user_id)
    except queue_service.AlreadyQueued as e:
        _err(status.HTTP_409_CONFLICT, f"Patient already has an active visit today ({queue_service.token_label(e.entry)})")
    except queue_service.InvalidDoctor:
        _err(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an active doctor")
    return _entry_out(db, entry)


@router.get("/queue", response_model=list[QueueEntryOut])
def list_queue(day: date | None = None, department_id: uuid.UUID | None = None, status_: QueueStatus | None =
               Query(None, alias="status"), q: str | None = Query(None, max_length=80),
               user: User = Depends(staff_or_doctor), db: Session = Depends(get_db)):
    entries = queue_service.list_entries(db, day=day or local_today(), department_id=department_id,
                                         status=status_, q=q,
                                         doctor=user if user.role == Role.DOCTOR.value else None)
    return [_entry_out(db, e) for e in entries]


@router.get("/queue/{entry_id}", response_model=QueueEntryDetail)
def read_visit(entry: QueueEntry = Depends(_entry_for), user: User = Depends(staff_or_doctor),
               db: Session = Depends(get_db)):
    audit_service.record(db, "queue.viewed", actor_user_id=user.id, target_type="queue_entry", target_id=entry.id)
    db.commit()
    return _detail(db, entry)


@router.post("/queue/{entry_id}/status", response_model=QueueEntryDetail)
def change_status(body: QueueStatusChange, entry: QueueEntry = Depends(_entry_for),
                  user: User = Depends(staff_or_doctor), db: Session = Depends(get_db)):
    try:
        return _detail(db, queue_service.change_status(db, entry, body.status, user))
    except queue_service.InvalidTransition:
        _err(status.HTTP_409_CONFLICT, f"Cannot change status from {entry.status} to {body.status.value}")


@router.patch("/queue/{entry_id}", response_model=QueueEntryDetail)
def reassign(body: QueueAssign, entry_id: uuid.UUID, staff: User = Depends(staff_only),
             db: Session = Depends(get_db)):
    entry = queue_service.get_for(db, entry_id, staff)
    if entry is None:
        _err(status.HTTP_404_NOT_FOUND, "Visit not found")
    kwargs = {"department_id": body.department_id}
    if "doctor_user_id" in body.model_fields_set:
        kwargs["doctor_user_id"] = body.doctor_user_id
    try:
        return _detail(db, queue_service.assign(db, entry, staff, **kwargs))
    except queue_service.InvalidDoctor:
        _err(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an active doctor")
    except queue_service.InactiveDepartment:
        _err(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an active department")
    except queue_service.EntryClosed:
        _err(status.HTTP_409_CONFLICT, "This visit is already closed")


@router.post("/queue/{entry_id}/notes", response_model=QueueEntryDetail, status_code=status.HTTP_201_CREATED)
def add_note(body: NoteCreate, entry: QueueEntry = Depends(_entry_for), user: User = Depends(staff_or_doctor),
             db: Session = Depends(get_db)):
    queue_service.add_note(db, entry, user, body.text)
    db.refresh(entry)
    return _detail(db, entry)


@router.get("/patients/me/visits", response_model=list[PatientVisitOut])
def my_visits(user: User = Depends(patient_only), db: Session = Depends(get_db)):
    patient = patient_service.get_for_user(db, user)
    if patient is None:
        return []
    return [PatientVisitOut(token=queue_service.token_label(e), day=e.day, department=e.department.name,
                            status=e.status, position=queue_service.position(db, e), called_at=e.called_at)
            for e in queue_service.for_patient(db, patient)]


# ---------- doctors & schedules ----------

@router.get("/doctors", response_model=list[DoctorOut], dependencies=[Depends(workforce)])
def list_doctors(db: Session = Depends(get_db)):
    schedules = schedule_service.list_schedules(db)
    return [DoctorOut(id=d.id, full_name=d.full_name,
                      departments=sorted({s.department.name for s in schedules
                                          if s.doctor_user_id == d.id and s.is_active}))
            for d in schedule_service.doctors(db)]


@router.get("/doctor-schedules", response_model=list[ScheduleOut])
def list_schedules(doctor_user_id: uuid.UUID | None = None, user: User = Depends(workforce),
                   db: Session = Depends(get_db)):
    if user.role == Role.DOCTOR.value:
        doctor_user_id = user.id  # doctors see their own schedule
    return [_schedule_out(s) for s in schedule_service.list_schedules(db, doctor_user_id)]


@router.post("/doctor-schedules", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(body: ScheduleCreate, user: User = Depends(staff_or_admin), db: Session = Depends(get_db)):
    try:
        return _schedule_out(schedule_service.create_schedule(db, body, user))
    except schedule_service.InvalidDoctor:
        _err(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an active doctor")
    except schedule_service.InactiveDepartment:
        _err(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an active department")


@router.patch("/doctor-schedules/{schedule_id}", response_model=ScheduleOut)
def update_schedule(schedule_id: uuid.UUID, body: ScheduleUpdate, user: User = Depends(staff_or_admin),
                    db: Session = Depends(get_db)):
    s = db.get(DoctorSchedule, schedule_id)
    if s is None:
        _err(status.HTTP_404_NOT_FOUND, "Schedule not found")
    try:
        return _schedule_out(schedule_service.update_schedule(db, s, body, user))
    except schedule_service.SlotUnavailable:
        _err(status.HTTP_422_UNPROCESSABLE_CONTENT, "End time must be after start time")


# ---------- appointments ----------

@router.get("/appointments/slots", response_model=list[SlotOut], dependencies=[Depends(staff_only)])
def free_slots(doctor_user_id: uuid.UUID, day: date, db: Session = Depends(get_db)):
    return [SlotOut(starts_at=s.starts_at, ends_at=s.ends_at, department=s.schedule.department.name,
                    room=s.schedule.room) for s in schedule_service.slots(db, doctor_user_id, day)]


@router.post("/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def book(body: AppointmentCreate, staff: User = Depends(staff_only), db: Session = Depends(get_db)):
    patient = patient_service.get(db, body.patient_id)
    if patient is None:
        _err(status.HTTP_404_NOT_FOUND, "Patient not found")
    try:
        return _appt_out(schedule_service.book(db, patient=patient, doctor_user_id=body.doctor_user_id,
                                               starts_at=body.starts_at, reason=body.reason, actor=staff))
    except schedule_service.InvalidDoctor:
        _err(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose an active doctor")
    except schedule_service.SlotUnavailable:
        _err(status.HTTP_409_CONFLICT, "That time is not available. Please choose another slot.")


@router.get("/appointments", response_model=list[AppointmentOut])
def list_appointments(day: date | None = None, days: int = Query(1, ge=1, le=31),
                      doctor_user_id: uuid.UUID | None = None,
                      user: User = Depends(staff_or_doctor), db: Session = Depends(get_db)):
    """`day` defaults to today. `days` (default 1) also lists the following days, so a doctor can see upcoming bookings."""
    if user.role == Role.DOCTOR.value:
        doctor_user_id = user.id
    return [_appt_out(a) for a in schedule_service.list_appointments(db, day=day or local_today(), days=days,
                                                                       doctor_user_id=doctor_user_id)]


@router.post("/appointments/{appointment_id}/status", response_model=AppointmentOut)
def appointment_status(appointment_id: uuid.UUID, body: AppointmentStatusChange,
                       user: User = Depends(staff_or_doctor), db: Session = Depends(get_db)):
    a = db.get(Appointment, appointment_id)
    if a is None or (user.role == Role.DOCTOR.value and a.doctor_user_id != user.id):
        _err(status.HTTP_404_NOT_FOUND, "Appointment not found")
    try:
        return _appt_out(schedule_service.set_status(db, a, AppointmentStatus(body.status), user, body.reason))
    except schedule_service.InvalidTransition:
        _err(status.HTTP_409_CONFLICT, "This change is not allowed")


@router.get("/patients/me/appointments", response_model=list[PatientAppointmentOut])
def my_appointments(user: User = Depends(patient_only), db: Session = Depends(get_db)):
    patient = patient_service.get_for_user(db, user)
    if patient is None:
        return []
    return [PatientAppointmentOut(id=a.id, doctor=a.doctor.full_name, department=a.department.name,
                                  starts_at=a.starts_at, ends_at=a.ends_at, room=a.room, status=a.status)
            for a in schedule_service.list_appointments(db, patient_id=patient.id)]


# ---------- notifications ----------

@router.get("/notifications", response_model=NotificationList)
def my_notifications(unread_only: bool = False, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    return NotificationList(unread=notification_service.unread_count(db, user),
                            items=[NotificationOut.model_validate(n)
                                   for n in notification_service.list_for(db, user, unread_only=unread_only)])


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def read_notification(notification_id: uuid.UUID, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    if not notification_service.mark_read(db, user, notification_id):
        _err(status.HTTP_404_NOT_FOUND, "Notification not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification_service.mark_all_read(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- dashboards ----------

@router.get("/dashboard/staff", dependencies=[Depends(staff_only)])
def staff_dashboard(db: Session = Depends(get_db)) -> dict:
    return dashboard_service.staff(db)


@router.get("/dashboard/doctor")
def doctor_dashboard(user: User = Depends(doctor_only), db: Session = Depends(get_db)) -> dict:
    return dashboard_service.doctor(db, user)


@router.get("/dashboard/admin", dependencies=[Depends(admin_only)])
def admin_dashboard(db: Session = Depends(get_db)) -> dict:
    return dashboard_service.admin(db)
