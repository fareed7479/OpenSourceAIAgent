import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class AgentLog(Base):
    __tablename__ = "agent_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    stage = Column(String, nullable=False)  # workspace, context, coding, validation, review, commit, pr
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)     # detailed logs, console stdout, error payloads
    
    created_at = Column(DateTime, default=func.now())
    
    agent_run = relationship("AgentRun", back_populates="logs")
