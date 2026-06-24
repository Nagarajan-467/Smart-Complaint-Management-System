"""
API endpoints for Complaint management.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.database import get_db
from app.models.complaint import ComplaintCategory, ComplaintPriority, ComplaintStatus
from app.models.user import User, UserRole
from app.schemas.complaint import (
    ComplaintAssign,
    ComplaintCreate,
    ComplaintResponse,
    ComplaintUpdate,
    PaginatedResponse,
)
from app.services import complaint_service, categorization_service, priority_service, duplicate_detection_service, estimation_service, clustering_service

router = APIRouter(prefix="/api/v1/complaints", tags=["Complaints"])


@router.post("/run-clustering", status_code=status.HTTP_200_OK)
def trigger_clustering(
    current_user: Annotated[User, Depends(require_roles([UserRole.ADMIN]))],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Run the AI clustering engine on all unresolved complaints.
    This groups similar widespread issues under shared cluster_ids.
    Requires ADMIN privileges.
    """
    clustered_complaints = clustering_service.run_clustering(db)
    return {
        "message": "Clustering completed successfully.",
        "complaints_clustered": len(clustered_complaints)
    }


@router.post("/", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def create_complaint(
    complaint_in: ComplaintCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Create a new complaint with smart features (Categorization, Priority, Duplicate Detection, Estimation)."""
    # Smart Auto-Categorization
    if complaint_in.category == ComplaintCategory.GENERAL:
        predicted_category = categorization_service.predict_category(
            title=complaint_in.title, 
            description=complaint_in.description
        )
        complaint_in.category = predicted_category

    # Smart Priority Detection
    predicted_priority = priority_service.predict_priority(
        title=complaint_in.title,
        description=complaint_in.description,
        current_priority=complaint_in.priority
    )
    complaint_in.priority = predicted_priority
    
    # NLP Duplicate Detection
    duplicate_id = duplicate_detection_service.detect_duplicate(
        db=db,
        title=complaint_in.title,
        description=complaint_in.description,
        category=complaint_in.category,
        threshold=0.75
    )
    
    # Smart AI Estimation
    estimated_hours = estimation_service.estimate_resolution_hours(
        db=db,
        category=complaint_in.category,
        priority=complaint_in.priority
    )

    return complaint_service.create_complaint(
        db=db, 
        complaint_in=complaint_in, 
        user_id=current_user.id, 
        duplicate_of=duplicate_id,
        estimated_resolution_hours=estimated_hours
    )


@router.post("/{complaint_id}/detect-duplicate", response_model=ComplaintResponse)
def run_duplicate_detection(
    complaint_id: int,
    current_user: Annotated[User, Depends(require_roles([UserRole.ADMIN, UserRole.STAFF]))],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Manually run duplicate detection for an existing complaint.
    Returns the complaint with updated duplicate_of field if a match is found.
    """
    complaint = complaint_service.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    duplicate_id = duplicate_detection_service.detect_duplicate(
        db=db,
        title=complaint.title,
        description=complaint.description,
        category=complaint.category,
        threshold=0.75
    )
    
    # Do not link to itself
    if duplicate_id and duplicate_id != complaint.id:
        complaint.duplicate_of = duplicate_id
        db.commit()
        db.refresh(complaint)
        
    return complaint


@router.get("/", response_model=PaginatedResponse[ComplaintResponse])
def list_complaints(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: Optional[ComplaintStatus] = None,
    category: Optional[ComplaintCategory] = None,
    priority: Optional[ComplaintPriority] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at_desc", pattern="^(created_at_desc|created_at_asc|priority|status)$")
):
    """
    List complaints with pagination, filtering, search, and sorting.
    Students only see their own complaints. Staff/Admin see all.
    """
    skip = (page - 1) * size
    
    # Restrict visibility for students
    filter_user_id = current_user.id if current_user.role == UserRole.STUDENT else None
    
    items, total = complaint_service.get_complaints(
        db=db,
        skip=skip,
        limit=size,
        user_id=filter_user_id,
        status=status,
        category=category,
        priority=priority,
        search_query=search,
        sort_by=sort_by
    )
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size
    }


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(
    complaint_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get a specific complaint by ID."""
    complaint = complaint_service.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # Security: Students can only view their own complaints
    if current_user.role == UserRole.STUDENT and complaint.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this complaint")
        
    return complaint


@router.put("/{complaint_id}", response_model=ComplaintResponse)
def update_complaint(
    complaint_id: int,
    update_data: ComplaintUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Update a complaint.
    Students can only update if it is PENDING.
    """
    complaint = complaint_service.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    if current_user.role == UserRole.STUDENT:
        if complaint.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this complaint")
        if complaint.status != ComplaintStatus.PENDING:
            raise HTTPException(status_code=400, detail="Cannot update a complaint that is already being processed")
            
    return complaint_service.update_complaint(db, complaint, update_data)


@router.delete("/{complaint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_complaint(
    complaint_id: int,
    current_user: Annotated[User, Depends(require_roles([UserRole.ADMIN]))],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Delete a complaint. Only admins can do this.
    """
    complaint = complaint_service.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    complaint_service.delete_complaint(db, complaint)


@router.post("/{complaint_id}/assign", response_model=ComplaintResponse)
def assign_complaint(
    complaint_id: int,
    assign_data: ComplaintAssign,
    current_user: Annotated[User, Depends(require_roles([UserRole.ADMIN, UserRole.STAFF]))],
    db: Annotated[Session, Depends(get_db)]
):
    """
    Assign a complaint to a staff member. Requires Staff/Admin role.
    """
    complaint = complaint_service.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    return complaint_service.assign_complaint(db, complaint, assign_data.assigned_to)
