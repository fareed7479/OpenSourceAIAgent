import httpx
import logging
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.repository import Repository
from app.models.issue import Issue
from app.models.assignment import Assignment
from app.core.encryption import decrypt_token

logger = logging.getLogger(__name__)

ASSIGNMENT_COMMENT_TEMPLATE = """Hello Maintainers,

I would like to work on this issue.

I plan to use AI-assisted development tools during implementation while carefully reviewing and validating all generated code before submission.

Could you please assign this issue to me?

Thank you."""

def request_issue_assignment(issue_id: str, user_id: str, db: Session = None) -> Assignment:
    """
    Posts assignment request comment to GitHub issue.
    Creates Assignment record in the database.
    """
    is_local = False
    if db is None:
        db = SessionLocal()
        is_local = True
    try:
        issue = db.query(Issue).filter(Issue.id == issue_id).first()
        if not issue:
            raise ValueError(f"Issue {issue_id} not found.")

        repo = db.query(Repository).filter(Repository.id == issue.repository_id).first()
        if not repo:
            raise ValueError(f"Repository for issue {issue_id} not found.")

        # Check if already requested or assigned
        existing = db.query(Assignment).filter(
            Assignment.issue_id == issue_id,
            Assignment.user_id == user_id
        ).first()
        
        if existing and existing.status in ["requested", "active"]:
            logger.info(f"Assignment already {existing.status} for issue {issue_id}.")
            return existing

        decrypted_token = decrypt_token(repo.user.access_token)
        is_mock = repo.user.github_id.startswith("mock-") or decrypted_token == "mock-github-access-token"

        comment_id = None
        
        if not is_mock:
            # Post comment to GitHub issue comments endpoint
            url = f"https://api.github.com/repos/{repo.owner}/{repo.name}/issues/{issue.number}/comments"
            headers = {
                "Authorization": f"token {decrypted_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "OpenSource-AI-Contribution-Agent"
            }
            payload = {"body": ASSIGNMENT_COMMENT_TEMPLATE}
            
            logger.info(f"Posting assignment request comment to GitHub: {url}")
            response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
            
            if response.status_code == 201:
                comment_data = response.json()
                comment_id = comment_data.get("id")
                logger.info(f"Comment posted successfully. Comment ID: {comment_id}")
            else:
                logger.error(f"Failed to post assignment comment to GitHub: {response.status_code} - {response.text}")
                raise Exception("Failed to post comment to GitHub. Please check repository access settings.")
        else:
            logger.info(f"[Mock Mode] Simulation: Posting comment requesting assignment for issue #{issue.number}")
            comment_id = 999111  # mock comment ID
            
        # Create DB Assignment record
        assignment = Assignment(
            user_id=user_id,
            issue_id=issue_id,
            status="requested",
            request_comment_id=comment_id
        )
        db.add(assignment)
        
        # Update Issue status to requested
        issue.assignment_status = "requested"
        db.commit()
        db.refresh(assignment)
        
        # If mock mode, trigger a quick background helper to auto-assign it after a short delay
        if is_mock:
            from fastapi import BackgroundTasks
            # We will handle mock auto-assignment inline in monitor task
            
        return assignment
    except Exception as e:
        logger.error(f"Error requesting issue assignment: {e}")
        db.rollback()
        raise e
    finally:
        if is_local:
            db.close()


