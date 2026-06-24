"""
Models package — imports all ORM models so they are registered
with SQLAlchemy's Base.metadata for table creation and migrations.
"""

from app.models.department import Department
from app.models.user import User, UserRole
from app.models.complaint import Complaint, ComplaintCategory, ComplaintPriority, ComplaintStatus
from app.models.feedback import Feedback
from app.models.escalation_log import EscalationLog

__all__ = [
    "Department",
    "User",
    "UserRole",
    "Complaint",
    "ComplaintCategory",
    "ComplaintPriority",
    "ComplaintStatus",
    "Feedback",
    "EscalationLog",
]
