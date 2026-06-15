import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ProviderConfig(Base):
    __tablename__ = "provider_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider_name = Column(String, nullable=False, index=True)  # gemini, claude, etc.
    config_data = Column(JSON, nullable=False)  # stores model_name, api_key (encrypted), custom_url, etc.
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="provider_configs")
