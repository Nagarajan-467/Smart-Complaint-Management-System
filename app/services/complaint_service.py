"""
Service layer for Complaint operations.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, ComplaintCategory, ComplaintPriority, ComplaintStatus
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate


def create_complaint(
    db: Session, 
    complaint_in: ComplaintCreate, 
    user_id: int, 
    duplicate_of: Optional[int] = None,
    estimated_resolution_hours: Optional[float] = None
) -> Complaint:
    db_complaint = Complaint(
        title=complaint_in.title,
        description=complaint_in.description,
        location=complaint_in.location,
        category=complaint_in.category,
        priority=complaint_in.priority,
        user_id=user_id,
        status=ComplaintStatus.PENDING,
        duplicate_of=duplicate_of,
        estimated_resolution_hours=estimated_resolution_hours
    )
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)
    return db_complaint


def get_complaint(db: Session, complaint_id: int) -> Optional[Complaint]:
    return db.get(Complaint, complaint_id)


def update_complaint(db: Session, db_complaint: Complaint, update_data: ComplaintUpdate) -> Complaint:
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # If status is changing to RESOLVED, set resolved_at automatically
    if "status" in update_dict and update_dict["status"] == ComplaintStatus.RESOLVED and db_complaint.status != ComplaintStatus.RESOLVED:
        db_complaint.resolved_at = datetime.now(timezone.utc)
        
    for field, value in update_dict.items():
        setattr(db_complaint, field, value)
        
    db.commit()
    db.refresh(db_complaint)
    return db_complaint


def delete_complaint(db: Session, db_complaint: Complaint) -> None:
    db.delete(db_complaint)
    db.commit()


def assign_complaint(db: Session, db_complaint: Complaint, user_id: int) -> Complaint:
    db_complaint.assigned_to = user_id
    db_complaint.status = ComplaintStatus.ASSIGNED
    db.commit()
    db.refresh(db_complaint)
    return db_complaint


def get_complaints(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    user_id: Optional[int] = None,
    status: Optional[ComplaintStatus] = None,
    category: Optional[ComplaintCategory] = None,
    priority: Optional[ComplaintPriority] = None,
    search_query: Optional[str] = None,
    sort_by: str = "created_at_desc"
) -> tuple[list[Complaint], int]:
    """
    Get paginated complaints with filtering, sorting, and text search.
    Returns (items, total_count).
    """
    stmt = select(Complaint)
    
    # ── Filters ──
    if user_id is not None:
        stmt = stmt.where(Complaint.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Complaint.status == status)
    if category is not None:
        stmt = stmt.where(Complaint.category == category)
    if priority is not None:
        stmt = stmt.where(Complaint.priority == priority)
        
    # ── Search ──
    if search_query:
        search_pattern = f"%{search_query}%"
        stmt = stmt.where(
            or_(
                Complaint.title.ilike(search_pattern),
                Complaint.description.ilike(search_pattern),
                Complaint.location.ilike(search_pattern)
            )
        )
        
    # ── Total Count ──
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt)
    
    # ── Sorting ──
    if sort_by == "created_at_desc":
        stmt = stmt.order_by(desc(Complaint.created_at))
    elif sort_by == "created_at_asc":
        stmt = stmt.order_by(Complaint.created_at)
    elif sort_by == "priority":
        # Sort by priority string value natively (can be improved with case statements later)
        stmt = stmt.order_by(desc(Complaint.priority))
    elif sort_by == "status":
        stmt = stmt.order_by(Complaint.status)
        
    # ── Pagination ──
    stmt = stmt.offset(skip).limit(limit)
    
    items = list(db.scalars(stmt).all())
    return items, total or 0
