import os
import hmac
import hashlib
import json
import logging
from fastapi import APIRouter, Header, Request, HTTPException, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.models.extensions import WebhookEvent
from app.models.repository import Repository
from app.models.issue import Issue
from app.services.ranking import evaluate_issue_difficulty_and_score
from app.services.agent_orchestrator import MultiAgentOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter()

# Get webhook secret from env settings
WEBHOOK_SECRET = settings.GITHUB_WEBHOOK_SECRET

async def verify_signature(request: Request, x_hub_signature_256: str = Header(None)):
    """Verifies that the webhook payload is signed with the correct secret."""
    if not x_hub_signature_256:
        logger.warning("Missing X-Hub-Signature-256 header in webhook delivery.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature validation header missing."
        )
        
    # Read raw body bytes
    body = await request.body()
    
    # Compute signature hash
    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + mac.hexdigest()
    
    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        logger.error("HMAC-SHA256 signature verification failed for webhook event.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="HMAC signature verification failed."
        )

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook_receiver(
    request: Request,
    x_github_delivery: str = Header(...),
    x_github_event: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint receiving GitHub Webhooks.
    Validates delivery signatures, logs payloads, and triggers background task runners.
    """
    # Verify HMAC signature
    await verify_signature(request, request.headers.get("x-hub-signature-256", ""))
    
    # Read payload
    payload = await request.json()
    
    # Log webhook delivery event
    event = db.query(WebhookEvent).filter(WebhookEvent.github_delivery_id == x_github_delivery).first()
    if event:
        return {"message": "Event delivery already processed."}
        
    event = WebhookEvent(
        github_delivery_id=x_github_delivery,
        event_type=x_github_event,
        payload=payload,
        status="received"
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    try:
        # Process specific GitHub webhook events
        if x_github_event == "issues":
            action = payload.get("action")
            issue_data = payload.get("issue", {})
            repo_data = payload.get("repository", {})
            
            repo_owner = repo_data.get("owner", {}).get("login")
            repo_name = repo_data.get("name")
            
            # Check if this repository is registered in our platform
            repo = db.query(Repository).filter(
                Repository.owner == repo_owner,
                Repository.name == repo_name
            ).first()
            
            if repo:
                github_issue_id = issue_data.get("id")
                number = issue_data.get("number")
                title = issue_data.get("title", "")
                body = issue_data.get("body", "")
                issue_url = issue_data.get("html_url")
                labels = [l.get("name") for l in issue_data.get("labels", [])]
                
                # Check assignee
                assignee = issue_data.get("assignee")
                assignee_username = assignee.get("login") if assignee else None
                
                # Filter: skip pull requests
                if "pull_request" not in issue_data:
                    # Difficulty & scoring heuristics
                    evals = evaluate_issue_difficulty_and_score(
                        title=title,
                        body=body,
                        labels=labels,
                        repo_language=repo.language or "unknown"
                    )
                    
                    # Search if issue exists in database
                    db_issue = db.query(Issue).filter(
                        Issue.repository_id == repo.id,
                        Issue.github_issue_id == github_issue_id
                    ).first()
                    
                    if not db_issue:
                        db_issue = Issue(
                            repository_id=repo.id,
                            github_issue_id=github_issue_id,
                            number=number,
                            title=title,
                            description=body,
                            url=issue_url,
                            labels=labels,
                            difficulty=evals["difficulty"],
                            score=evals["score"],
                            ranking_reason=evals["ranking_reason"],
                            status="open"
                        )
                        db.add(db_issue)
                    else:
                        db_issue.title = title
                        db_issue.description = body
                        db_issue.labels = labels
                        db_issue.difficulty = evals["difficulty"]
                        db_issue.score = evals["score"]
                        db_issue.ranking_reason = evals["ranking_reason"]
                        db_issue.status = "open" if action != "closed" else "closed"

                    # If issue is assigned to our logged-in user, auto-trigger implementation run!
                    if action == "assigned" and assignee_username == repo.user.username:
                        db_issue.assignment_status = "assigned_to_user"
                        db_issue.assignee_username = assignee_username
                        db.commit()
                        
                        # Create Run & Trigger State Machine Orchestrator
                        from app.services.assignment import _trigger_agent_run
                        _trigger_agent_run(db, repo.id, db_issue.id, repo.user_id)
                    elif action == "unassigned" or (assignee_username and assignee_username != repo.user.username):
                        db_issue.assignment_status = "assigned_to_other" if assignee_username else "unassigned"
                        db_issue.assignee_username = assignee_username
                        
                    db.commit()
                    
        event.status = "processed"
        db.commit()
        
    except Exception as e:
        logger.error(f"Failed to process webhook event delivery {x_github_delivery}: {e}")
        event.status = "failed"
        event.error_message = str(e)
        db.commit()
        
    return {"message": "Webhook processed successfully."}
