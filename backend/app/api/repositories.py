import os
import shutil
import httpx
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.encryption import decrypt_token
from app.models.repository import Repository
from app.schemas.repository import RepositoryCreate, RepositoryResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services.tasks import clone_and_analyze_repo_task
from app.services.workspace import WorkspaceManager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def register_repository(
    payload: RepositoryCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register a forked or original GitHub repository.
    Verifies existence via GitHub API and schedules asynchronous cloning/analysis.
    """
    url_str = payload.url
    # Extract owner and repo name from GitHub URL
    parts = url_str.replace("https://github.com/", "").split("/")
    owner = parts[0]
    name = parts[1]
    
    # Check if repository already registered by this user
    existing_repo = db.query(Repository).filter(
        Repository.user_id == current_user.id,
        Repository.owner == owner,
        Repository.name == name
    ).first()
    
    if existing_repo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository is already registered."
        )

    # Fetch repo details from GitHub API to validate existence and get default branch
    decrypted_token = decrypt_token(current_user.access_token)
    default_branch = "main"
    
    # Check if we are running in developer mock mode
    is_mock = current_user.github_id.startswith("mock-") or decrypted_token == "mock-github-access-token"
    
    if not is_mock:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"token {decrypted_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "OpenSource-AI-Contribution-Agent"
                }
                gh_response = await client.get(
                    f"https://api.github.com/repos/{owner}/{name}",
                    headers=headers,
                    timeout=10.0
                )
                
            if gh_response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found on GitHub. Verify ownership and visibility settings."
                )
            elif gh_response.status_code != 200:
                logger.error(f"GitHub API returned status {gh_response.status_code}: {gh_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to verify repository on GitHub."
                )
                
            repo_info = gh_response.json()
            default_branch = repo_info.get("default_branch", "main")
            
        except httpx.HTTPError as err:
            logger.error(f"Failed to communicate with GitHub API: {err}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub API communication failure."
            )
    else:
        logger.info("Skipping GitHub API verification for mock user.")
        # Default mock defaults
        default_branch = "main"

    # Create new repository record
    new_repo = Repository(
        user_id=current_user.id,
        owner=owner,
        name=name,
        url=url_str,
        branch=default_branch,
        status="pending"
    )
    
    db.add(new_repo)
    db.commit()
    db.refresh(new_repo)
    
    # Trigger local cloning and analysis in background
    background_tasks.add_task(
        clone_and_analyze_repo_task,
        repo_id=new_repo.id,
        github_token=decrypted_token if not is_mock else None
    )
    
    return new_repo

@router.get("", response_model=List[RepositoryResponse])
def list_repositories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all registered repositories for the current user."""
    repos = db.query(Repository).filter(Repository.user_id == current_user.id).all()
    return repos

@router.get("/{repo_id}", response_model=RepositoryResponse)
def get_repository(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details of a registered repository."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )
    return repo

@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a registered repository and its local workspace clone."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )
        
    # Clean up local workspace files
    clone_path = WorkspaceManager.get_repo_dir(repo.id)
    if os.path.exists(clone_path):
        logger.info(f"Removing repository workspace directory: {clone_path}")
        shutil.rmtree(clone_path, ignore_errors=True)
        
    db.delete(repo)
    db.commit()
    return None
