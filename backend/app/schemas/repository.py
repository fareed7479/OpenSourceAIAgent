from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, HttpUrl, field_validator

class RepositoryCreate(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        # standard github URL check: https://github.com/owner/name
        # clean the url first
        url_str = str(v).strip().rstrip("/")
        if url_str.endswith(".git"):
            url_str = url_str[:-4]
        if not url_str.startswith("https://github.com/"):
            raise ValueError("Only GitHub HTTPS repository URLs are supported (https://github.com/owner/repo)")
        parts = url_str.replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            raise ValueError("Repository URL must include owner and repository name (https://github.com/owner/repo)")
        return url_str

class RepositoryUpdate(BaseModel):
    status: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    build_system: Optional[str] = None
    test_command: Optional[str] = None
    lint_command: Optional[str] = None
    contribution_rules: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None

class RepositoryResponse(BaseModel):
    id: str
    owner: str
    name: str
    url: str
    branch: str
    status: str
    language: Optional[str] = None
    framework: Optional[str] = None
    build_system: Optional[str] = None
    test_command: Optional[str] = None
    lint_command: Optional[str] = None
    contribution_rules: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
