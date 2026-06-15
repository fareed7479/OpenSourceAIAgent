import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.encryption import encrypt_token, decrypt_token
from app.models.settings import Setting
from app.models.provider_config import ProviderConfig
from app.schemas.settings import SettingUpdate, SettingResponse, ProviderConfigUpdate, ProviderConfigResponse
from app.api.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", response_model=List[SettingResponse])
def get_user_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all custom settings for the current user."""
    settings = db.query(Setting).filter(Setting.user_id == current_user.id).all()
    return settings

@router.post("", response_model=SettingResponse)
def update_user_setting(
    payload: SettingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update a custom user setting (e.g. preferred_languages)."""
    setting = db.query(Setting).filter(
        Setting.user_id == current_user.id,
        Setting.key == payload.key
    ).first()
    
    if setting:
        setting.value = payload.value
    else:
        setting = Setting(
            user_id=current_user.id,
            key=payload.key,
            value=payload.value
        )
        db.add(setting)
        
    db.commit()
    db.refresh(setting)
    return setting

@router.get("/providers", response_model=List[ProviderConfigResponse])
def get_provider_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve configured LLM providers. Encrypted fields are obfuscated."""
    configs = db.query(ProviderConfig).filter(ProviderConfig.user_id == current_user.id).all()
    
    # Obfuscate API keys before returning
    safe_configs = []
    for c in configs:
        data = dict(c.config_data)
        if "api_key" in data and data["api_key"]:
            data["api_key"] = "••••••••••••••••"
        
        # Create a transient representation to avoid writing obfuscated data back to DB
        safe_configs.append(
            ProviderConfig(
                id=c.id,
                user_id=c.user_id,
                provider_name=c.provider_name,
                config_data=data,
                created_at=c.created_at,
                updated_at=c.updated_at
            )
        )
    return safe_configs

@router.post("/providers", response_model=ProviderConfigResponse)
def update_provider_config(
    payload: ProviderConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save or update LLM provider configuration, encrypting the API key."""
    config = db.query(ProviderConfig).filter(
        ProviderConfig.user_id == current_user.id,
        ProviderConfig.provider_name == payload.provider_name
    ).first()
    
    cleaned_config_data = dict(payload.config_data)
    
    # Check if a new api_key was provided (if it's not the obfuscated bullet string)
    if "api_key" in cleaned_config_data:
        key_val = cleaned_config_data["api_key"]
        if key_val == "••••••••••••••••" and config:
            # Keep the existing encrypted key
            cleaned_config_data["api_key"] = config.config_data.get("api_key", "")
        else:
            # Encrypt the new key
            cleaned_config_data["api_key"] = encrypt_token(key_val)
            
    if config:
        config.config_data = cleaned_config_data
    else:
        config = ProviderConfig(
            user_id=current_user.id,
            provider_name=payload.provider_name,
            config_data=cleaned_config_data
        )
        db.add(config)
        
    db.commit()
    db.refresh(config)
    
    # Return response obfuscated
    response_data = dict(config.config_data)
    if "api_key" in response_data and response_data["api_key"]:
        response_data["api_key"] = "••••••••••••••••"
        
    return ProviderConfig(
        id=config.id,
        user_id=config.user_id,
        provider_name=config.provider_name,
        config_data=response_data,
        created_at=config.created_at,
        updated_at=config.updated_at
    )
