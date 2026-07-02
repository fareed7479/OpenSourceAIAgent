from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import Column, String, BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Assignment(Base):
    __tablename__ = "assignments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    issue_id = Column(String, ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="requested")  # requested, approved, rejected, monitoring, active, completed, failed
    request_comment_id = Column(BigInteger, nullable=True)  # GitHub comment ID where request comment was posted
    comment_url = Column(String, nullable=True)
    issue_url = Column(String, nullable=True)
    repository_url = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="assignments")
    issue = relationship("Issue", back_populates="assignments")

    @property
    def assignment_id(self) -> str:
        return self.id

    @property
    def issue_number(self) -> Optional[int]:
        return self.issue.number if self.issue else None

    @property
    def issue_title(self) -> Optional[str]:
        return self.issue.title if self.issue else None

    @property
    def repository_name(self) -> Optional[str]:
        return self.issue.repository.name if self.issue and self.issue.repository else None

    @property
    def repository_owner(self) -> Optional[str]:
        return self.issue.repository.owner if self.issue and self.issue.repository else None

    @property
    def assignment_status(self) -> str:
        return self.status

    @property
    def assigned_at(self) -> datetime:
        return self.created_at

    @property
    def agent_run_id(self) -> Optional[str]:
        if self.issue and self.issue.agent_runs:
            sorted_runs = sorted(self.issue.agent_runs, key=lambda r: r.created_at, reverse=True)
            return sorted_runs[0].id
        return None

    @property
    def workflow_status(self) -> Optional[str]:
        if self.issue and self.issue.agent_runs:
            sorted_runs = sorted(self.issue.agent_runs, key=lambda r: r.created_at, reverse=True)
            return sorted_runs[0].status
        return None

    @property
    def current_stage(self) -> Optional[str]:
        if self.issue and self.issue.agent_runs:
            sorted_runs = sorted(self.issue.agent_runs, key=lambda r: r.created_at, reverse=True)
            latest_run = sorted_runs[0]
            if latest_run.logs:
                sorted_logs = sorted(latest_run.logs, key=lambda l: l.created_at, reverse=True)
                return sorted_logs[0].stage
            return latest_run.status
        return None

    @property
    def repository(self):
        return self.issue.repository if self.issue else None

