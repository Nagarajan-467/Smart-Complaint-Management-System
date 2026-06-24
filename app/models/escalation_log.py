"""
EscalationLog model — immutable audit trail of every escalation event.
One row is written each time a complaint's escalation_level advances.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EscalationLog(Base):
    __tablename__ = "escalation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complaint_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    complaint: Mapped["Complaint"] = relationship(  # noqa: F821
        "Complaint", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<EscalationLog(id={self.id}, complaint_id={self.complaint_id}, "
            f"level={self.escalation_level}, reason='{self.reason}')>"
        )
