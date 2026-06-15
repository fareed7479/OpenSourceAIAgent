import os
import shutil
import logging
from typing import Dict, Any, List
import git
from app.core.config import settings

logger = logging.getLogger(__name__)

class WorkspaceManager:
    @staticmethod
    def get_repo_dir(repo_id: str) -> str:
        """Get the absolute disk directory for a repository workspace."""
        return os.path.abspath(os.path.join(settings.WORKSPACES_DIR, repo_id))

    @classmethod
    def clone_repository(cls, repo_id: str, git_url: str, github_token: str = None) -> str:
        """
        Clones a repository to a local isolated workspace.
        Supports authentication by embedding the GitHub OAuth token in the URL if provided.
        """
        clone_path = cls.get_repo_dir(repo_id)
        
        # Clean up existing workspace if directory exists
        if os.path.exists(clone_path):
            logger.warning(f"Workspace directory {clone_path} already exists. Cleaning it up first.")
            shutil.rmtree(clone_path, ignore_errors=True)
            
        os.makedirs(clone_path, exist_ok=True)
        
        # Inject token into URL if authenticated
        url = git_url
        if github_token and "github.com" in git_url:
            # git_url format is usually: https://github.com/owner/repo
            # we want: https://<token>@github.com/owner/repo
            url = git_url.replace("https://github.com/", f"https://x-access-token:{github_token}@github.com/")

        logger.info(f"Cloning repository from {git_url} to {clone_path}...")
        try:
            repo = git.Repo.clone_from(url, clone_path)
            logger.info(f"Cloned successfully. Default branch is: {repo.active_branch.name}")
            return clone_path
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            if os.path.exists(clone_path):
                shutil.rmtree(clone_path, ignore_errors=True)
            raise e

    @classmethod
    def create_and_checkout_branch(cls, repo_id: str, branch_name: str) -> bool:
        """Create a new branch and checkout to it."""
        repo_path = cls.get_repo_dir(repo_id)
        try:
            repo = git.Repo(repo_path)
            
            # Ensure we are clean on default branch first
            repo.git.checkout(repo.active_branch.name)
            repo.git.reset('--hard')
            
            # Create and checkout branch
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            logger.info(f"Created and checked out branch: {branch_name} in {repo_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create/checkout branch {branch_name}: {e}")
            return False

    @classmethod
    def get_diff(cls, repo_id: str) -> str:
        """Get the current uncommitted diff in the repository workspace."""
        repo_path = cls.get_repo_dir(repo_id)
        try:
            repo = git.Repo(repo_path)
            # Diff against HEAD to see both staged and unstaged edits
            diff = repo.git.diff('HEAD')
            return diff
        except Exception as e:
            logger.error(f"Failed to get diff: {e}")
            return ""

    @classmethod
    def commit_changes(cls, repo_id: str, commit_message: str) -> bool:
        """Stage all changes and commit them with conventional commit guidelines."""
        repo_path = cls.get_repo_dir(repo_id)
        try:
            repo = git.Repo(repo_path)
            
            # Stage all changes (git add .)
            repo.git.add(A=True)
            
            # Check if there are changes to commit
            if not repo.is_dirty(untracked_files=True):
                logger.warning("No changes to commit.")
                return False
                
            # Commit changes
            repo.index.commit(commit_message)
            logger.info(f"Committed changes with message: '{commit_message}'")
            return True
        except Exception as e:
            logger.error(f"Failed to commit changes: {e}")
            return False

    @classmethod
    def push_branch(cls, repo_id: str, branch_name: str, github_token: str = None) -> bool:
        """Push branch to origin remote, injecting OAuth token for write access."""
        repo_path = cls.get_repo_dir(repo_id)
        try:
            repo = git.Repo(repo_path)
            
            # Set up push URL with credential if available
            origin = repo.remote(name='origin')
            push_url = origin.url
            
            if github_token and "github.com" in push_url and "x-access-token" not in push_url:
                push_url = push_url.replace("https://github.com/", f"https://x-access-token:{github_token}@github.com/")
                # Temporarily update remote url
                origin.set_url(push_url)
                
            logger.info(f"Pushing branch {branch_name} to origin remote...")
            origin.push(refspec=f"{branch_name}:{branch_name}", force=True)
            logger.info(f"Branch {branch_name} pushed successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to push branch {branch_name}: {e}")
            return False
