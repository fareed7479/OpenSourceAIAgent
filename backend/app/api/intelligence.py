import os
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.issue import Issue
from app.models.repository import Repository
from app.models.extensions import CodeSearchIndex, RepositoryMemory, AgentTask, LearningSignal, FeedbackHistory, ImplementationIteration, QualityMetric, RepairAttempt
from app.api.deps import get_current_user
from app.models.user import User
from app.services.intelligence import query_semantic_code_search

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/elusoc", status_code=status.HTTP_200_OK)
def get_elusoc_dashboard_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all ELUSOC-eligible issues across user registered repositories,
    sorted by score priority, along with aggregate metrics for the dashboard.
    """
    # Query all repositories belonging to the user
    user_repos = db.query(Repository).filter(Repository.user_id == current_user.id).all()
    repo_ids = [r.id for r in user_repos]
    
    if not repo_ids:
        return {
            "issues": [],
            "metrics": {
                "total_eligible": 0,
                "easy_count": 0,
                "medium_count": 0,
                "hard_count": 0,
                "completed_prs": 0
            }
        }
        
    # Fetch issues belonging to these repositories that are open
    # and have ELUSOC labels or fit ELUSOC criteria
    issues = db.query(Issue).filter(
        Issue.repository_id.in_(repo_ids),
        Issue.status == "open"
    ).all()
    
    # Filter issues that contain 'elusoc', 'good-first-issue', 'bug', etc.
    elusoc_issues = []
    easy_count = 0
    medium_count = 0
    hard_count = 0
    
    for issue in issues:
        # Match case-insensitive label names
        labels_lower = [l.lower() for l in issue.labels]
        is_eligible = any(
            x in labels_lower 
            for x in ["elusoc", "good-first-issue", "good first issue", "bug", "enhancement"]
        )
        
        if is_eligible or issue.score >= 50:
            elusoc_issues.append(issue)
            if issue.difficulty == "easy":
                easy_count += 1
            elif issue.difficulty == "hard":
                hard_count += 1
            else:
                medium_count += 1
                
    # Sort by score descending (highest priority recommended first)
    elusoc_issues.sort(key=lambda x: x.score, reverse=True)
    
    # Get completed PRs
    from app.models.pr import PullRequest
    from app.models.run import AgentRun
    completed_prs = db.query(PullRequest).join(AgentRun).filter(
        AgentRun.user_id == current_user.id,
        PullRequest.status == "submitted"
    ).count()
    
    return {
        "issues": [
            {
                "id": i.id,
                "repository_name": db.query(Repository).filter(Repository.id == i.repository_id).first().name,
                "number": i.number,
                "title": i.title,
                "difficulty": i.difficulty,
                "score": i.score,
                "labels": i.labels,
                "status": i.status,
                "assignment_status": i.assignment_status,
                "url": i.url
            } for i in elusoc_issues
        ],
        "metrics": {
            "total_eligible": len(elusoc_issues),
            "easy_count": easy_count,
            "medium_count": medium_count,
            "hard_count": hard_count,
            "completed_prs": completed_prs
        }
    }

@router.get("/repo/{repo_id}/symbols", status_code=status.HTTP_200_OK)
def get_repository_symbols_map(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve indexed symbol map and code relationships for visualizer page."""
    # Verify access
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
        
    symbols = db.query(CodeSearchIndex).filter(
        CodeSearchIndex.repository_id == repo_id
    ).all()
    
    # Structure symbols grouped by file
    symbols_by_file: Dict[str, List[Dict[str, Any]]] = {}
    for s in symbols:
        if s.filepath not in symbols_by_file:
            symbols_by_file[s.filepath] = []
        symbols_by_file[s.filepath].append({
            "name": s.symbol_name,
            "type": s.symbol_type,
            "lines": f"{s.start_line}-{s.end_line}"
        })
        
    return {
        "repository_id": repo_id,
        "files_count": len(symbols_by_file),
        "symbols_count": len(symbols),
        "codebase_map": [
            {
                "filepath": path,
                "symbols": syms
            } for path, syms in symbols_by_file.items()
        ]
    }

