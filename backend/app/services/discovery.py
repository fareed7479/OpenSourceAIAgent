import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.repository import Repository
from app.models.issue import Issue
from app.models.settings import Setting
from app.services.ranking import evaluate_issue_difficulty_and_score

logger = logging.getLogger(__name__)

def parse_github_datetime(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        clean_str = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        return None

def discover_repository_issues_task(repo_id: str, github_token: str = None) -> None:
    """
    Scans a registered repository's open issues using GitHub API,
    filters them, calculates difficulty scores, and saves them to the DB.
    """
    db: Session = SessionLocal()
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            logger.error(f"Repository {repo_id} not found.")
            return

        # Check if user has preferred languages configured
        pref_langs = []
        user_langs_setting = db.query(Setting).filter(
            Setting.user_id == repo.user_id,
            Setting.key == "preferred_languages"
        ).first()
        if user_langs_setting:
            pref_langs = [l.strip() for l in user_langs_setting.value.split(",") if l.strip()]

        # Check if we are running in mock developer mode
        is_mock = github_token is None or github_token == "mock-github-access-token"
        
        if is_mock:
            logger.info(f"Mock issue discovery triggered for repository {repo.owner}/{repo.name}")
            _seed_mock_issues(db, repo, pref_langs)
            return

        # Check if issue tracker is disabled on fork and redirects upstream
        target_owner = repo.owner
        target_name = repo.name
        
        meta = repo.meta_info or {}
        gh_meta = meta.get("github_metadata", {})
        has_issues = gh_meta.get("has_issues", True)
        is_fork = gh_meta.get("fork", False)
        
        if not has_issues and is_fork:
            parent_info = gh_meta.get("parent")
            if parent_info:
                parent_owner = parent_info.get("owner", {}).get("login")
                parent_name = parent_info.get("name")
                if parent_owner and parent_name:
                    target_owner = parent_owner
                    target_name = parent_name
                    logger.info(f"Fork issues disabled. Redirecting issue sync to upstream: {target_owner}/{target_name}")

        # Fetch issues from GitHub API
        url = f"https://api.github.com/repos/{target_owner}/{target_name}/issues"
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OpenSource-AI-Contribution-Agent"
        }
        params = {
            "state": "all",
            "per_page": 100
        }
        
        logger.info(f"Fetching issues from {url}...")
        response = httpx.get(url, headers=headers, params=params, timeout=15.0)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch issues: {response.status_code} - {response.text}")
            return
            
        github_issues = response.json()
        saved_count = 0
        
        for gh_issue in github_issues:
            # GitHub API returns pull requests inside the issues endpoint. Filter them out.
            if "pull_request" in gh_issue:
                continue

            labels = [label.get("name", "") for label in gh_issue.get("labels", [])]
            title = gh_issue.get("title", "")
            body = gh_issue.get("body", "")
            number = gh_issue.get("number")
            issue_url = gh_issue.get("html_url")
            github_issue_id = gh_issue.get("id")

            # Parse extra fields
            author_username = gh_issue.get("user", {}).get("login")
            comments_count = gh_issue.get("comments", 0)
            github_created_at = parse_github_datetime(gh_issue.get("created_at"))
            github_updated_at = parse_github_datetime(gh_issue.get("updated_at"))
            status = gh_issue.get("state", "open")

            # Get assignee username and assignment status
            assignees_list = gh_issue.get("assignees", [])
            github_assignee = gh_issue.get("assignee")
            assignee_username = None
            if github_assignee:
                assignee_username = github_assignee.get("login")
            elif assignees_list:
                assignee_username = assignees_list[0].get("login")
                
            if assignee_username:
                if repo.user and repo.user.username and assignee_username.lower() == repo.user.username.lower():
                    assignment_status = "assigned_to_user"
                else:
                    assignment_status = "assigned_to_other"
            else:
                assignment_status = "unassigned"

            # Rank the issue
            eval_results = evaluate_issue_difficulty_and_score(
                title=title,
                body=body,
                labels=labels,
                repo_language=repo.language or "unknown",
                user_preferred_languages=pref_langs,
                comments_count=comments_count,
                github_created_at=github_created_at,
                assignment_status=assignment_status
            )

            # Parse source owner and source repo from issue_url
            source_owner, source_repo = None, None
            if issue_url:
                try:
                    parts = issue_url.replace("https://github.com/", "").split("/")
                    if len(parts) >= 2:
                        source_owner = parts[0]
                        source_repo = parts[1]
                except Exception as parse_err:
                    logger.warning(f"Failed to parse issue URL {issue_url}: {parse_err}")

            # Check if issue exists in database
            existing_issue = db.query(Issue).filter(
                Issue.repository_id == repo.id,
                Issue.github_issue_id == github_issue_id
            ).first()

            if existing_issue:
                # Update issue
                existing_issue.title = title
                existing_issue.description = body
                existing_issue.labels = labels
                existing_issue.difficulty = eval_results["difficulty"]
                existing_issue.score = eval_results["score"]
                existing_issue.ranking_reason = eval_results["ranking_reason"]
                existing_issue.status = status
                existing_issue.assignment_status = assignment_status
                existing_issue.assignee_username = assignee_username
                existing_issue.author_username = author_username
                existing_issue.github_created_at = github_created_at
                existing_issue.github_updated_at = github_updated_at
                existing_issue.comments_count = comments_count
                existing_issue.source_owner = source_owner
                existing_issue.source_repo = source_repo
            else:
                # Create issue
                new_issue = Issue(
                    repository_id=repo.id,
                    github_issue_id=github_issue_id,
                    number=number,
                    title=title,
                    description=body,
                    url=issue_url,
                    labels=labels,
                    difficulty=eval_results["difficulty"],
                    score=eval_results["score"],
                    ranking_reason=eval_results["ranking_reason"],
                    status=status,
                    assignment_status=assignment_status,
                    assignee_username=assignee_username,
                    author_username=author_username,
                    github_created_at=github_created_at,
                    github_updated_at=github_updated_at,
                    comments_count=comments_count,
                    source_owner=source_owner,
                    source_repo=source_repo
                )
                db.add(new_issue)
                
            saved_count += 1
            
        db.commit()
        logger.info(f"Discovered and saved {saved_count} issues for {repo.owner}/{repo.name}.")
        
    except Exception as e:
        logger.error(f"Error in discover_repository_issues_task: {e}")
    finally:
        db.close()


