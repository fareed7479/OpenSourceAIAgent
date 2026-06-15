import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.assignment import Assignment
from app.schemas.assignment import AssignmentCreate, AssignmentResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services.assignment import request_issue_assignment, monitor_assignments_task

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/request", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def request_assignment(
    payload: AssignmentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request assignment for an open repository issue.
    Posts comment on GitHub and initiates monitoring.
    """
    try:
        assignment = request_issue_assignment(
            issue_id=payload.issue_id,
            user_id=current_user.id
        )
        
        # Trigger assignment monitoring immediately in the background
        background_tasks.add_task(monitor_assignments_task)
        
        return assignment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit assignment request: {str(e)}"
        )

@router.get("", response_model=List[AssignmentResponse])
def list_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all issue assignment requests for the current user."""
    assignments = db.query(Assignment).filter(Assignment.user_id == current_user.id).all()
    return assignments

@router.post("/monitor", status_code=status.HTTP_200_OK)
def trigger_monitoring(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Manually force-trigger polling monitoring of all active assignment requests.
    """
    background_tasks.add_task(monitor_assignments_task)
    return {"message": "Assignment monitoring polling scheduled."}
