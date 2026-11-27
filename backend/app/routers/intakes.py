"""Patient conversations/intake submission, and staff intake review.

Access (this phase):
- patient: their own conversations and intakes only (others' ids return 404)
- staff:   list, view (audited), correct and confirm intakes
- doctor:  verified doctors read (only) the intakes of visits assigned to them, under /doctor/intakes
- admin:   no access to intakes
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.audio import AudioRejected
from app.core.config import get_settings
from app.core.enums import ContentLanguage, ReviewStatus, Role
from app.core.permissions import require_roles
from app.database.models import Conversation, IntakeRecord, Patient, QueueEntry, User
from app.database.session import get_db
from app.schemas.history import HistoryOut, SymptomAdd, SymptomOut, SymptomReview
from app.schemas.intake import (
    ConversationOut,
    IntakeConfirm,
    IntakeCorrection,
    IntakeList,
    IntakePatientView,
    IntakeStaffView,
    MessageCreate,
    MessageExchange,
    MessageOut,
    PriorityChange,
    TranscriptionOut,
)
from app.services import (
    analysis_service,
    audit_service,
    history_service,
    intake_service,
    patient_service,
    priority_service,
    speech_service,
    symptom_service,
    translation_service,
)

router = APIRouter(tags=["intake"])

patient_only = require_roles(Role.PATIENT)
staff_only = require_roles(Role.STAFF)
doctor_only = require_roles(Role.DOCTOR)  # verified doctors only (see core/permissions.py)

_ERRORS = {
    intake_service.ConsentMissing: (status.HTTP_403_FORBIDDEN,
                                    "Please give consent before sharing your health concerns."),
    intake_service.ConversationClosed: (status.HTTP_409_CONFLICT, "This conversation has already been submitted."),
    intake_service.TooManyMessages: (status.HTTP_409_CONFLICT,
                                     "This conversation is too long. Please submit it and start a new one."),
    intake_service.NothingToSubmit: (status.HTTP_422_UNPROCESSABLE_CONTENT,
                                     "Please describe your concern before submitting."),
    intake_service.AlreadyConfirmed: (status.HTTP_409_CONFLICT, "This intake is already confirmed."),
    intake_service.InvalidTranscription: (status.HTTP_422_UNPROCESSABLE_CONTENT,
                                          "That voice transcription cannot be used for this message."),
    intake_service.UnknownDepartment: (status.HTTP_422_UNPROCESSABLE_CONTENT,
                                       "Choose an active department."),
    intake_service.EnglishTextNeeded: (status.HTTP_422_UNPROCESSABLE_CONTENT,
                                       "Enter the English version of the patient's words before confirming."),
}


def _fail(exc: Exception):
    code, msg = _ERRORS[type(exc)]
    raise HTTPException(status_code=code, detail=msg) from None


def _my_patient(user: User = Depends(patient_only), db: Session = Depends(get_db)) -> Patient:
    patient = patient_service.get_for_user(db, user)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No patient profile for this account")
    return patient


def _my_conversation(conversation_id: uuid.UUID, patient: Patient = Depends(_my_patient),
                     db: Session = Depends(get_db)) -> Conversation:
    conv = intake_service.get_own_conversation(db, conversation_id, patient)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conv


# ---------- patient ----------

@router.post("/conversations", response_model=ConversationOut)
def open_conversation(response: Response, patient: Patient = Depends(_my_patient),
                      user: User = Depends(patient_only), db: Session = Depends(get_db)):
    """Resume the patient's open conversation, or start one (201)."""
    try:
        conv, created = intake_service.open_conversation(db, patient, user)
    except intake_service.ConsentMissing as e:
        _fail(e)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return conv


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def read_conversation(conv: Conversation = Depends(_my_conversation)):
    return conv


@router.post("/conversations/{conversation_id}/messages", response_model=MessageExchange,
             status_code=status.HTTP_201_CREATED)
def send_message(body: MessageCreate, conv: Conversation = Depends(_my_conversation),
                 db: Session = Depends(get_db)) -> MessageExchange:
    try:
        mine, ack = intake_service.add_message(db, conv, body)
    except (intake_service.ConversationClosed, intake_service.TooManyMessages,
            intake_service.ConsentMissing, intake_service.InvalidTranscription) as e:
        _fail(e)
    return MessageExchange(patient_message=MessageOut.model_validate(mine),
                           assistant_message=MessageOut.model_validate(ack))


@router.post("/conversations/{conversation_id}/transcriptions", response_model=TranscriptionOut,
             status_code=status.HTTP_201_CREATED)
