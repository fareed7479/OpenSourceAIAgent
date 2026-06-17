import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.run import AgentRun
from app.schemas.run import AgentRunCreate, AgentRunResponse
from app.api.deps import get_current_user
from app.models.user import User
from app.services.agent_runner import run_agent_workflow_task

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", response_model=List[AgentRunResponse])
def list_runs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all agent runs for the current user."""
    runs = db.query(AgentRun).filter(AgentRun.user_id == current_user.id).order_by(AgentRun.created_at.desc()).all()
    return runs

@router.get("/{run_id}", response_model=AgentRunResponse)
def get_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details and logs of a specific agent run."""
    run = db.query(AgentRun).filter(
        AgentRun.id == run_id,
        AgentRun.user_id == current_user.id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found."
        )
    return run

@router.post("/trigger", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
def trigger_agent_run(
    payload: AgentRunCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a coding agent run for an issue.
    """
    from app.models.issue import Issue
    issue = db.query(Issue).filter(Issue.id == payload.issue_id).first()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found."
        )
        
    repo = issue.repository
    if repo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this repository."
        )
        
    # Check if there is already an active run for this issue
    existing_run = db.query(AgentRun).filter(
        AgentRun.issue_id == issue.id,
        AgentRun.status.in_(["pending", "running", "validating", "reviewing"])
    ).first()
    
    if existing_run:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is already an active agent run for this issue."
        )

    # Generate branch name
    slug = issue.title.lower().replace(":", "").replace("/", "").replace(" ", "-")[:40]
    branch_name = f"issue-{issue.number}-{slug}"
    
    new_run = AgentRun(
        repository_id=repo.id,
        issue_id=issue.id,
        user_id=current_user.id,
        branch_name=branch_name,
        provider=payload.provider,
        status="pending"
    )
    
    db.add(new_run)
    db.commit()
    db.refresh(new_run)
    
    # Trigger background orchestrator state machine task
    from app.services.agent_orchestrator import MultiAgentOrchestrator
    orchestrator = MultiAgentOrchestrator()
    
    import threading
    thread = threading.Thread(target=orchestrator.execute_workflow, args=(new_run.id,))
    thread.daemon = True
    thread.start()
    
    return new_run

@router.get("/{run_id}/plan")
def get_run_plan(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve the generated strategy plan for a specific agent run."""
    from app.models.extensions import AgentPlan
    plan = db.query(AgentPlan).filter(AgentPlan.run_id == run_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy plan not found for this run."
        )
    return {
        "id": plan.id,
        "run_id": plan.run_id,
        "title": plan.title,
        "description": plan.description,
        "steps": plan.steps,
        "status": plan.status,
        "feedback": plan.feedback
    }

@router.post("/{run_id}/approve-plan")
def approve_run_plan(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve the proposed plan and resume workflow execution."""
    from app.models.extensions import AgentPlan
    plan = db.query(AgentPlan).filter(AgentPlan.run_id == run_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy plan not found."
        )
        
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
         raise HTTPException(status_code=404, detail="Run not found.")

    plan.status = "approved"
    run.status = "running"
    db.commit()
    
    # Resume orchestrator state machine from the context_agent node
    from app.services.agent_orchestrator import MultiAgentOrchestrator
    orchestrator = MultiAgentOrchestrator()
    
    import threading
    thread = threading.Thread(target=orchestrator.execute_workflow, args=(run_id, "context_agent"))
    thread.daemon = True
    thread.start()
    
    return {"message": "Plan approved. Workflow execution resumed.", "status": "approved"}

@router.post("/{run_id}/reject-plan")
async def reject_run_plan(
    run_id: str,
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject the plan with feedback, halting execution in failed status."""
    from app.models.extensions import AgentPlan
    plan = db.query(AgentPlan).filter(AgentPlan.run_id == run_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
        
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
         raise HTTPException(status_code=404, detail="Run not found.")
         
    feedback = payload.get("feedback", "")
    plan.status = "rejected"
    plan.feedback = feedback
    run.status = "failed"
    db.commit()
    
    return {"message": "Plan rejected.", "status": "rejected"}

@router.post("/{run_id}/regenerate-plan")
def regenerate_run_plan(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request the Planning Agent to regenerate the strategy plan."""
    from app.models.extensions import AgentPlan
    plan = db.query(AgentPlan).filter(AgentPlan.run_id == run_id).first()
    if not plan:
         raise HTTPException(status_code=404, detail="Plan not found.")
         
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
         raise HTTPException(status_code=404, detail="Run not found.")

    plan.status = "pending_approval"
    run.status = "running"
    db.commit()
    
    # Rerun state machine starting at the planning_agent node
    from app.services.agent_orchestrator import MultiAgentOrchestrator
    orchestrator = MultiAgentOrchestrator()
    
    import threading
    thread = threading.Thread(target=orchestrator.execute_workflow, args=(run_id, "planning_agent"))
    thread.daemon = True
    thread.start()
    
    return {"message": "Regeneration triggered.", "status": "regenerating"}

@router.get("/{run_id}/diff")
def get_run_diff(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve code diff (files modified, lines added/removed, patch preview) for a run."""
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
        
    # Read persisted code_diff from AgentRun first
    diff_content = run.code_diff or ""
    
    # Try live workspace diff if DB record is empty
    if not diff_content:
        from app.services.workspace import WorkspaceManager
        try:
            diff_content = WorkspaceManager.get_diff(run.repository_id)
        except Exception as e:
            logger.error(f"Failed to get live git diff: {e}")
        
    # Fallback to stored implementation iteration diff if still clean (e.g. committed)
    if not diff_content:
        from app.models.extensions import ImplementationIteration
        latest_it = db.query(ImplementationIteration).filter(
            ImplementationIteration.run_id == run_id
        ).order_by(ImplementationIteration.iteration_number.desc()).first()
        if latest_it:
            diff_content = latest_it.code_diff
            
    files_modified = []
    lines_added = 0
    lines_removed = 0
    
    if diff_content:
        for line in diff_content.splitlines():
            if line.startswith("diff --git"):
                parts = line.split(" ")
                if len(parts) >= 4:
                    filename = parts[3].replace("b/", "")
                    if filename not in files_modified:
                        files_modified.append(filename)
            elif line.startswith("+") and not line.startswith("+++"):
                lines_added += 1
            elif line.startswith("-") and not line.startswith("---"):
                lines_removed += 1
                
    # Add payload logging to verify contents as requested
    logger.info(f"[/diff API] run_id={run_id} files_modified={len(files_modified)} lines_added={lines_added} lines_removed={lines_removed} commit_hash={run.commit_hash}")
                
    return {
        "run_id": run_id,
        "diff": diff_content,
        "files_modified": files_modified,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "commit_hash": run.commit_hash,
        "branch_name": run.branch_name
    }

@router.get("/{run_id}/context-metrics")
def get_context_metrics(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve semantic context retrieval quality metrics for a run."""
    from app.models.logs import AgentLog
    log = db.query(AgentLog).filter(
        AgentLog.agent_run_id == run_id,
        AgentLog.stage == "context",
        AgentLog.message.like("%Context retrieval finished%")
    ).first()
    
    if log and log.data and "retrieval_details" in log.data:
        return log.data["retrieval_details"]
        
    return []

