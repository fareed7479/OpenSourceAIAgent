from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.schemas.issue import IssueResponse
from app.schemas.repository import RepositoryResponse

class AssignmentCreate(BaseModel):
    issue_id: str

class AssignmentResponse(BaseModel):
    id: str
    assignment_id: str
    user_id: str
    issue_id: str
    status: str
    assignment_status: str
    request_comment_id: Optional[int] = None
    comment_url: Optional[str] = None
    issue_url: Optional[str] = None
    repository_url: Optional[str] = None
    created_at: datetime
    assigned_at: datetime
    updated_at: datetime
    issue: Optional[IssueResponse] = None
    
    # New fields resolved from model properties
    issue_number: Optional[int] = None
    issue_title: Optional[str] = None
    repository_name: Optional[str] = None
    repository_owner: Optional[str] = None
    agent_run_id: Optional[str] = None
    workflow_status: Optional[str] = None
    current_stage: Optional[str] = None
    repository: Optional[RepositoryResponse] = None

    class Config:
        from_attributes = True

