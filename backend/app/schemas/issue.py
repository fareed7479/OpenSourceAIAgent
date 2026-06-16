from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class IssueResponse(BaseModel):
    id: str
    repository_id: str
    github_issue_id: int
    number: int
    title: str
    description: Optional[str] = None
    url: str
    labels: List[str]
    difficulty: str
    score: int
    ranking_reason: Optional[str] = None
    status: str
    assignment_status: str
    assignee_username: Optional[str] = None
    
    author_username: Optional[str] = None
    github_created_at: Optional[datetime] = None
    github_updated_at: Optional[datetime] = None
    comments_count: Optional[int] = 0
    meta_info: Optional[dict] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class IssueUpdate(BaseModel):
    difficulty: Optional[str] = None
    score: Optional[int] = None
    ranking_reason: Optional[str] = None
    status: Optional[str] = None
    assignment_status: Optional[str] = None
    assignee_username: Optional[str] = None
