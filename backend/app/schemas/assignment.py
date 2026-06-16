from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.schemas.issue import IssueResponse

class AssignmentCreate(BaseModel):
    issue_id: str

class AssignmentResponse(BaseModel):
    id: str
    user_id: str
    issue_id: str
    status: str
    request_comment_id: Optional[int] = None
    comment_url: Optional[str] = None
    issue_url: Optional[str] = None
    repository_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    issue: Optional[IssueResponse] = None

    class Config:
        from_attributes = True