async def transcribe(audio: UploadFile = File(...), language: ContentLanguage = Form(ContentLanguage.EN),
                     conv: Conversation = Depends(_my_conversation),
                     user: User = Depends(patient_only), db: Session = Depends(get_db)):
    """Upload a recording; returns the machine transcript for the patient to review.

    Nothing is added to the conversation yet: the patient sends the (possibly
    edited) text as a voice_server message referencing this transcription.
    """
    limit = get_settings().audio_max_bytes
    data = await audio.read(limit + 1)  # never read more than the limit allows
    from starlette.concurrency import run_in_threadpool

    try:
        return await run_in_threadpool(speech_service.transcribe_upload, db, conv, user, data,
                                       audio.content_type, language)
    except AudioRejected as e:
        raise HTTPException(e.status, str(e)) from None
    except speech_service.TranscriptionFailed as e:
        raise HTTPException(e.status, str(e)) from None
    except speech_service.ConversationNotOpen:
        _fail(intake_service.ConversationClosed())
    except speech_service.ConsentMissing:
        _fail(intake_service.ConsentMissing())


@router.post("/conversations/{conversation_id}/submit", response_model=IntakePatientView,
             status_code=status.HTTP_201_CREATED)
def submit_conversation(conv: Conversation = Depends(_my_conversation),
                        user: User = Depends(patient_only), db: Session = Depends(get_db)):
    try:
        return intake_service.submit(db, conv, user)
    except (intake_service.ConversationClosed, intake_service.NothingToSubmit) as e:
        _fail(e)


@router.get("/patients/me/intakes", response_model=list[IntakePatientView])
def my_intakes(patient: Patient = Depends(_my_patient), db: Session = Depends(get_db)):
    return intake_service.list_for_patient(db, patient)


# ---------- staff ----------

def _intake_or_404(intake_id: uuid.UUID, db: Session) -> IntakeRecord:
    intake = intake_service.get(db, intake_id)
    if intake is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Intake not found")
    return intake


@router.get("/intakes", response_model=IntakeList)
def list_intakes(review_status: ReviewStatus | None = None,
                 limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                 _: User = Depends(staff_only), db: Session = Depends(get_db)) -> IntakeList:
    return intake_service.list_for_staff(db, review_status=review_status, limit=limit, offset=offset)


def _assigned_intake_or_404(intake_id: uuid.UUID, doctor: User, db: Session) -> IntakeRecord:
    """A doctor may read an intake only when a visit assigned to THEM points at it (404 otherwise)."""
    intake = _intake_or_404(intake_id, db)
    assigned = db.scalar(select(QueueEntry.id).where(QueueEntry.intake_id == intake.id,
                                                    QueueEntry.doctor_user_id == doctor.id).limit(1))
    if assigned is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Intake not found")
    return intake


@router.get("/doctor/intakes/{intake_id}", response_model=IntakeStaffView)
def doctor_read_intake(intake_id: uuid.UUID, doctor: User = Depends(doctor_only),
                       db: Session = Depends(get_db)) -> IntakeStaffView:
    """Read-only view of an intake for the doctor it is assigned to (symptoms, priority, evidence)."""
    return intake_service.staff_view(db, _assigned_intake_or_404(intake_id, doctor, db), doctor)


@router.get("/doctor/intakes/{intake_id}/history", response_model=HistoryOut)
def doctor_intake_history(intake_id: uuid.UUID, limit: int = Query(5, ge=1, le=50), offset: int = Query(0, ge=0),
                          doctor: User = Depends(doctor_only), db: Session = Depends(get_db)) -> HistoryOut:
    """Earlier encounters of the same patient, for the assigned doctor (audited like the staff view)."""
    intake = _assigned_intake_or_404(intake_id, doctor, db)
    audit_service.record(db, "patient.history_viewed", actor_user_id=doctor.id, target_type="patient",
                         target_id=intake.patient_id, details={"intake_id": str(intake.id)})
    db.commit()
    return history_service.for_intake(db, intake, limit=limit, offset=offset)


@router.get("/intakes/{intake_id}", response_model=IntakeStaffView)
def read_intake(intake_id: uuid.UUID, staff: User = Depends(staff_only),
                db: Session = Depends(get_db)) -> IntakeStaffView:
    return intake_service.staff_view(db, _intake_or_404(intake_id, db), staff)


@router.patch("/intakes/{intake_id}", response_model=IntakeStaffView)
def correct_intake(intake_id: uuid.UUID, body: IntakeCorrection, staff: User = Depends(staff_only),
                   db: Session = Depends(get_db)) -> IntakeStaffView:
    intake = intake_service.correct(db, _intake_or_404(intake_id, db), staff, body.final_text, body.reason)
    return intake_service.staff_view(db, intake, staff)


@router.patch("/intakes/{intake_id}/priority", response_model=IntakeStaffView)
def change_priority(intake_id: uuid.UUID, body: PriorityChange, staff: User = Depends(staff_only),
                    db: Session = Depends(get_db)) -> IntakeStaffView:
    """Staff set Urgent / Normal. A reason is required; the change is audited and kept as a revision."""
    intake = _intake_or_404(intake_id, db)
    try:
        priority_service.set_by_staff(db, intake, staff, body.priority, body.reason)
    except priority_service.PriorityUnchanged:
        raise HTTPException(status.HTTP_409_CONFLICT, "The priority is already set to that value by staff.") from None
    return intake_service.staff_view(db, intake, staff)


