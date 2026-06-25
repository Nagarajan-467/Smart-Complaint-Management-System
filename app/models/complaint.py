"""
Complaint model — the core entity of the system.
Tracks complaints from creation through resolution.
"""
# imort standard libraries
import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

## Complaint Classification Enums
class ComplaintCategory(str, enum.Enum):
    """Categories for automatic complaint classification."""
    NETWORK = "network"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    HOSTEL = "hostel"
    CLASSROOM = "classroom"
    GENERAL = "general"

# Complaint Priority and Status Enums
class ComplaintPriority(str, enum.Enum):
    """Priority levels for complaints."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplaintStatus(str, enum.Enum):
    """Lifecycle status of a complaint."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"

## Complaint ORM Model
class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── Classification ────────────────────────────────────────────────────
    category: Mapped[ComplaintCategory] = mapped_column(
        Enum(ComplaintCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ComplaintCategory.GENERAL,
        index=True,
    )
    priority: Mapped[ComplaintPriority] = mapped_column(
        Enum(ComplaintPriority, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ComplaintPriority.LOW,
        index=True,
    )
    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ComplaintStatus.PENDING,
        index=True,
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_to: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # ── Smart Features ────────────────────────────────────────────────────
    duplicate_of: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("complaints.id", ondelete="SET NULL"), nullable=True
    )
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    estimated_resolution_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    escalation_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Resolution ────────────────────────────────────────────────────────
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────
    complainant: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="complaints_filed",
        foreign_keys=[user_id],
        lazy="selectin",
    )
    assignee: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        back_populates="complaints_assigned",
        foreign_keys=[assigned_to],
        lazy="selectin",
    )
    department: Mapped["Department | None"] = relationship(  # noqa: F821
        "Department",
        back_populates="complaints",
        lazy="selectin",
    )
    duplicate_original: Mapped["Complaint | None"] = relationship(
        "Complaint",
        remote_side="Complaint.id",
        foreign_keys=[duplicate_of],
        lazy="selectin",
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(  # noqa: F821
        "Feedback",
        back_populates="complaint",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ── Composite Indexes ─────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_complaints_status_priority", "status", "priority"),
        Index("ix_complaints_user_status", "user_id", "status"),
        Index("ix_complaints_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Complaint(id={self.id}, title='{self.title[:30]}', "
            f"status='{self.status.value}', priority='{self.priority.value}')>"
        )
