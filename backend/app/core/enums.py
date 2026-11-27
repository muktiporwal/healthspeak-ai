"""Fixed value lists shared by models, schemas and permission checks.

The database enforces the same lists with CHECK constraints, so a typo can never
be stored. Add a value here AND in a new migration when extending a list.
"""

from enum import StrEnum


class Role(StrEnum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    STAFF = "staff"  # front-desk / medical staff
    ADMIN = "admin"  # hospital administrator


class DoctorVerification(StrEnum):
    """Where a self-registered doctor is in the administrator's verification of their credentials."""

    PENDING = "pending"  # submitted, nobody has checked the details yet: NO doctor access
    APPROVED = "approved"  # an administrator verified the registration details
    REJECTED = "rejected"  # an administrator did not accept them


class UiLanguage(StrEnum):
    """Language used to DISPLAY the app to one user (not the spoken-audio language)."""

    EN = "en"
    HI = "hi"
    UR = "ur"
    DOI = "doi"  # Dogri (ISO 639-3), written in Devanagari


class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class ConsentType(StrEnum):
    # Consent to collect and process the patient's details and described concerns.
    DATA_PROCESSING = "data_processing"


class ConsentMethod(StrEnum):
    SELF_SERVICE = "self_service"  # patient ticked the box themselves
    STAFF_ASSISTED = "staff_assisted"  # staff recorded the patient's verbal/written consent


class ContentLanguage(StrEnum):
    """Language a patient SPOKE or TYPED in (separate from anyone's UI language)."""

    EN = "en"
    HI = "hi"
    UR = "ur"
    DOI = "doi"  # Dogri (ISO 639-3), written in Devanagari


class ConversationStatus(StrEnum):
    OPEN = "open"
    SUBMITTED = "submitted"


class MessageSender(StrEnum):
    PATIENT = "patient"
    ASSISTANT = "assistant"  # fixed, non-clinical acknowledgement text


class InputMode(StrEnum):
    TEXT = "text"
    VOICE_BROWSER = "voice_browser"  # (legacy) transcribed by the browser's speech service
    VOICE_SERVER = "voice_server"  # recorded audio transcribed by our local model, reviewed by the patient


class TranscriptionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class TranslationStatus(StrEnum):
    NOT_NEEDED = "not_needed"  # original is already English
    PENDING = "pending"  # waiting for the local translation model
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    PENDING_REVIEW = "pending_review"  # AI/system output, not yet checked by staff
    CONFIRMED = "confirmed"  # an authorised staff member confirmed the final text


class IntakePriority(StrEnum):
    """Urgent / Normal flag on an intake record (from the existing emergency rules; staff may change it)."""

    URGENT = "urgent"
    NORMAL = "normal"


class PrioritySource(StrEnum):
    SYSTEM = "system"  # set by the emergency rules
    STAFF = "staff"  # set or changed by a staff member (with a reason); the system never overrides it


class QueueStatus(StrEnum):
    WAITING = "waiting"
    CHECKED_IN = "checked_in"
    IN_CONSULTATION = "in_consultation"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


QUEUE_ACTIVE = (QueueStatus.WAITING, QueueStatus.CHECKED_IN, QueueStatus.IN_CONSULTATION)

# Allowed status changes. Staff may make any of these; doctors only the ones in
# DOCTOR_QUEUE_TRANSITIONS, and only for patients assigned to them.
QUEUE_TRANSITIONS = {
    QueueStatus.WAITING: {QueueStatus.CHECKED_IN, QueueStatus.CANCELLED, QueueStatus.NO_SHOW},
    QueueStatus.CHECKED_IN: {QueueStatus.IN_CONSULTATION, QueueStatus.CANCELLED, QueueStatus.NO_SHOW},
    QueueStatus.IN_CONSULTATION: {QueueStatus.COMPLETED},
}
DOCTOR_QUEUE_TRANSITIONS = {
    QueueStatus.CHECKED_IN: {QueueStatus.IN_CONSULTATION},
    QueueStatus.IN_CONSULTATION: {QueueStatus.COMPLETED},
}


class AppointmentStatus(StrEnum):
    BOOKED = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class SymptomStatus(StrEnum):
    """What the patient's words say about one symptom mention (machine-assigned, never edited)."""

    CURRENT = "current"
    UNCERTAIN = "uncertain"  # patient sounded unsure
    NEGATED = "negated"  # patient said they do NOT have it
    HISTORICAL = "historical"  # described as past
    THIRD_PARTY = "third_party"  # described for another person


class SymptomReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"  # AI output only
    CONFIRMED = "confirmed"  # staff agree with the AI's reading
    CORRECTED = "corrected"  # staff changed the symptom and/or its status
    REJECTED = "rejected"  # staff say this is not a symptom of the patient


class SymptomMatchType(StrEnum):
    EXACT = "exact"
    FUZZY = "fuzzy"  # one-typo match
    STAFF = "staff"  # added by a staff member


def sql_in_list(enum_cls: type[StrEnum]) -> str:
    """Render "'a', 'b', 'c'" for use inside a CHECK constraint."""
    return ", ".join(f"'{m.value}'" for m in enum_cls)
