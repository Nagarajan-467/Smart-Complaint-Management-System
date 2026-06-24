"""
Department model — represents organizational departments
that complaints can be assigned to.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User", back_populates="department", lazy="selectin"
    )
    complaints: Mapped[list["Complaint"]] = relationship(  # noqa: F821
        "Complaint", back_populates="department", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Department(id={self.id}, name='{self.name}')>"
