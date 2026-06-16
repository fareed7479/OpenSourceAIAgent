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
    
    meta_info = {}
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
            meta_info = {
                "github_metadata": {
                    "name": repo_info.get("name"),
                    "description": repo_info.get("description"),
                    "default_branch": default_branch,
                    "fork": repo_info.get("fork", False),
                    "private": repo_info.get("private", False),
                    "owner": repo_info.get("owner", {}).get("login"),
                    "language": repo_info.get("language"),
                    "topics": repo_info.get("topics", []),
                    "clone_url": repo_info.get("clone_url"),
                    "html_url": repo_info.get("html_url"),
                    "updated_at": repo_info.get("updated_at"),
                    "stargazers_count": repo_info.get("stargazers_count", 0),
                    "open_issues_count": repo_info.get("open_issues_count", 0),
                    "has_issues": repo_info.get("has_issues", True),
                    "parent": repo_info.get("parent")
                }
            }
            
        except httpx.HTTPError as err:
            logger.error(f"Failed to communicate with GitHub API: {err}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub API communication failure."
            )
    else:
        logger.info("Skipping GitHub API verification for mock user.")
        default_branch = "main"
        meta_info = {
            "github_metadata": {
                "name": name,
                "description": "Mocked repository description for developer testing.",
                "default_branch": default_branch,
                "fork": True,
                "private": False,
                "owner": owner,
                "language": "Python",
                "topics": ["mock", "test"],
                "clone_url": f"https://github.com/{owner}/{name}.git",
                "html_url": f"https://github.com/{owner}/{name}",
                "updated_at": "2026-06-16T00:00:00Z",
                "stargazers_count": 42,
                "open_issues_count": 3,
                "has_issues": True,
                "parent": None
            }
        }

    # Create new repository record
    new_repo = Repository(
        user_id=current_user.id,
        owner=owner,
        name=name,
        url=url_str,
        branch=default_branch,
        status="pending",
        meta_info=meta_info
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

@router.get("/github", response_model=List[dict])
async def list_github_repositories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch the authenticated user's repositories directly from GitHub API.
    """
    decrypted_token = decrypt_token(current_user.access_token)
    is_mock = current_user.github_id.startswith("mock-") or decrypted_token == "mock-github-access-token"
    
    if is_mock:
        return [
            {
                "name": "College_Companion",
                "full_name": f"{current_user.username}/College_Companion",
                "description": "A student companion for college task tracking.",
                "html_url": f"https://github.com/{current_user.username}/College_Companion",
                "clone_url": f"https://github.com/{current_user.username}/College_Companion.git",
                "default_branch": "main",
                "fork": True,
                "private": False,
                "language": "Python",
                "updated_at": "2026-06-16T00:00:00Z",
                "stargazers_count": 12,
                "open_issues_count": 4
            },
            {
                "name": "Backend",
                "full_name": f"{current_user.username}/Backend",
                "description": "FastAPI backend services.",
                "html_url": f"https://github.com/{current_user.username}/Backend",
                "clone_url": f"https://github.com/{current_user.username}/Backend.git",
                "default_branch": "master",
                "fork": False,
                "private": True,
                "language": "Go",
                "updated_at": "2026-06-15T00:00:00Z",
                "stargazers_count": 99,
                "open_issues_count": 0
            }
        ]
        
    try:
        repos = []
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"token {decrypted_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "OpenSource-AI-Contribution-Agent"
            }
            
            response = await client.get(
                "https://api.github.com/user/repos?per_page=100&sort=updated",
                headers=headers,
                timeout=15.0
            )
            
            if response.status_code != 200:
                logger.error(f"GitHub API returned {response.status_code} on /user/repos: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch repositories from GitHub."
                )
                
            gh_repos = response.json()
            for r in gh_repos:
                repos.append({
                    "name": r.get("name"),
                    "full_name": r.get("full_name"),
                    "description": r.get("description"),
                    "html_url": r.get("html_url"),
                    "clone_url": r.get("clone_url"),
                    "default_branch": r.get("default_branch", "main"),
                    "fork": r.get("fork", False),
                    "private": r.get("private", False),
                    "language": r.get("language"),
                    "updated_at": r.get("updated_at"),
                    "stargazers_count": r.get("stargazers_count", 0),
                    "open_issues_count": r.get("open_issues_count", 0)
                })
        return repos
    except httpx.HTTPError as err:
        logger.error(f"Failed to communicate with GitHub API: {err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API communication failure."
        )

@router.post("/{repo_id}/sync", response_model=RepositoryResponse)
async def sync_repository(
    repo_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Refresh repository metadata from GitHub and trigger issue discovery.
    """
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found."
        )
        
    decrypted_token = decrypt_token(current_user.access_token)
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
                    f"https://api.github.com/repos/{repo.owner}/{repo.name}",
                    headers=headers,
                    timeout=10.0
                )
                
            if gh_response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found on GitHub."
                )
            elif gh_response.status_code != 200:
                logger.error(f"GitHub API returned status {gh_response.status_code}: {gh_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch repository info from GitHub."
                )
                
            repo_info = gh_response.json()
            repo.branch = repo_info.get("default_branch", "main")
            
            # Update meta_info
            meta = dict(repo.meta_info) if repo.meta_info else {}
            meta["github_metadata"] = {
                "name": repo_info.get("name"),
                "description": repo_info.get("description"),
                "default_branch": repo.branch,
                "fork": repo_info.get("fork", False),
                "private": repo_info.get("private", False),
                "owner": repo_info.get("owner", {}).get("login"),
                "language": repo_info.get("language"),
                "topics": repo_info.get("topics", []),
                "clone_url": repo_info.get("clone_url"),
                "html_url": repo_info.get("html_url"),
                "updated_at": repo_info.get("updated_at"),
                "stargazers_count": repo_info.get("stargazers_count", 0),
                "open_issues_count": repo_info.get("open_issues_count", 0),
                "has_issues": repo_info.get("has_issues", True),
                "parent": repo_info.get("parent")
            }
            repo.meta_info = meta
            db.commit()
            db.refresh(repo)
            
        except httpx.HTTPError as err:
            logger.error(f"Failed to communicate with GitHub API: {err}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub API communication failure."
            )
    else:
        meta = dict(repo.meta_info) if repo.meta_info else {}
        meta["github_metadata"] = {
            "name": repo.name,
            "description": "Mocked repository description.",
            "default_branch": repo.branch,
            "fork": True,
            "private": False,
            "owner": repo.owner,
            "language": "Python",
            "topics": ["mock", "demo"],
            "clone_url": f"https://github.com/{repo.owner}/{repo.name}.git",
            "html_url": f"https://github.com/{repo.owner}/{repo.name}",
            "updated_at": "2026-06-16T00:00:00Z",
            "stargazers_count": 100,
            "open_issues_count": 5,
            "has_issues": True,
            "parent": None
        }
        repo.meta_info = meta
        db.commit()
        db.refresh(repo)
        
    from app.services.discovery import discover_repository_issues_task
    background_tasks.add_task(
        discover_repository_issues_task,
        repo_id=repo.id,
        github_token=decrypted_token if not is_mock else None
    )
    
    return repo

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
