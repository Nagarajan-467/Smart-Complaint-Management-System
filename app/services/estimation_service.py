"""
Estimated Resolution Time Service.
Calculates how long a complaint will take to resolve based on historical data.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, ComplaintCategory, ComplaintPriority, ComplaintStatus


def estimate_resolution_hours(
    db: Session, 
    category: ComplaintCategory, 
    priority: ComplaintPriority
) -> float:
    """
    Calculates the average resolution time in hours for a specific category and priority.
    Returns a fallback estimate if there isn't enough historical data.
    """
    stmt = select(Complaint).where(
        Complaint.status == ComplaintStatus.RESOLVED,
        Complaint.category == category,
        Complaint.priority == priority,
        Complaint.resolved_at.isnot(None)
    )
    resolved_complaints = list(db.scalars(stmt).all())
    
    if resolved_complaints:
        total_seconds = 0.0
        valid_count = 0
        
        for c in resolved_complaints:
            if c.resolved_at and c.created_at:
                delta = c.resolved_at - c.created_at
                total_seconds += delta.total_seconds()
                valid_count += 1
                
        if valid_count > 0:
            avg_seconds = total_seconds / valid_count
            # Convert to hours and round to 2 decimal places
            return round(avg_seconds / 3600.0, 2)
            
    # Fallback Rules if there's no historical data
    fallbacks = {
        ComplaintPriority.CRITICAL: 12.0,
        ComplaintPriority.HIGH: 24.0,
        ComplaintPriority.MEDIUM: 48.0,
        ComplaintPriority.LOW: 72.0
    }
    
    return fallbacks.get(priority, 48.0)
