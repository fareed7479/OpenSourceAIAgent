import httpx
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.core.encryption import encrypt_token
from app.models.user import User
from app.schemas.user import User as UserSchema
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/login")
def login(developer_mode: bool = Query(False, description="Force developer mock login bypass")):
    """Redirect to GitHub OAuth or return mock bypass options."""
    if not settings.GITHUB_CLIENT_ID or developer_mode:
        logger.info("GitHub Client ID not set or developer_mode enabled. Directing to developer mock login.")
        # Redirect to frontend mock login page
        return RedirectResponse(url=f"{settings.GITHUB_REDIRECT_URI}?mock=true")
        
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=repo,user"
    )
    return RedirectResponse(url=github_auth_url)

@router.get("/callback")
async def callback(code: str = None, mock_username: str = None, db: Session = Depends(get_db)):
    """Handle GitHub OAuth callback or mock login callback."""
    # 1. Developer Mock Mode handling
    if mock_username or (not code and not settings.GITHUB_CLIENT_ID):
        username = mock_username or "dev-contributor"
        logger.info(f"Mocking authentication callback for user: {username}")
        
        # Check if mock user already exists, or create them
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                github_id=f"mock-{username}",
                username=username,
                email=f"{username}@example.com",
                avatar_url=f"https://avatars.githubusercontent.com/u/999999?v=4",
                access_token=encrypt_token("mock-github-access-token")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
        access_token = create_access_token(subject=user.id)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "developer_mode": True
            }
        }

    # 2. Production GitHub OAuth exchange
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code was not provided by GitHub."
        )
        
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GITHUB_REDIRECT_URI,
                },
                timeout=10.0
            )
            token_data = token_response.json()
            
        if "error" in token_data:
            logger.error(f"GitHub OAuth error: {token_data}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"GitHub authentication failed: {token_data.get('error_description')}"
            )
            
        github_access_token = token_data.get("access_token")
        if not github_access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Did not receive access token from GitHub."
            )
            
        # Fetch user details
        async with httpx.AsyncClient() as client:
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {github_access_token}",
                    "Accept": "application/json"
                },
                timeout=10.0
            )
            github_user = user_response.json()
            
        github_id = str(github_user.get("id"))
        username = github_user.get("login")
        email = github_user.get("email")
        avatar_url = github_user.get("avatar_url")
        
        # Save or update user in database
        user = db.query(User).filter(User.github_id == github_id).first()
        encrypted_token = encrypt_token(github_access_token)
        
        if user:
            user.username = username
            user.email = email
            user.avatar_url = avatar_url
            user.access_token = encrypted_token
        else:
            user = User(
                github_id=github_id,
                username=username,
                email=email,
                avatar_url=avatar_url,
                access_token=encrypted_token
            )
            db.add(user)
            
        db.commit()
        db.refresh(user)
        
        # Generate JWT session token
        jwt_token = create_access_token(subject=user.id)
        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "developer_mode": False
            }
        }
        
    except httpx.HTTPError as err:
        logger.error(f"HTTP request to GitHub failed: {err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to communicate with GitHub API."
        )

@router.get("/me", response_model=UserSchema)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return current_user
