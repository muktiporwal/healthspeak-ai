"""D1 User Accounts and Roles."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DoctorVerification, Role, UiLanguage, sql_in_list
from app.database.base import Base
from app.database.models.mixins import Timestamps, UuidPk


class User(UuidPk, Timestamps, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"role IN ({sql_in_list(Role)})", name="role_valid"),
        CheckConstraint(f"ui_language IN ({sql_in_list(UiLanguage)})", name="ui_language_valid"),
        CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="email_or_phone"),
    )

    # Stored lower-case. Either email or phone (or both) identifies the account.
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    # Stored normalised as +<country><number>, e.g. +919876543210.
    phone: Mapped[str | None] = mapped_column(String(16), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16))
    ui_language: Mapped[str] = mapped_column(
        String(8), default=UiLanguage.EN.value, server_default=UiLanguage.EN.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))

    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set only when the account holder proved they receive SMS on `phone` (one-time code).
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Only self-registered doctors have one (see models/doctor.py).
    doctor_profile = relationship("DoctorProfile", foreign_keys="DoctorProfile.user_id", uselist=False,
                                  back_populates="user", lazy="joined")

    @property
    def verification_status(self) -> str | None:
        """None for non-doctors. A doctor is 'approved' unless a registration is still pending/rejected.
        (Doctors an administrator created directly have no profile row and are trusted.)"""
        if self.role != Role.DOCTOR.value:
            return None
        return self.doctor_profile.verification_status if self.doctor_profile else DoctorVerification.APPROVED.value
