"""User-related request/response shapes. password_hash is never part of any output."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.config import get_settings
from app.core.enums import DoctorVerification, Role, UiLanguage
from app.core.security import normalize_email, normalize_phone

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    phone: str | None
    full_name: str
    role: Role
    ui_language: UiLanguage
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    # Doctors only: pending / approved / rejected. The server enforces it on every doctor endpoint.
    verification_status: DoctorVerification | None = None


class PreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ui_language: UiLanguage


class ContactFields(BaseModel):
    """Email and/or phone, normalised. At least one is required."""

    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=24)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, v: str | None) -> str | None:
        return normalize_email(v) if v else None

    @field_validator("phone")
    @classmethod
    def _norm_phone(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        norm = normalize_phone(v, get_settings().default_phone_country_code)
        if norm is None:
            raise ValueError("Enter a valid phone number (8-15 digits).")
        return norm

    @model_validator(mode="after")
    def _need_one(self):
        if not self.email and not self.phone:
            raise ValueError("Provide an email address or a phone number.")
        return self


class AdminUserCreate(ContactFields):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    role: Role
    ui_language: UiLanguage = UiLanguage.EN

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Full name is required.")
        return v


class UserList(BaseModel):
    items: list[UserOut]
    total: int
