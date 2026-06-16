import uuid
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, JSON, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Issue(Base):
    __tablename__ = "issues"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    github_issue_id = Column(BigInteger, nullable=False, index=True)
    number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=False)
    labels = Column(JSON, default=list)
    
    difficulty = Column(String, default="unknown")  # easy, medium, hard, unknown
    score = Column(Integer, default=0)              # score from 0 to 100
    ranking_reason = Column(Text, nullable=True)
    
    status = Column(String, default="open")          # open, closed
    assignment_status = Column(String, default="unassigned")  # unassigned, requested, assigned_to_user, assigned_to_other
    assignee_username = Column(String, nullable=True)
    
    author_username = Column(String, nullable=True)
    github_created_at = Column(DateTime, nullable=True)
    github_updated_at = Column(DateTime, nullable=True)
    comments_count = Column(Integer, default=0)
    meta_info = Column(JSON, nullable=True)
    source_owner = Column(String, nullable=True)
    source_repo = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    repository = relationship("Repository", back_populates="issues")
    assignments = relationship("Assignment", back_populates="issue", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="issue", cascade="all, delete-orphan")
