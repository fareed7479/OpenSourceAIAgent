import os
import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.repository import Repository
from app.services.workspace import WorkspaceManager
from app.services.analyzer import analyze_repository

logger = logging.getLogger(__name__)

def clone_and_analyze_repo_task(repo_id: str, github_token: str = None) -> None:
    """
    Background task to:
    1. Clone the repository locally.
    2. Analyze the codebase (languages, build system, tests, guidelines).
    3. Update the Repository entry in the database.
    4. Trigger issue discovery (Phase 2).
    """
    db: Session = SessionLocal()
    try:
        # Fetch repository from DB
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            logger.error(f"Repository {repo_id} not found in database.")
            return

        # Update status to cloning
        repo.status = "cloning"
        db.commit()

        # 1. Clone repository
        try:
            clone_path = WorkspaceManager.clone_repository(
                repo_id=repo.id,
                git_url=repo.url,
                github_token=github_token
            )
            # Verify files exist locally
            if not os.path.exists(clone_path) or not os.listdir(clone_path):
                raise ValueError("Cloned directory does not exist or is empty.")
            repo.clone_path = clone_path
        except Exception as e:
            logger.error(f"Error cloning repository {repo.url}: {e}")
            repo.status = "failed"
            db.commit()
            return

        # 2. Analyze repository
        logger.info(f"Analyzing repository at {clone_path}...")
        try:
            analysis_results = analyze_repository(clone_path)
            
            repo.language = analysis_results.get("language")
            repo.framework = analysis_results.get("framework")
            repo.build_system = analysis_results.get("build_system")
            repo.test_command = analysis_results.get("test_command")
            repo.lint_command = analysis_results.get("lint_command")
            repo.contribution_rules = analysis_results.get("contribution_rules")
            
            # Merge existing metadata with analysis metadata
            existing_meta = dict(repo.meta_info or {})
            analysis_meta = analysis_results.get("meta_info") or {}
            existing_meta.update(analysis_meta)
            repo.meta_info = existing_meta
            
            repo.status = "cloned"
            
            logger.info(f"Repository {repo.owner}/{repo.name} analysis complete. Triggering indexing...")
            try:
                from app.services.intelligence import scan_and_index_repository
                scan_and_index_repository(repo.id, clone_path)
            except Exception as index_err:
                logger.error(f"Failed to compile symbol index / embeddings for repo: {index_err}")
                
        except Exception as e:
            logger.error(f"Error analyzing repository {repo.url}: {e}")
            repo.status = "failed"
            
        db.commit()
        
        # 3. Trigger issue discovery task (Phase 2)
        # We will import and call it here. To avoid circular imports, we import inline.
        try:
            from app.services.discovery import discover_repository_issues_task
            logger.info(f"Triggering issue discovery for repository: {repo.owner}/{repo.name}")
            discover_repository_issues_task(repo_id, github_token)
        except Exception as discovery_error:
            logger.error(f"Failed to auto-trigger issue discovery: {discovery_error}")

    except Exception as e:
        logger.error(f"Fatal error in clone_and_analyze_repo_task: {e}")
    finally:
        db.close()
