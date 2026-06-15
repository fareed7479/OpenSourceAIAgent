import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Repository(Base):
    __tablename__ = "repositories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    owner = Column(String, nullable=False)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    clone_path = Column(String, nullable=True)
    branch = Column(String, default="main")
    status = Column(String, default="pending")  # pending, cloning, cloned, failed
    
    language = Column(String, nullable=True)
    framework = Column(String, nullable=True)
    build_system = Column(String, nullable=True)
    test_command = Column(String, nullable=True)
    lint_command = Column(String, nullable=True)
    contribution_rules = Column(Text, nullable=True)
    meta_info = Column(JSON, nullable=True)  # renamed from metadata because SQLAlchemy has a metadata attribute in Base
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="repositories")
    issues = relationship("Issue", back_populates="repository", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="repository", cascade="all, delete-orphan")
