from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel

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

class AgentRunResponse(BaseModel):
    id: str
    repository_id: str
    issue_id: str
    user_id: str
    branch_name: str
    provider: str
    status: str
    created_at: datetime
    updated_at: datetime
    logs: List[AgentLogResponse] = []

    class Config:
        from_attributes = True
