"""ORM models. Importing this package registers every table on Base.metadata."""

from app.database.models.audit_event import AuditEvent
from app.database.models.auth_session import AuthSession
from app.database.models.department import Department, RoutingRule
from app.database.models.intake import (
    AudioTranscription,
    Conversation,
    ExtractedSymptom,
    IntakeAnalysis,
    IntakeRecord,
    IntakeRevision,
    Message,
)
from app.database.models.doctor import DoctorProfile
from app.database.models.kiosk import Kiosk
from app.database.models.password_reset import PasswordResetCode
from app.database.models.patient import ConsentRecord, Patient
from app.database.models.user import User
from app.database.models.visit import (
    Appointment,
    DoctorSchedule,
    Notification,
    QueueCounter,
    QueueEntry,
    QueueNote,
)

__all__ = [
    "AudioTranscription", "AuditEvent", "AuthSession", "ConsentRecord", "Conversation", "Department",
    "ExtractedSymptom", "IntakeAnalysis", "IntakeRecord", "RoutingRule",
    "IntakeRevision", "Message", "PasswordResetCode", "Patient", "User",
    "Appointment", "DoctorSchedule", "Notification", "QueueCounter", "QueueEntry", "QueueNote",
    "Kiosk", "DoctorProfile",
]