@router.post("/intakes/{intake_id}/translate", response_model=IntakeStaffView)
def retry_translation(intake_id: uuid.UUID, staff: User = Depends(staff_only),
                      db: Session = Depends(get_db)) -> IntakeStaffView:
    """Run the local translation model again for a pending/failed intake."""
    intake = _intake_or_404(intake_id, db)
    if not translation_service.needs_translation(intake):
        raise HTTPException(status.HTTP_409_CONFLICT, "This intake does not need translation.")
    intake = translation_service.translate_intake(db, intake, staff)
    return intake_service.staff_view(db, intake, staff)


class AnalyseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["english_text", "final_text"] = "final_text"


@router.post("/intakes/{intake_id}/analyse", response_model=IntakeStaffView)
def analyse_intake(intake_id: uuid.UUID, body: AnalyseRequest, staff: User = Depends(staff_only),
                   db: Session = Depends(get_db)) -> IntakeStaffView:
    """Re-run the rule-based extraction (e.g. on the staff-reviewed text)."""
    intake = _intake_or_404(intake_id, db)
    try:
        analysis_service.analyse(db, intake, source=body.source, actor=staff)
    except analysis_service.NoTextToAnalyse:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "There is no English text to analyse yet.") from None
    db.refresh(intake)
    return intake_service.staff_view(db, intake, staff)


@router.get("/intakes/{intake_id}/history", response_model=HistoryOut)
def intake_history(intake_id: uuid.UUID, limit: int = Query(5, ge=1, le=50), offset: int = Query(0, ge=0),
                   staff: User = Depends(staff_only), db: Session = Depends(get_db)) -> HistoryOut:
    """Earlier encounters of the SAME patient as this intake (matched by record id), for review."""
    intake = _intake_or_404(intake_id, db)
    audit_service.record(db, "patient.history_viewed", actor_user_id=staff.id, target_type="patient",
                         target_id=intake.patient_id, details={"intake_id": str(intake.id)})
    db.commit()
    return history_service.for_intake(db, intake, limit=limit, offset=offset)


_SYMPTOM_ERRORS = {
    symptom_service.SymptomNotFound: (status.HTTP_404_NOT_FOUND, "Symptom not found"),
    symptom_service.SymptomSuperseded: (status.HTTP_409_CONFLICT,
                                        "This symptom is from an older analysis. Reload the intake."),
    symptom_service.IntakeLocked: (status.HTTP_409_CONFLICT, "This intake is already confirmed."),
    symptom_service.InvalidSymptom: (status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid symptom details."),
}


@router.post("/intakes/{intake_id}/symptoms/{symptom_id}/review", response_model=SymptomOut)
def review_symptom(intake_id: uuid.UUID, symptom_id: uuid.UUID, body: SymptomReview,
                   staff: User = Depends(staff_only), db: Session = Depends(get_db)):
    """Confirm, reject or correct one AI-extracted symptom. The AI reading itself is never edited."""
    intake = _intake_or_404(intake_id, db)
    try:
        return symptom_service.review(db, intake, symptom_id, staff, action=body.action, term=body.term,
                                      status=body.status.value if body.status else None, note=body.note)
    except tuple(_SYMPTOM_ERRORS) as e:
        code, msg = _SYMPTOM_ERRORS[type(e)]
        raise HTTPException(status_code=code, detail=msg) from None


@router.post("/intakes/{intake_id}/symptoms", response_model=SymptomOut, status_code=status.HTTP_201_CREATED)
def add_symptom(intake_id: uuid.UUID, body: SymptomAdd, staff: User = Depends(staff_only),
                db: Session = Depends(get_db)):
    """Staff record a symptom the system missed."""
    intake = _intake_or_404(intake_id, db)
    try:
        return symptom_service.add_staff_symptom(db, intake, staff, term=body.term, status=body.status.value,
                                                 evidence_text=body.evidence_text, note=body.note)
    except tuple(_SYMPTOM_ERRORS) as e:
        code, msg = _SYMPTOM_ERRORS[type(e)]
        raise HTTPException(status_code=code, detail=msg) from None


@router.post("/intakes/{intake_id}/confirm", response_model=IntakeStaffView)
def confirm_intake(intake_id: uuid.UUID, body: IntakeConfirm, staff: User = Depends(staff_only),
                   db: Session = Depends(get_db)) -> IntakeStaffView:
    try:
        intake = intake_service.confirm(db, _intake_or_404(intake_id, db), staff,
                                        body.final_text, body.reason, body.department_id)
    except (intake_service.AlreadyConfirmed, intake_service.EnglishTextNeeded,
            intake_service.UnknownDepartment) as e:
        _fail(e)
    return intake_service.staff_view(db, intake, staff)
