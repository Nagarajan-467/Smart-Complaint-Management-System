"""
Feedback model — allows users to rate and comment on
resolved complaints.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complaint_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    complaint: Mapped["Complaint"] = relationship(  # noqa: F821
        "Complaint", back_populates="feedbacks", lazy="selectin"
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="feedbacks", lazy="selectin"
    )

    # ── Constraints ───────────────────────────────────────────────────────
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating_range"),
        UniqueConstraint("complaint_id", "user_id", name="uq_feedback_complaint_user"),
    )

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, complaint_id={self.complaint_id}, rating={self.rating})>"
