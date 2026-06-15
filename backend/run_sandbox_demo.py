import os
import sys
import shutil
import json
import logging
import subprocess
import stat
from unittest.mock import patch, MagicMock

# Add current directory to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Now import app modules
from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.models.repository import Repository
from app.models.issue import Issue
from app.models.run import AgentRun
from app.models.user import User
from app.models.logs import AgentLog
from app.models.pr import PullRequest
from app.models.extensions import AgentPlan, RepairAttempt, ImplementationIteration, QualityMetric, AgentState, AgentTask, AgentReview
from app.services.agent_orchestrator import MultiAgentOrchestrator
from app.services.workspace import WorkspaceManager

# Setup directory paths
SANDBOX_DIR = WorkspaceManager.get_repo_dir("opensource-agent-sandbox")

def rmtree_force(dir_path):
    if not os.path.exists(dir_path):
        return
    for root, dirs, files in os.walk(dir_path, topdown=False):
        for name in files:
            file_path = os.path.join(root, name)
            try:
                os.chmod(file_path, stat.S_IWRITE)
                os.unlink(file_path)
            except Exception:
                pass
        for name in dirs:
            dir_path_item = os.path.join(root, name)
            try:
                os.chmod(dir_path_item, stat.S_IWRITE)
                os.rmdir(dir_path_item)
            except Exception:
                pass
    try:
        os.chmod(dir_path, stat.S_IWRITE)
        os.rmdir(dir_path)
    except Exception:
        pass

