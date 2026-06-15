from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class UserBase(BaseModel):
    github_id: str
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    access_token: str

class UserUpdate(BaseModel):
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    access_token: Optional[str] = None

class UserInDBBase(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class User(UserInDBBase):
    pass
