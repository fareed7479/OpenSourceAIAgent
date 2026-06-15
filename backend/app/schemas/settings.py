from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class SettingUpdate(BaseModel):
    key: str
    value: str

class SettingResponse(BaseModel):
    id: str
    key: str
    value: str
    created_at: datetime

    class Config:
        from_attributes = True

class ProviderConfigUpdate(BaseModel):
    provider_name: str
    config_data: Dict[str, Any]

class ProviderConfigResponse(BaseModel):
    id: str
    provider_name: str
    config_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
