from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class PullRequestResponse(BaseModel):
    id: str
    agent_run_id: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    github_pr_id: Optional[int] = None
    status: str
    files_changed: List[str]
    tests_passed: Optional[bool] = None
    review_status: Optional[str] = None
    approval_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PullRequestApproval(BaseModel):
    approved: bool
    feedback: Optional[str] = None
