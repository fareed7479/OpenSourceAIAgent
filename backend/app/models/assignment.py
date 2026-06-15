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
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="assignments")
    issue = relationship("Issue", back_populates="assignments")
