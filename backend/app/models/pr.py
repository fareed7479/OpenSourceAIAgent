import uuid
from sqlalchemy import Column, String, BigInteger, Boolean, DateTime, ForeignKey, Text, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class PullRequest(Base):
    __tablename__ = "pull_requests"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    github_pr_id = Column(BigInteger, nullable=True)
    status = Column(String, default="draft")  # draft, review_pending, approved, submitted, closed
    
    files_changed = Column(JSON, default=list)  # list of modified files
    tests_passed = Column(Boolean, nullable=True)
    review_status = Column(Text, nullable=True)  # summary of AI review comments/results
    approval_status = Column(String, default="pending")  # pending, approved, rejected
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    agent_run = relationship("AgentRun", back_populates="pull_request")
