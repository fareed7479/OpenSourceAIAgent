import httpx
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.encryption import decrypt_token
from app.models.pr import PullRequest
from app.schemas.pr import PullRequestResponse, PullRequestApproval
from app.api.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", response_model=List[PullRequestResponse])
def list_prs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all pull requests drafts/submissions for the current user."""
    from app.models.run import AgentRun
    prs = db.query(PullRequest).join(AgentRun).filter(AgentRun.user_id == current_user.id).all()
    return prs

@router.get("/{pr_id}", response_model=PullRequestResponse)
def get_pr(
    pr_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details of a specific pull request draft."""
    from app.models.run import AgentRun
    pr = db.query(PullRequest).join(AgentRun).filter(
        PullRequest.id == pr_id,
        AgentRun.user_id == current_user.id
    ).first()
    
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found."
        )
    return pr

@router.post("/{pr_id}/approve", response_model=PullRequestResponse)
async def approve_and_submit_pr(
    pr_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve the draft pull request and submit it to GitHub.
    Determines if it is a fork and creates a cross-repository PR if upstream exists.
    """
    from app.models.run import AgentRun
    from app.models.repository import Repository
    
    pr = db.query(PullRequest).join(AgentRun).filter(
        PullRequest.id == pr_id,
        AgentRun.user_id == current_user.id
    ).first()
    
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found."
        )
        
    if pr.status == "submitted":
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pull request has already been submitted."
        )

    run = pr.agent_run
    repo = run.repository
    issue = run.issue
    
    decrypted_token = decrypt_token(current_user.access_token)
    is_mock = current_user.github_id.startswith("mock-") or decrypted_token == "mock-github-access-token"
    
    if is_mock:
        logger.info(f"[Mock Mode] Simulating PR creation on GitHub for branch: {run.branch_name}")
        pr.status = "submitted"
        pr.approval_status = "approved"
        pr.url = f"https://github.com/{repo.owner}/{repo.name}/pull/{issue.number + 50}"
        pr.github_pr_id = 100000 + issue.number
        
        # Save human feedback & learning signal
        from app.models.extensions import FeedbackHistory, LearningSignal
        feedback = FeedbackHistory(
            repository_id=repo.id,
            user_id=current_user.id,
            action="approve",
            feedback_text="PR approved by human reviewer."
        )
        db.add(feedback)
        signal = LearningSignal(
            repository_id=repo.id,
            signal_type="preference",
            description="User approved PR style and implementations.",
            strength=1.0
        )
        db.add(signal)
        
        db.commit()
        return pr

    # Production GitHub API PR submission
    # Check if this repository was forked from a parent repo (upstream)
    target_owner = repo.owner
    target_name = repo.name
    
    # Check parent details stored in meta_info (e.g. from GitHub API in register repository)
    if repo.meta_info and "parent" in repo.meta_info:
        parent_info = repo.meta_info["parent"]
        target_owner = parent_info.get("owner", {}).get("login", repo.owner)
        target_name = parent_info.get("name", repo.name)
        
    url = f"https://api.github.com/repos/{target_owner}/{target_name}/pulls"
    headers = {
        "Authorization": f"token {decrypted_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "OpenSource-AI-Contribution-Agent"
    }
    
    # Format of head: "owner:branch" (since it's a cross-repo PR from fork)
    head_branch = f"{repo.owner}:{run.branch_name}"
    
    payload = {
        "title": pr.title,
        "body": pr.description,
        "head": head_branch,
        "base": repo.branch,  # e.g. main/master
        "draft": False
    }
    
    logger.info(f"Submitting PR to GitHub: {url} | head: {head_branch}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=15.0)
            
        if response.status_code != 201:
            logger.error(f"GitHub PR creation failed ({response.status_code}): {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to submit Pull Request on GitHub: {response.text}"
            )
            
        pr_data = response.json()
        
        # Update database record
        pr.status = "submitted"
        pr.approval_status = "approved"
        pr.url = pr_data.get("html_url")
        pr.github_pr_id = pr_data.get("id")
        
        # Save human feedback & learning signal
        from app.models.extensions import FeedbackHistory, LearningSignal
        feedback = FeedbackHistory(
            repository_id=repo.id,
            user_id=current_user.id,
            action="approve",
            feedback_text="PR approved by human reviewer."
        )
        db.add(feedback)
        signal = LearningSignal(
            repository_id=repo.id,
            signal_type="preference",
            description="User approved PR style and implementations.",
            strength=1.0
        )
        db.add(signal)
        
        db.commit()
        
        logger.info(f"PR submitted successfully. HTML URL: {pr.url}")
        return pr
        
    except httpx.HTTPError as err:
        logger.error(f"HTTP request to GitHub failed: {err}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to communicate with GitHub API."
        )

@router.post("/{pr_id}/reject", response_model=PullRequestResponse)
def reject_pr(
    pr_id: str,
    payload: PullRequestApproval,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject the draft PR, writing review feedback."""
    from app.models.run import AgentRun
    pr = db.query(PullRequest).join(AgentRun).filter(
        PullRequest.id == pr_id,
        AgentRun.user_id == current_user.id
    ).first()
    
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pull request not found."
        )
        
    pr.approval_status = "rejected"
    pr.status = "draft"
    if payload.feedback:
        # Append feedback to review status field
        pr.review_status = f"{pr.review_status or ''}\n\n### User Reject Feedback\n{payload.feedback}"
        
        # Save human feedback & learning signal
        from app.models.extensions import FeedbackHistory, LearningSignal
        feedback = FeedbackHistory(
            repository_id=pr.agent_run.repository_id,
            user_id=current_user.id,
            action="reject",
            feedback_text=payload.feedback
        )
        db.add(feedback)
        signal = LearningSignal(
            repository_id=pr.agent_run.repository_id,
            signal_type="review_pattern",
            description=f"User rejected PR with feedback: {payload.feedback}",
            strength=2.0
        )
        db.add(signal)
        
    db.commit()
    return pr