def monitor_assignments_task() -> None:
    """
    Background worker task to poll active assignment requests.
    Validates if assignee matches user, updating the DB and triggering the work task.
    """
    db: Session = SessionLocal()
    try:
        # Get all requested or monitoring assignments
        active_requests = db.query(Assignment).filter(
            Assignment.status.in_(["requested", "monitoring"])
        ).all()
        
        for assignment in active_requests:
            issue = assignment.issue
            repo = issue.repository
            user = assignment.user
            
            decrypted_token = decrypt_token(user.access_token)
            is_mock = user.github_id.startswith("mock-") or decrypted_token == "mock-github-access-token"
            
            # 1. Handle Mock Auto-Assignment Bypass
            if is_mock:
                logger.info(f"[Mock Mode] Simulating maintainer review. Auto-assigning issue #{issue.number} to user {user.username}")
                assignment.status = "active"
                issue.assignment_status = "assigned_to_user"
                issue.assignee_username = user.username
                db.commit()
                
                # Trigger Workspace Manager / coding flow (Phase 4 / 5)
                # To prevent circular imports we do it inline
                _trigger_agent_run(db, repo.id, issue.id, user.id)
                continue

            # 2. Production GitHub API status polling
            url = f"https://api.github.com/repos/{repo.owner}/{repo.name}/issues/{issue.number}"
            headers = {
                "Authorization": f"token {decrypted_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "OpenSource-AI-Contribution-Agent"
            }
            
            logger.info(f"Polling assignment status for issue #{issue.number} from GitHub: {url}")
            response = httpx.get(url, headers=headers, timeout=10.0)
            
            if response.status_code != 200:
                logger.error(f"Failed to poll issue status: {response.status_code} - {response.text}")
                continue
                
            issue_data = response.json()
            
            # Check issue state
            if issue_data.get("state") == "closed":
                assignment.status = "failed"
                issue.status = "closed"
                issue.assignment_status = "unassigned"
                logger.info(f"Issue #{issue.number} was closed. Marking assignment as failed.")
                db.commit()
                continue
                
            # Check assignee details
            assignee = issue_data.get("assignee")
            if assignee:
                assignee_login = assignee.get("login")
                if assignee_login == user.username:
                    # Assigned to current user!
                    assignment.status = "active"
                    issue.assignment_status = "assigned_to_user"
                    issue.assignee_username = user.username
                    db.commit()
                    logger.info(f"Successfully assigned to user! Triggering agent run.")
                    
                    # Trigger implementation workspace clone and agent run
                    _trigger_agent_run(db, repo.id, issue.id, user.id)
                else:
                    # Assigned to someone else
                    assignment.status = "rejected"
                    issue.assignment_status = "assigned_to_other"
                    issue.assignee_username = assignee_login
                    db.commit()
                    logger.info(f"Issue assigned to someone else: {assignee_login}. Assignment request rejected.")
            else:
                # Still unassigned, keep polling next time
                logger.info(f"Issue #{issue.number} is still unassigned.")
                
    except Exception as e:
        logger.error(f"Error monitoring assignments: {e}")
    finally:
        db.close()


def _trigger_agent_run(db: Session, repo_id: str, issue_id: str, user_id: str) -> None:
    """Creates a new agent run and schedules execution."""
    from app.models.run import AgentRun
    # Import removed
    from fastapi import BackgroundTasks
    
    # Check if there is already an active run for this issue
    existing_run = db.query(AgentRun).filter(
        AgentRun.issue_id == issue_id,
        AgentRun.status.in_(["pending", "running", "validating", "reviewing"])
    ).first()
    
    if existing_run:
        logger.warning(f"Active agent run {existing_run.id} already exists for issue {issue_id}. Skipping trigger.")
        return

    # Create run entry in pending state
    # Branch name format: issue-{issue-number}-{slug}
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    slug = issue.title.lower().replace(":", "").replace("/", "").replace(" ", "-")[:40]
    branch_name = f"issue-{issue.number}-{slug}"
    
    # Get user settings for preferred LLM provider or default to jules
    # Let's inspect settings or config. We can check settings or default to jules.
    provider = "jules" # default
    
    new_run = AgentRun(
        repository_id=repo_id,
        issue_id=issue_id,
        user_id=user_id,
        branch_name=branch_name,
        provider=provider,
        status="pending"
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)
    
    logger.info(f"Created pending agent run {new_run.id} for issue #{issue.number}. Triggering async runner.")
    
    # We will trigger the runner in a background thread/task
    # Using raw thread pool / BackgroundTasks
    # For now, let's run it. We import the executor inline
    try:
        from fastapi import BackgroundTasks
        # We can trigger it asynchronously using a background thread
        import threading
        from app.services.agent_orchestrator import MultiAgentOrchestrator
        orchestrator = MultiAgentOrchestrator()
        thread = threading.Thread(target=orchestrator.execute_workflow, args=(new_run.id,))
        thread.daemon = True
        thread.start()
    except Exception as run_trigger_error:
        logger.error(f"Failed to start agent workflow thread: {run_trigger_error}")
