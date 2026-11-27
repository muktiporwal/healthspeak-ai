"""Doctor registration and verification shapes. There is deliberately NO role field anywhere here."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import get_settings
from app.core.enums import DoctorVerification, UiLanguage
from app.core.security import normalize_email, normalize_phone
from app.schemas.user import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, UserOut


def _clean(v: str) -> str:
    v = " ".join(v.split())
    if not v:
        raise ValueError("This field is required.")
    return v


class DoctorRegister(BaseModel):
    """Public doctor sign-up. The account is created as a PENDING doctor; the client cannot choose a role."""

    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=24)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    qualification: str = Field(min_length=2, max_length=120)  # e.g. MBBS, MD (Medicine)
    specialization: str = Field(min_length=2, max_length=120)
    registration_number: str = Field(min_length=3, max_length=64)
    registration_authority: str = Field(min_length=2, max_length=120)  # state medical council
    hospital_name: str = Field(min_length=2, max_length=160)
    years_experience: int = Field(ge=0, le=70)
    ui_language: UiLanguage | None = None

    @field_validator("full_name", "qualification", "specialization", "registration_authority", "hospital_name")
    @classmethod
    def _tidy(cls, v: str) -> str:
        return _clean(v)

    @field_validator("registration_number")
    @classmethod
    def _tidy_number(cls, v: str) -> str:
        v = _clean(v).upper()
        if not all(c.isalnum() or c in "/-. " for c in v):
            raise ValueError("Use letters, digits and / - . only.")
        return v

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str) -> str:
        return normalize_email(v)

    @field_validator("phone")
    @classmethod
    def _norm_phone(cls, v: str) -> str:
        norm = normalize_phone(v, get_settings().default_phone_country_code)
        if norm is None:
            raise ValueError("Enter a valid phone number (8-15 digits).")
        return norm


class DoctorProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    qualification: str
    specialization: str
    registration_number: str
    registration_authority: str
    hospital_name: str
    years_experience: int
    verification_status: DoctorVerification
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime


class DoctorApplicationOut(BaseModel):
    """What an administrator reviews. Only profile fields, never the password hash."""

    user: UserOut
    profile: DoctorProfileOut


class DoctorApplicationList(BaseModel):
    items: list[DoctorApplicationOut]
    total: int


class DoctorDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Required when rejecting (shown to the doctor); optional note when approving.
    note: str | None = Field(default=None, max_length=500)


class DoctorStatusOut(BaseModel):
    """The signed-in doctor's own verification state."""

    status: DoctorVerification
    profile: DoctorProfileOut | None
    user_id: uuid.UUID
