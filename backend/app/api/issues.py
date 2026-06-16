import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.encryption import decrypt_token
from app.models.issue import Issue
from app.models.repository import Repository
from app.schemas.issue import IssueResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services.discovery import discover_repository_issues_task

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", response_model=List[IssueResponse])
def list_issues(
    repository_id: Optional[str] = Query(None, description="Filter issues by repository ID"),
    difficulty: Optional[str] = Query(None, description="Filter by easy, medium, or hard"),
    label: Optional[str] = Query(None, description="Filter by label"),
    search: Optional[str] = Query(None, description="Search search term in title or description"),
    state: Optional[str] = Query("open", description="Filter by state (open, closed, or all)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List issues across all user repositories, sorted by suitability score (descending).
    """
    query = db.query(Issue).join(Repository).filter(Repository.user_id == current_user.id)
    
    # Apply state filter
    if state and state.lower() == "closed":
        query = query.filter(Issue.status == "closed")
    elif state and state.lower() == "all":
        # Fetch both open and closed issues
        pass
    else:
        # Default to open
        query = query.filter(Issue.status == "open")
        
    if repository_id:
        query = query.filter(Issue.repository_id == repository_id)
        
    if difficulty:
        query = query.filter(Issue.difficulty == difficulty)
        
    if label:
        # Check if the labels JSON array contains the label
        query = query.filter(Issue.labels.like(f"%{label}%"))
        
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Issue.title.like(search_filter)) | 
            (Issue.description.like(search_filter))
        )
        
    # Order by Score descending (highest priority recommended first)
    issues = query.order_by(Issue.score.desc()).all()
    return issues

@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue(
    issue_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details of a specific issue."""
    issue = db.query(Issue).join(Repository).filter(
        Issue.id == issue_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found."
        )
    return issue

@router.post("/scan/{repo_id}", status_code=status.HTTP_202_ACCEPTED)
def trigger_issue_scan(
    repo_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger an issue discovery scan for a repository.
    """
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )
        
    decrypted_token = decrypt_token(current_user.access_token)
    is_mock = current_user.github_id.startswith("mock-") or decrypted_token == "mock-github-access-token"
    
    background_tasks.add_task(
        discover_repository_issues_task,
        repo_id=repo.id,
        github_token=decrypted_token if not is_mock else None
    )
    
    return {"message": "Issue scan triggered successfully."}
