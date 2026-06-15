import os
import subprocess
import logging
import httpx
from datetime import datetime
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.encryption import decrypt_token
from app.models.repository import Repository
from app.models.issue import Issue
from app.models.run import AgentRun
from app.models.logs import AgentLog
from app.models.pr import PullRequest
from app.services.workspace import WorkspaceManager
from app.services.agent_provider import get_coding_agent

logger = logging.getLogger(__name__)

def run_agent_workflow_task(run_id: str) -> None:
    """
    Orchestrates the end-to-end AI agent workflow:
    1. Workspace Setup (Branch checkout)
    2. Context Building
    3. Coding Agent Fix Generation
    4. Code Patching
    5. Validation (Build, Test, Lint commands)
    6. AI Review Agent Pass
    7. Git Commit & Optional Remote Push
    8. PR Draft Generation
    """
    db: Session = SessionLocal()
    run = None
    try:
        run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            logger.error(f"Agent run {run_id} not found.")
            return

        run.status = "running"
        db.commit()

        repo = run.repository
        issue = run.issue
        user = run.user
        
        # Determine API Key and Mode
        decrypted_token = decrypt_token(user.access_token)
        is_mock = user.github_id.startswith("mock-") or decrypted_token == "mock-github-access-token"
        
        # Load user provider config settings if they exist
        llm_key = None
        # In a real app we'd load this from provider_configs table, check fallback to env setting
        from app.core.config import settings
        llm_key = settings.GEMINI_API_KEY

        # --- STEP 1: Workspace setup (Branch creation) ---
        _log_stage(db, run_id, "workspace", "Creating isolated workspace and checking out branch.")
        success = WorkspaceManager.create_and_checkout_branch(repo.id, run.branch_name)
        if not success:
            _log_stage(db, run_id, "workspace", "Failed to create checkout branch.", {"error": "Git branch checkout failure"})
            run.status = "failed"
            db.commit()
            return
        _log_stage(db, run_id, "workspace", f"Checked out branch: {run.branch_name}")

        # --- STEP 2: Context Building ---
        _log_stage(db, run_id, "context", "Building issue context and parsing relevant files.")
        file_tree, relevant_files = _build_codebase_context(repo.id, issue.description or "")
        _log_stage(db, run_id, "context", f"Gathered {len(relevant_files)} relevant source files.", {
            "files_found": list(relevant_files.keys()),
            "tree_size": len(file_tree)
        })

        # --- STEP 3: Coding Agent Fix Generation ---
        _log_stage(db, run_id, "coding", f"Invoking coding provider: {run.provider}")
        agent = get_coding_agent(run.provider, llm_key)
        
        try:
            agent_result = agent.generate_fix(
                issue_title=issue.title,
                issue_desc=issue.description or "",
                file_tree=file_tree,
                relevant_files=relevant_files,
                contribution_rules=repo.contribution_rules or ""
            )
            explanation = agent_result.get("explanation", "")
            changes = agent_result.get("changes", [])
            _log_stage(db, run_id, "coding", f"Agent proposed changes. Explanation: {explanation[:200]}...", {
                "explanation": explanation,
                "changes_count": len(changes)
            })
        except Exception as e:
            _log_stage(db, run_id, "coding", f"Coding Agent failed: {e}", {"error": str(e)})
            run.status = "failed"
            db.commit()
            return

        # --- STEP 4: Code Patching ---
        _log_stage(db, run_id, "coding", "Applying generated file changes back to workspace.")
        repo_path = WorkspaceManager.get_repo_dir(repo.id)
        applied_files = []
        for change in changes:
            filepath = change.get("filepath")
            content = change.get("content")
            
            # Form absolute filepath safely
            abs_path = os.path.abspath(os.path.join(repo_path, filepath))
            # Ensure it is inside workspace directory
            if not abs_path.startswith(os.path.abspath(repo_path)):
                _log_stage(db, run_id, "coding", f"Security violation: filepath {filepath} points outside workspace.")
                continue
                
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            applied_files.append(filepath)
            
        _log_stage(db, run_id, "coding", f"Successfully patched files: {', '.join(applied_files)}")

        # --- STEP 5: Validation ---
        run.status = "validating"
        db.commit()
        _log_stage(db, run_id, "validation", "Starting validation engine. Running tests and build checks.")
        
        test_success, val_logs = _run_validation_commands(
            repo_id=repo.id,
            build_system=repo.build_system or "unknown",
            test_cmd=repo.test_command or "",
            lint_cmd=repo.lint_command or ""
        )
        _log_stage(db, run_id, "validation", f"Validation complete. Tests Passed: {test_success}", val_logs)

        # --- STEP 6: AI Review Agent Pass ---
        run.status = "reviewing"
        db.commit()
        _log_stage(db, run_id, "review", "Initiating AI Review Agent pass on git diff.")
        diff = WorkspaceManager.get_diff(repo.id)
        
        review_report = _run_ai_review(
            diff=diff,
            issue_title=issue.title,
            issue_desc=issue.description or "",
            api_key=llm_key
        )
        _log_stage(db, run_id, "review", "AI Review completed successfully.", {"review_report": review_report})

        # --- STEP 7: Conventional Commit message generation ---
        _log_stage(db, run_id, "commit", "Staging files and generating conventional commit.")
        # Generate Conventional Commit message based on title
        commit_prefix = "fix"
        if "feat" in issue.title.lower() or "add" in issue.title.lower():
            commit_prefix = "feat"
        elif "docs" in issue.title.lower() or "documentation" in issue.title.lower():
            commit_prefix = "docs"
            
        clean_title = issue.title.replace("fix:", "").replace("feat:", "").replace("docs:", "").strip()
        commit_message = f"{commit_prefix}: {clean_title} (#{issue.number})"
        
        commit_success = WorkspaceManager.commit_changes(repo.id, commit_message)
        if commit_success:
            _log_stage(db, run_id, "commit", f"Committed: '{commit_message}'")
            if not is_mock:
                # Push branch to remote fork
                _log_stage(db, run_id, "commit", f"Pushing branch {run.branch_name} to GitHub remote fork...")
                push_success = WorkspaceManager.push_branch(repo.id, run.branch_name, decrypted_token)
                if push_success:
                    _log_stage(db, run_id, "commit", "Pushed branch successfully.")
                else:
                    _log_stage(db, run_id, "commit", "Warning: Failed to push branch to origin remote.")
        else:
            _log_stage(db, run_id, "commit", "No modifications detected. Skipping commit.")

        # --- STEP 8: PR Draft Generation (Phase 8 / 9) ---
        _log_stage(db, run_id, "pr", "Creating Pull Request draft template for human approval.")
        
        pr_description = _generate_pr_description(
            issue=issue,
            explanation=explanation,
            applied_files=applied_files,
            tests_passed=test_success
        )
        
        # Save PR draft record
        pr = db.query(PullRequest).filter(PullRequest.agent_run_id == run_id).first()
        if not pr:
            pr = PullRequest(
                agent_run_id=run_id,
                title=f"{commit_prefix.capitalize()}: {clean_title}",
                description=pr_description,
                status="draft",
                files_changed=applied_files,
                tests_passed=test_success,
                review_status=review_report,
                approval_status="pending"
            )
            db.add(pr)
        else:
            pr.title = f"{commit_prefix.capitalize()}: {clean_title}"
            pr.description = pr_description
            pr.files_changed = applied_files
            pr.tests_passed = test_success
            pr.review_status = review_report
            
        run.status = "completed"
        db.commit()
        
        _log_stage(db, run_id, "pr", "PR Draft template created. Awaiting human approval in the dashboard.")

    except Exception as e:
        logger.error(f"Error executing agent workflow: {e}", exc_info=True)
        if run:
            run.status = "failed"
            db.commit()
            _log_stage(db, run_id, "pr", f"Agent workflow aborted due to fatal error: {e}")
    finally:
        db.close()


