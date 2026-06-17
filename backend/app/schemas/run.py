from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel
from app.schemas.pr import PullRequestResponse

class AgentLogResponse(BaseModel):
    id: str
    stage: str
    message: str
    data: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AgentRunCreate(BaseModel):
    issue_id: str
    provider: str  # gemini, claude, etc.

class RepositorySummary(BaseModel):
    id: str
    name: str
    owner: str
    url: str

    class Config:
        from_attributes = True

class IssueSummary(BaseModel):
    id: str
    number: int
    title: str
    url: str

    class Config:
        from_attributes = True

class AgentRunResponse(BaseModel):
    id: str
    repository_id: str
    issue_id: str
    user_id: str
    branch_name: str
    provider: str
    status: str
    actual_provider: Optional[str] = None
    fallback_provider: Optional[str] = None
    fallback_reason: Optional[str] = None
    code_diff: Optional[str] = None
    commit_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    logs: List[AgentLogResponse] = []
    pull_request: Optional[PullRequestResponse] = None
    repository: Optional[RepositorySummary] = None
    issue: Optional[IssueSummary] = None

    class Config:
        from_attributes = True