def _seed_mock_issues(db: Session, repo: Repository, pref_langs: List[str]) -> None:
    """Helper to seed mock issues for developer testing."""
    mock_data = [
        {
            "github_issue_id": 900001,
            "number": 1,
            "title": "fix: auth token validation crashes when token is empty",
            "body": "### Problem\nWhen the Authorization header is present but empty, the token parser throws a ValueError instead of returning a 401 response.\n\n### Steps to Reproduce\n1. Run API backend\n2. Send a request with `Authorization: Bearer `\n3. See server trace: `ValueError: token cannot be empty`\n\n### Expected Behavior\nShould raise HTTP 401 Unauthorized.\n\n### Files affected\n`app/core/security.py` or token parsing dependency.",
            "labels": ["bug", "backend", "security"],
            "url": f"{repo.url}/issues/1"
        },
        {
            "github_issue_id": 900002,
            "number": 2,
            "title": "feat: add user preferred language filter to issues dashboard",
            "body": "### Feature Request\nAdd a preference selector in the user settings UI to let developers specify their preferred languages (e.g. Python, JavaScript, TypeScript, Go). Show an indicator on the issues list highlighting issues that match these languages.\n\n### Tasks\n- Add UI elements in settings page\n- Update profile schemas\n- Sort issues list using language settings.",
            "labels": ["enhancement", "frontend", "elusoc", "good-first-issue"],
            "url": f"{repo.url}/issues/2"
        },
        {
            "github_issue_id": 900003,
            "number": 3,
            "title": "docs: update API documentation for repository registration endpoints",
            "body": "We need to document the new `/api/v1/repositories/register` endpoints. Include payloads, query parameters, responses, and example curl requests.\n\nUpdate `docs/API.md` and reference OAuth prerequisites.",
            "labels": ["documentation", "docs"],
            "url": f"{repo.url}/issues/3"
        }
    ]

    saved_count = 0
    for mock in mock_data:
        # Check if already seeded
        exists = db.query(Issue).filter(
            Issue.repository_id == repo.id,
            Issue.github_issue_id == mock["github_issue_id"]
        ).first()

        if not exists:
            eval_results = evaluate_issue_difficulty_and_score(
                title=mock["title"],
                body=mock["body"],
                labels=mock["labels"],
                repo_language=repo.language or "unknown",
                user_preferred_languages=pref_langs,
                comments_count=2,
                github_created_at=datetime.utcnow(),
                assignment_status="unassigned"
            )

            new_issue = Issue(
                repository_id=repo.id,
                github_issue_id=mock["github_issue_id"],
                number=mock["number"],
                title=mock["title"],
                description=mock["body"],
                url=mock["url"],
                labels=mock["labels"],
                difficulty=eval_results["difficulty"],
                score=eval_results["score"],
                ranking_reason=eval_results["ranking_reason"],
                status="open",
                assignment_status="unassigned",
                author_username="mock-author",
                github_created_at=datetime.utcnow(),
                github_updated_at=datetime.utcnow(),
                comments_count=2,
                source_owner=repo.owner,
                source_repo=repo.name
            )
            db.add(new_issue)
            saved_count += 1
            
    db.commit()
    logger.info(f"Seeded {saved_count} mock issues for repository {repo.owner}/{repo.name}.")
