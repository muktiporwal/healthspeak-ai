"""doctor registration details and administrator verification

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-28 09:00:00.000000+00:00

Additive only: one NEW table, doctor_profiles. No existing table or column changes and no row is touched.
Doctors that already exist (created by an administrator, e.g. the demo doctor) get no row and stay verified.
Downgrade drops only the new table (refuses nothing: the table holds only self-registered doctors' details).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0014'
down_revision: Union[str, None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "doctor_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("qualification", sa.String(length=120), nullable=False),
        sa.Column("specialization", sa.String(length=120), nullable=False),
        sa.Column("registration_number", sa.String(length=64), nullable=False),
        sa.Column("registration_authority", sa.String(length=120), nullable=False),
        sa.Column("hospital_name", sa.String(length=160), nullable=False),
        sa.Column("years_experience", sa.Integer(), nullable=False),
        sa.Column("verification_status", sa.String(length=10), server_default="pending", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("verification_status IN ('pending', 'approved', 'rejected')",
                           name=op.f("ck_doctor_profiles_verification_status_valid")),
        sa.CheckConstraint("years_experience BETWEEN 0 AND 70",
                           name=op.f("ck_doctor_profiles_years_experience_range")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_doctor_profiles_user_id_users"),
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"],
                                name=op.f("fk_doctor_profiles_reviewed_by_user_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_doctor_profiles")),
        sa.UniqueConstraint("registration_authority", "registration_number",
                            name=op.f("uq_doctor_profiles_registration_unique")),
    )
    op.create_index(op.f("ix_doctor_profiles_user_id"), "doctor_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_doctor_profiles_user_id"), table_name="doctor_profiles")
    op.drop_table("doctor_profiles")