@router.get("/repo/{repo_id}/memory", status_code=status.HTTP_200_OK)
def get_repository_memory(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve long-term memory patterns and maintainer preferences."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
        
    memories = db.query(RepositoryMemory).filter(
        RepositoryMemory.repository_id == repo_id
    ).order_by(RepositoryMemory.created_at.desc()).all()
    
    return [
        {
            "id": m.id,
            "key": m.key,
            "value": m.value,
            "memory_type": m.memory_type,
            "created_at": m.created_at
        } for m in memories
    ]

@router.get("/repo/{repo_id}/search", status_code=status.HTTP_200_OK)
def perform_semantic_search(
    repo_id: str,
    query: str = Query(..., min_length=2),
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Execute vector embedding semantic similarity search in codebase."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
        
    return query_semantic_code_search(repo_id, query, limit)

@router.get("/repo/{repo_id}/learning", status_code=status.HTTP_200_OK)
def get_learning_and_feedback(
    repo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve learning signals and feedback history logs for audit."""
    repo = db.query(Repository).filter(
        Repository.id == repo_id,
        Repository.user_id == current_user.id
    ).first()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
        
    signals = db.query(LearningSignal).filter(
        LearningSignal.repository_id == repo_id
    ).all()
    
    feedback = db.query(FeedbackHistory).filter(
        FeedbackHistory.repository_id == repo_id
    ).all()
    
    return {
        "learning_signals": [
            {
                "id": s.id,
                "type": s.signal_type,
                "description": s.description,
                "strength": s.strength,
                "created_at": s.created_at
            } for s in signals
        ],
        "feedback_history": [
            {
                "id": f.id,
                "action": f.action,
                "feedback": f.feedback_text,
                "diff_preview": f.code_diff[:400] if f.code_diff else None,
                "created_at": f.created_at
            } for f in feedback
        ]
    }

@router.get("/run/{run_id}/timeline", status_code=status.HTTP_200_OK)
def get_run_timeline_tasks(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve detailed agent nodes execution timeline task log list for tracing."""
    tasks = db.query(AgentTask).filter(
        AgentTask.run_id == run_id
    ).order_by(AgentTask.created_at.asc()).all()
    
    # Load quality metrics and iterations if present
    from app.models.extensions import AgentReview
    
    iterations = db.query(ImplementationIteration).filter(
        ImplementationIteration.run_id == run_id
    ).order_by(ImplementationIteration.iteration_number.asc()).all()
    
    metrics = db.query(QualityMetric).filter(
        QualityMetric.run_id == run_id
    ).first()
    
    attempts = db.query(RepairAttempt).filter(
        RepairAttempt.run_id == run_id
    ).order_by(RepairAttempt.attempt_number.asc()).all()
    
    return {
        "run_id": run_id,
        "timeline": [
            {
                "id": t.id,
                "task_name": t.task_name,
                "description": t.description,
                "assignee": t.assignee,
                "status": t.status,
                "result": t.result,
                "created_at": t.created_at,
                "updated_at": t.updated_at
            } for t in tasks
        ],
        "healing_attempts": [
            {
                "attempt_number": a.attempt_number,
                "error_message": a.error_message,
                "planned_fix": a.planned_fix,
                "status": a.status,
                "created_at": a.created_at
            } for a in attempts
        ],
        "iterations": [
            {
                "iteration_number": it.iteration_number,
                "explanation": it.explanation,
                "code_diff": it.code_diff,
                "test_passed": it.test_passed,
                "created_at": it.created_at
            } for it in iterations
        ],
        "quality_metrics": {
            "security": metrics.security_score if metrics else 0,
            "performance": metrics.performance_score if metrics else 0,
            "style": metrics.style_score if metrics else 0,
            "overall": metrics.overall_score if metrics else 0
        } if metrics else None
    }
