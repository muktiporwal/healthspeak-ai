"""Queue, schedule, appointment and notification shapes."""

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.core.enums import AppointmentStatus, ContentLanguage, Gender, QueueStatus, ReviewStatus


class Ref(BaseModel):
    id: uuid.UUID
    name: str


class PatientBrief(BaseModel):
    id: uuid.UUID
    full_name: str
    age: int
    gender: Gender
    preferred_language: ContentLanguage


class QueueEntryOut(BaseModel):
    id: uuid.UUID
    token: str
    token_number: int
    day: date
    status: QueueStatus
    department: Ref
    doctor: Ref | None
    patient: PatientBrief
    intake_id: uuid.UUID | None
    intake_review_status: ReviewStatus | None
    priority: str | None = None  # "urgent" / "normal" of the linked intake (None if there is none)
    position: int | None
    created_at: datetime
    checked_in_at: datetime | None
    called_at: datetime | None
    completed_at: datetime | None


class NoteOut(BaseModel):
    id: uuid.UUID
    text: str
    author: str | None
    created_at: datetime


class IntakeBrief(BaseModel):
    """Staff-confirmed intake information shown to the care team."""

    original_language: ContentLanguage
    original_text: str
    final_text: str | None
    review_status: ReviewStatus
    confirmed_department: str | None


class QueueEntryDetail(QueueEntryOut):
    notes: list[NoteOut]
    intake: IntakeBrief | None


class QueueCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: uuid.UUID
    department_id: uuid.UUID
    doctor_user_id: uuid.UUID | None = None


class QueueStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: QueueStatus


class QueueAssign(BaseModel):
    """Omit a field to leave it unchanged; send doctor_user_id: null to unassign."""

    model_config = ConfigDict(extra="forbid")

    doctor_user_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def check_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Note cannot be empty.")
        return v.strip()


class PatientVisitOut(BaseModel):
    token: str
    day: date
    department: str
    status: QueueStatus
    position: int | None
    called_at: datetime | None


class DoctorOut(BaseModel):
    id: uuid.UUID
    full_name: str
    departments: list[str]


class ScheduleOut(BaseModel):
    id: uuid.UUID
    doctor: Ref
    department: Ref
    weekday: int
    start_time: time
    end_time: time
    slot_minutes: int
    room: str | None
    is_active: bool


class ScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doctor_user_id: uuid.UUID
    department_id: uuid.UUID
    weekday: int = Field(ge=0, le=6, description="0 = Monday ... 6 = Sunday")
    start_time: time
    end_time: time
    slot_minutes: int = Field(default=15, ge=5, le=120)
    room: str | None = Field(default=None, max_length=60)

    @field_validator("end_time")
    @classmethod
    def check_order(cls, v: time, info) -> time:
        start = info.data.get("start_time")
        if start is not None and v <= start:
            raise ValueError("End time must be after start time.")
        return v


class ScheduleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_time: time | None = None
    end_time: time | None = None
    slot_minutes: int | None = Field(default=None, ge=5, le=120)
    room: str | None = Field(default=None, max_length=60)
    is_active: bool | None = None


class SlotOut(BaseModel):
    starts_at: datetime
    ends_at: datetime
    department: str
    room: str | None


class AppointmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: uuid.UUID
    doctor_user_id: uuid.UUID
    starts_at: AwareDatetime  # must include a time-zone offset
    reason: str | None = Field(default=None, max_length=300)


class AppointmentOut(BaseModel):
    id: uuid.UUID
    patient: Ref
    doctor: Ref
    department: str
    starts_at: datetime
    ends_at: datetime
    room: str | None
    status: AppointmentStatus
    reason: str | None


class PatientAppointmentOut(BaseModel):
    id: uuid.UUID
    doctor: str
    department: str
    starts_at: datetime
    ends_at: datetime
    room: str | None
    status: AppointmentStatus


class AppointmentStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "cancelled", "no_show"]
    reason: str | None = Field(default=None, max_length=300)


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationOut]
