"""
User model — supports Student, Staff, and Admin roles.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    """Enumeration of user roles in the system."""
    STUDENT = "student"
    STAFF = "staff"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.STUDENT,
        index=True,
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    department_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    department: Mapped["Department"] = relationship(  # noqa: F821
        "Department", back_populates="users", lazy="selectin"
    )
    complaints_filed: Mapped[list["Complaint"]] = relationship(  # noqa: F821
        "Complaint",
        back_populates="complainant",
        foreign_keys="Complaint.user_id",
        lazy="selectin",
    )
    complaints_assigned: Mapped[list["Complaint"]] = relationship(  # noqa: F821
        "Complaint",
        back_populates="assignee",
        foreign_keys="Complaint.assigned_to",
        lazy="selectin",
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(  # noqa: F821
        "Feedback", back_populates="user", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role.value}')>"
