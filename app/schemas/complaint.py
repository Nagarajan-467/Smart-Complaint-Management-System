"""
Pydantic schemas for Complaint entity.
"""

from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.models.complaint import ComplaintCategory, ComplaintPriority, ComplaintStatus

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic pagination response wrapper."""
    items: list[T]
    total: int
    page: int
    size: int


class ComplaintBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    location: Optional[str] = Field(None, max_length=200)
    category: ComplaintCategory = ComplaintCategory.GENERAL
    priority: ComplaintPriority = ComplaintPriority.LOW


class ComplaintCreate(ComplaintBase):
    pass


class ComplaintUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    location: Optional[str] = Field(None, max_length=200)
    category: Optional[ComplaintCategory] = None
    priority: Optional[ComplaintPriority] = None
    status: Optional[ComplaintStatus] = None
    department_id: Optional[int] = None


class ComplaintAssign(BaseModel):
    assigned_to: int = Field(..., description="ID of the staff/admin to assign the complaint to")


class ComplaintResponse(ComplaintBase):
    id: int
    status: ComplaintStatus
    user_id: int
    department_id: Optional[int] = None
    assigned_to: Optional[int] = None
    
    # AI/Smart fields
    duplicate_of: Optional[int] = None
    cluster_id: Optional[int] = None
    estimated_resolution_hours: Optional[float] = None
    escalation_level: int
    
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