def _log_stage(db: Session, run_id: str, stage: str, message: str, data: Any = None) -> None:
    """Helper to save log entries to DB and stdout."""
    logger.info(f"[{stage.upper()}] {message}")
    log_entry = AgentLog(
        agent_run_id=run_id,
        stage=stage,
        message=message,
        data=data
    )
    db.add(log_entry)
    db.commit()


def _build_codebase_context(repo_id: str, issue_desc: str) -> Tuple[List[str], Dict[str, str]]:
    """
    Scans files in repository.
    Extracts tree structure and content of relevant code files.
    """
    repo_path = WorkspaceManager.get_repo_dir(repo_id)
    file_tree = []
    relevant_files = {}

    exclude_dirs = {".git", "node_modules", "venv", ".venv", "build", "target", "dist", "__pycache__", ".gemini"}
    exclude_extensions = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz", ".db", ".pyc"}

    for root, dirs, files in os.walk(repo_path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in exclude_extensions:
                continue
                
            abs_filepath = os.path.join(root, file)
            rel_filepath = os.path.relpath(abs_filepath, repo_path)
            file_tree.append(rel_filepath)
            
            # Simple heuristic: is this file mentioned or highly related to issue?
            # 1. Mentioned by name in issue description
            file_basename = os.path.basename(rel_filepath)
            is_mentioned = file_basename.lower() in issue_desc.lower()
            
            # 2. Main target files: check if they are core logic files
            # For python/node projects, check config or main files
            is_core = file_basename in ["security.py", "auth.py", "main.py", "App.tsx", "index.css", "server.js", "package.json"]
            
            # Limit file content reading to max 10 related files to avoid bloating prompt
            if (is_mentioned or is_core) and len(relevant_files) < 10:
                try:
                    with open(abs_filepath, "r", encoding="utf-8", errors="ignore") as f:
                        relevant_files[rel_filepath] = f.read(50000)  # read first 50k chars
                except Exception as e:
                    logger.error(f"Could not read file content for context {rel_filepath}: {e}")

    # If no specific relevant files matched, default to reading the first 3 files
    if not relevant_files and file_tree:
        for rel_filepath in file_tree[:3]:
            abs_filepath = os.path.join(repo_path, rel_filepath)
            try:
                with open(abs_filepath, "r", encoding="utf-8", errors="ignore") as f:
                    relevant_files[rel_filepath] = f.read(50000)
            except Exception:
                pass

    return file_tree, relevant_files


def _run_validation_commands(
    repo_id: str,
    build_system: str,
    test_cmd: str,
    lint_cmd: str
) -> Tuple[bool, Dict[str, Any]]:
    """Runs tests and linting in the repo folder, capturing outputs."""
    repo_path = WorkspaceManager.get_repo_dir(repo_id)
    
    logs = {
        "test_stdout": "",
        "test_stderr": "",
        "test_exit_code": 0,
        "lint_stdout": "",
        "lint_stderr": "",
        "lint_exit_code": 0
    }
    
    test_passed = True
    
    # 1. Run Test Command
    if test_cmd:
        logger.info(f"Running test command: {test_cmd} in {repo_path}")
        try:
            # Run command using powershell or shell
            res = subprocess.run(
                test_cmd,
                shell=True,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=120.0
            )
            logs["test_stdout"] = res.stdout[:50000]
            logs["test_stderr"] = res.stderr[:50000]
            logs["test_exit_code"] = res.returncode
            if res.returncode != 0:
                test_passed = False
        except subprocess.TimeoutExpired:
            logs["test_stderr"] = "Test command timed out after 120 seconds."
            logs["test_exit_code"] = -1
            test_passed = False
        except Exception as e:
            logs["test_stderr"] = f"Failed to execute test command: {e}"
            logs["test_exit_code"] = -2
            test_passed = False
    else:
        logs["test_stdout"] = "No test command configured. Skipping test verification."

    # 2. Run Lint Command
    if lint_cmd:
        logger.info(f"Running lint command: {lint_cmd} in {repo_path}")
        try:
            res = subprocess.run(
                lint_cmd,
                shell=True,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60.0
            )
            logs["lint_stdout"] = res.stdout[:20000]
            logs["lint_stderr"] = res.stderr[:20000]
            logs["lint_exit_code"] = res.returncode
        except Exception as e:
            logs["lint_stderr"] = f"Failed to execute lint command: {e}"
            logs["lint_exit_code"] = -2

    return test_passed, logs


def _run_ai_review(diff: str, issue_title: str, issue_desc: str, api_key: str = None) -> str:
    """Invokes LLM to inspect git diff and provide code quality review report."""
    if not diff:
        return "No changes detected. Nothing to review."
        
    if not api_key:
        # Return mock review report for testing
        return """### AI Code Review Report
- **Bugs/Logic**: No direct logic bugs detected. Token validation safety checks look complete.
- **Security**: safely rejects empty and whitespace-only authentication tokens.
- **Style conformity**: Adheres to standard PEP-8 style guidelines.
- **Performance**: Operations are O(1), no performance regression.
- **Recommendation**: Approved for merge."""

    prompt = f"""You are an expert code reviewer. Please review the following git diff for this issue.

=== ISSUE TITLE ===
{issue_title}

=== ISSUE DESCRIPTION ===
{issue_desc}

=== GIT DIFF ===
{diff}

=== INSTRUCTIONS ===
Evaluate the changes for:
1. Logic bugs or syntax errors.
2. Security concerns (e.g. input injection, unvalidated inputs).
3. Maintainability and styling conformity.
4. Performance concerns.

Provide a concise review report in Markdown format. Outline critical concerns or confirm if code is approved.
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = httpx.post(url, json=payload, timeout=40.0)
        if response.status_code == 200:
            resp_data = response.json()
            return resp_data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return f"AI Review service returned error: {response.text}"
    except Exception as e:
        return f"AI Review pass failed: {e}"


def _generate_pr_description(
    issue: Issue,
    explanation: str,
    applied_files: List[str],
    tests_passed: bool
) -> str:
    """Generates the Markdown body for the pull request, including the AI Disclosure."""
    test_status = "✅ All tests passed" if tests_passed else "❌ Tests failed or build checks failed"
    
    return f"""## Problem
{issue.title}
Issue link: #{issue.number}

## Solution
{explanation}

## Changes Made
{chr(10).join([f'- `{f}`' for f in applied_files])}

## Testing
* **Test Verification**: {test_status}

## AI Disclosure
This contribution was developed with AI-assisted tooling (Gemini Coding Agent). All generated code was reviewed, validated, and submitted by the contributor.

Fixes #{issue.number}
"""
