import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    issue_id = Column(String, ForeignKey("issues.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    branch_name = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # gemini, claude, etc.
    status = Column(String, default="pending")  # pending, running, validating, reviewing, completed, failed
    actual_provider = Column(String, nullable=True)
    fallback_provider = Column(String, nullable=True)
    fallback_reason = Column(String, nullable=True)
    code_diff = Column(String, nullable=True)
    commit_hash = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    repository = relationship("Repository", back_populates="agent_runs")
    issue = relationship("Issue", back_populates="agent_runs")
    user = relationship("User", back_populates="agent_runs")
    logs = relationship("AgentLog", back_populates="agent_run", cascade="all, delete-orphan")
    pull_request = relationship("PullRequest", back_populates="agent_run", uselist=False, cascade="all, delete-orphan")
