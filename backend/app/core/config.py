import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Open Source AI Contribution Agent"
    
    # Security
    SECRET_KEY: str = Field(default="supersecretjwtkey_change_me_in_production_1234567890")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Token Encryption (Fernet key - must be 32 url-safe base64-encoded bytes)
    # If not set, we generate a random one for transient dev use.
    ENCRYPTION_KEY: str = Field(default="")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./agent_platform.db")
    
    # Redis & Celery
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    
    # GitHub OAuth
    GITHUB_CLIENT_ID: Optional[str] = Field(default=None)
    GITHUB_CLIENT_SECRET: Optional[str] = Field(default=None)
    GITHUB_REDIRECT_URI: str = Field(default="http://localhost:5173/auth/callback")
    GITHUB_WEBHOOK_SECRET: str = Field(default="supersecretwebhookkey")
    
    # Workspace management
    WORKSPACES_DIR: str = Field(default="./workspaces")
    
    # LLM Keys
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    
    # OpenHands Config
    OPENHANDS_API_KEY: Optional[str] = Field(default=None)
    OPENHANDS_BASE_URL: str = Field(default="http://localhost:3000")
    
    # Allowed CORS Origins
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Ensure workspaces directory exists
os.makedirs(settings.WORKSPACES_DIR, exist_ok=True)
