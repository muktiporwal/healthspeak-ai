"""Professional details a doctor submitted when registering, and the administrator's decision on them.

A doctor who registers themselves starts as PENDING and has no doctor access until an administrator
approves. Doctors created by an administrator (e.g. the seeded demo doctor) have no row here and count as
verified, because an authorised administrator created the account directly.
The submitted details are claims, not proof: the administrator is expected to check the registration
number with the named council before approving.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DoctorVerification, sql_in_list
from app.database.base import Base
from app.database.models.mixins import Timestamps, UuidPk


class DoctorProfile(UuidPk, Timestamps, Base):
    __tablename__ = "doctor_profiles"
    __table_args__ = (
        CheckConstraint(f"verification_status IN ({sql_in_list(DoctorVerification)})",
                        name="verification_status_valid"),
        CheckConstraint("years_experience BETWEEN 0 AND 70", name="years_experience_range"),
        # The same registration number cannot be used for two accounts.
        UniqueConstraint("registration_authority", "registration_number", name="uq_doctor_profiles_registration_unique"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    qualification: Mapped[str] = mapped_column(String(120))
    specialization: Mapped[str] = mapped_column(String(120))
    registration_number: Mapped[str] = mapped_column(String(64))
    registration_authority: Mapped[str] = mapped_column(String(120))  # state medical council etc.
    hospital_name: Mapped[str] = mapped_column(String(160))
    years_experience: Mapped[int] = mapped_column(Integer)

    verification_status: Mapped[str] = mapped_column(
        String(10), default=DoctorVerification.PENDING.value, server_default=DoctorVerification.PENDING.value)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)  # reason shown to the doctor when rejected

    user = relationship("User", foreign_keys=[user_id], back_populates="doctor_profile")