def setup_sandbox_repo():
    print("Setting up sandbox repository...")
    if os.path.exists(SANDBOX_DIR):
        rmtree_force(SANDBOX_DIR)
    os.makedirs(SANDBOX_DIR, exist_ok=True)

    # 1. Create calculator.py (contains bug)
    calc_path = os.path.join(SANDBOX_DIR, "calculator.py")
    with open(calc_path, "w", encoding="utf-8") as f:
        f.write("""def divide(a, b):
    # Bug: does not raise ValueError on zero divisor
    return a / b
""")

    # 2. Create test_calculator.py
    test_path = os.path.join(SANDBOX_DIR, "test_calculator.py")
    with open(test_path, "w", encoding="utf-8") as f:
        f.write("""import sys
from calculator import divide

try:
    assert divide(6, 3) == 2
    try:
        divide(6, 0)
        print("Test failed: expected ValueError or ZeroDivisionError handling")
        sys.exit(1)
    except ValueError:
        pass
    print("Tests passed successfully!")
    sys.exit(0)
except Exception as e:
    print(f"Test execution crashed/failed: {e}")
    sys.exit(1)
""")

    # Initialize Git
    subprocess.run(["git", "init"], cwd=SANDBOX_DIR, check=True)
    subprocess.run(["git", "config", "user.name", "Demo Contributor"], cwd=SANDBOX_DIR, check=True)
    subprocess.run(["git", "config", "user.email", "demo@example.com"], cwd=SANDBOX_DIR, check=True)
    subprocess.run(["git", "add", "."], cwd=SANDBOX_DIR, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit of calculator module"], cwd=SANDBOX_DIR, check=True)
    print(f"Sandbox repository initialized at: {SANDBOX_DIR}")

def setup_database_entries():
    print("Configuring database mock entries...")
    db = SessionLocal()
    try:
        # Clear old trace tables to keep database completely clean
        db.query(AgentState).delete()
        db.query(AgentTask).delete()
        db.query(AgentPlan).delete()
        db.query(AgentReview).delete()
        db.query(RepairAttempt).delete()
        db.query(ImplementationIteration).delete()
        db.query(QualityMetric).delete()
        db.query(PullRequest).delete()
        db.query(AgentRun).delete()
        db.query(Issue).delete()
        db.query(Repository).delete()
        db.query(User).delete()
        db.commit()

        # Create user
        user = User(
            id="demo-user-id",
            username="demo-user",
            github_id="mock-user-123",
            access_token="mock-github-access-token"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create repo with ID set to "opensource-agent-sandbox"
        repo = Repository(
            id="opensource-agent-sandbox",
            user_id=user.id,
            owner="demo-user",
            name="opensource-agent-sandbox",
            url="local://opensource-agent-sandbox",
            status="cloned",
            build_system="custom",
            test_command="python test_calculator.py",
            lint_command="python -m py_compile calculator.py"
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

        # Create issue
        issue = Issue(
            id="opensource-agent-sandbox-issue",
            repository_id=repo.id,
            github_issue_id=98765,
            number=42,
            title="Fix division by zero crash in divide function",
            description="The divide function in calculator.py crashes with a ZeroDivisionError when the divisor b is 0. It should raise a ValueError instead.",
            url="https://github.com/demo-user/opensource-agent-sandbox/issues/42",
            difficulty="easy",
            score=90,
            assignment_status="assigned_to_user",
            assignee_username="demo-user",
            status="open"
        )
        db.add(issue)
        db.commit()
        db.refresh(issue)

        # Create run
        run = AgentRun(
            repository_id=repo.id,
            issue_id=issue.id,
            user_id=user.id,
            branch_name="issue-42-fix-division-by-zero",
            provider="jules",  # Jules is default primary provider!
            status="pending"
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        return run.id, repo.id
    finally:
        db.close()

# Mock responses helper
class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    @property
    def text(self):
        return json.dumps(self.json_data)

def mock_httpx_post(url, *args, **kwargs):
    payload = kwargs.get("json", {})
    text_content = ""
    try:
        text_content = payload["contents"][0]["parts"][0]["text"]
    except (KeyError, IndexError):
        pass

    # 1. Planning agent prompt check
    if "Generate a step-by-step implementation plan" in text_content:
        plan_data = {
            "title": "Fix divide function bug in calculator.py",
            "description": "Handle zero divisor input safely and raise ValueError as expected.",
            "steps": [
                {"step": 1, "description": "Inspect calculator.py and update divide function", "status": "pending"},
                {"step": 2, "description": "Execute validation test suite test_calculator.py", "status": "pending"}
            ]
        }
        return MockResponse({
            "candidates": [{"content": {"parts": [{"text": json.dumps(plan_data)}]}}]
        })

    # 2. Coding agent prompt check (first attempt)
    elif "You are an expert AI software engineer" in text_content:
        # Return incorrect fix that returns 0 instead of raising ValueError (fails test)
        coding_data = {
            "explanation": "Modified divide function to return 0 when divisor b is 0.",
            "changes": [
                {
                    "filepath": "calculator.py",
                    "content": "def divide(a, b):\n    if b == 0:\n        return 0\n    return a / b\n"
                }
            ]
        }
        return MockResponse({
            "candidates": [{"content": {"parts": [{"text": json.dumps(coding_data)}]}}]
        })

    # 3. Self-healing loop prompt check (second attempt)
    elif "The tests failed with the following traceback" in text_content:
        # Return correct fix that raises ValueError
        repaired_data = {
            "explanation": "Self-healing repair: Caught ZeroDivisionError and raised ValueError.",
            "changes": [
                {
                    "filepath": "calculator.py",
                    "content": "def divide(a, b):\n    if b == 0:\n        raise ValueError('Cannot divide by zero')\n    return a / b\n"
                }
            ]
        }
        return MockResponse({
            "candidates": [{"content": {"parts": [{"text": json.dumps(repaired_data)}]}}]
        })

    # 4. Review agent prompt check
    elif "You are a Staff Code Reviewer" in text_content:
        review_data = {
            "report": "### Code Review Feedback\n1. Security Profile: Clean. No vulnerabilities.\n2. Style compliance: Perfect.\n3. Performance profile: Efficient.",
            "score": 95,
            "security_score": 95,
            "performance_score": 95,
            "style_score": 95
        }
        return MockResponse({
            "candidates": [{"content": {"parts": [{"text": json.dumps(review_data)}]}}]
        })

    # Default fallback
    return MockResponse({"message": "default fallback response"})

@patch("httpx.post", side_effect=mock_httpx_post)
def run_demonstration(mock_post):
    print("\n" + "="*80)
    print("                  STARTING SANDBOX WORKFLOW DEMONSTRATION")
    print("="*80 + "\n")

    setup_sandbox_repo()
    run_id, repo_id = setup_database_entries()
    
    # Configure dummy API key to bypass parameter checks, HTTP post will be intercepted
    settings.GEMINI_API_KEY = "dummy-gemini-key"

    # Pre-index AST codebase symbols for the sandbox repo
    from app.services.intelligence import scan_and_index_repository
    print("Indexing repository intelligence layer (AST Scanner)...")
    scan_and_index_repository(repo_id, SANDBOX_DIR)

    # Initialize orchestrator
    orchestrator = MultiAgentOrchestrator()
    db = SessionLocal()

    try:
        # Run first stages of workflow (Issue -> Assignment -> Planning)
        print("\n--- PHASE 1: Running Issue classification, Assignment verification, and Planning ---")
        orchestrator.execute_workflow(run_id, start_node="issue_agent")

        # Verify plan was generated and workflow is paused awaiting approval
        run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
        plan = db.query(AgentPlan).filter(AgentPlan.run_id == run_id).first()
        print(f"\nPLANNING AGENT GENERATED PLAN (ID: {plan.id if plan else 'None'}):")
        print(f"Title: {plan.title if plan else 'N/A'}")
        print(f"Description: {plan.description if plan else 'N/A'}")
        print(f"Steps: {plan.steps if plan else 'N/A'}")
        print(f"Workflow State Status: {run.status}")

        if run.status == "awaiting_plan_approval":
            print("\n--- PHASE 2: Approving Plan and resuming coding workflow ---")
            plan.status = "approved"
            run.status = "running"
            db.commit()

            # Resume orchestrator from context_agent
            orchestrator.execute_workflow(run_id, start_node="context_agent")

        # Load final results from database
        run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
        pr = db.query(PullRequest).filter(PullRequest.agent_run_id == run_id).first()
        attempts = db.query(RepairAttempt).filter(RepairAttempt.run_id == run_id).all()
        iterations = db.query(ImplementationIteration).filter(ImplementationIteration.run_id == run_id).all()
        metrics = db.query(QualityMetric).filter(QualityMetric.run_id == run_id).first()

        print("\n" + "="*80)
        print("                         DEMONSTRATION RUN OUTCOMES")
        print("="*80 + "\n")
        print(f"Agent Run ID: {run_id}")
        print(f"Execution Final Status: {run.status}")
        print(f"Total Self-Healing Attempts Logged: {len(attempts)}")
        if len(attempts) > 0:
            for att in attempts:
                print(f"  - Attempt #{att.attempt_number}: Status: {att.status}")
                print(f"    Planned Fix: {att.planned_fix}")
                print(f"    Error Log:\n{att.error_message}")
        
        print(f"\nCode Iterations Logged: {len(iterations)}")
        for idx, iter in enumerate(iterations):
            print(f"  - Iteration #{iter.iteration_number} Diff:\n{iter.code_diff}")

        print(f"\nReview Score Metrics:")
        if metrics:
            print(f"  - Overall Score: {metrics.overall_score}/100")
            print(f"  - Security Score: {metrics.security_score}/100")
            print(f"  - Performance Score: {metrics.performance_score}/100")
            print(f"  - Style Score: {metrics.style_score}/100")

        print(f"\nGenerated PR Draft:")
        if pr:
            print(f"  - PR ID: {pr.id}")
            title_safe = pr.title.encode('ascii', errors='ignore').decode('ascii')
            print(f"  - Title: {title_safe}")
            desc_safe = pr.description.encode('ascii', errors='ignore').decode('ascii')
            print(f"  - Description:\n{desc_safe}")
            print(f"  - Files changed: {pr.files_changed}")
            print(f"  - Submission Status: {pr.approval_status}")
        else:
            print("  - PR not generated.")

    finally:
        db.close()

if __name__ == "__main__":
    # Force loggers to output to console
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_demonstration()
