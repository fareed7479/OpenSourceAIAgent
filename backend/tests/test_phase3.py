import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import Base, get_db
from app.models.repository import Repository
from app.models.issue import Issue
from app.models.user import User
from app.services.ranking import evaluate_issue_difficulty_and_score
from app.services.discovery import discover_repository_issues_task
from app.db.init_db import run_migrations

# Test database setup (isolated test database)
TEST_DATABASE_URL = "sqlite:///./test_agent_platform_temp_p3.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestPhase3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 1. Create table structure
        Base.metadata.create_all(bind=test_engine)
        
        # 2. Run migrations check
        with patch('app.db.init_db.engine', test_engine):
            run_migrations()
            
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=test_engine)
        if os.path.exists("./test_agent_platform_temp_p3.db"):
            try:
                os.remove("./test_agent_platform_temp_p3.db")
            except Exception:
                pass

    def test_database_migration_columns(self):
        # Verify columns exist in SQLite database table
        inspector = inspect(test_engine)
        columns = [col["name"] for col in inspector.get_columns("issues")]
        self.assertIn("author_username", columns)
        self.assertIn("github_created_at", columns)
        self.assertIn("github_updated_at", columns)
        self.assertIn("comments_count", columns)
        self.assertIn("meta_info", columns)

    def test_ranking_engine_signals(self):
        # 1. ELUSOC + Freshness + Bug + Tech Stack Match
        res = evaluate_issue_difficulty_and_score(
            title="Fix ELUSOC auth issue",
            body="This is a bug that needs to be fixed. It has a reproduce code block like: ```python\nprint('bug')\n```",
            labels=["bug", "elusoc"],
            repo_language="python",
            user_preferred_languages=["python"],
            comments_count=5,
            github_created_at=datetime.now(timezone.utc) - timedelta(days=5),
            assignment_status="unassigned"
        )
        self.assertEqual(res["difficulty"], "easy")
        self.assertEqual(res["score"], 100)
        self.assertIn("ELUSOC bounty target boost", res["ranking_reason"])

        # 2. Assigned / already taken issue penalty
        res_assigned = evaluate_issue_difficulty_and_score(
            title="Refactor database interface",
            body="We need a rewrite or refactor of all the database interfaces because the performance is poor and lacks security.",
            labels=["refactor", "performance"],
            repo_language="go",
            user_preferred_languages=["python"],
            comments_count=25,
            github_created_at=datetime.now(timezone.utc) - timedelta(days=200),
            assignment_status="assigned_to_other"
        )
        self.assertEqual(res_assigned["difficulty"], "hard")
        self.assertEqual(res_assigned["score"], 0)
        self.assertIn("already in progress/assigned", res_assigned["ranking_reason"])

    @patch("httpx.get")
    def test_fork_redirection_and_sync(self, mock_get):
        # 1. Use login callback API to create the user safely
        login_res = self.client.get("/api/v1/auth/callback?mock_username=test_fork_user")
        self.assertEqual(login_res.status_code, 200)
        user_id = login_res.json()["user"]["id"]
        
        # Setup mock db session and add repo
        db = TestingSessionLocal()
        
        # Create repository with forked metadata and disabled issues
        repo_metadata = {
            "github_metadata": {
                "fork": True,
                "has_issues": False,
                "parent": {
                    "name": "UpstreamRepo",
                    "owner": {
                        "login": "UpstreamOwner"
                    }
                }
            }
        }
        repo = Repository(
            user_id=user_id,
            owner="test_fork_user",
            name="ForkedRepo",
            url="https://github.com/test_fork_user/ForkedRepo",
            meta_info=repo_metadata,
            language="python"
        )
        db.add(repo)
        db.commit()
        repo_id = repo.id
        
        # Setup mock GitHub response for UpstreamRepo issues
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": 888801,
                "number": 42,
                "title": "Bug in upstream",
                "body": "This issue is upstream but should show on our dashboard.",
                "html_url": "https://github.com/UpstreamOwner/UpstreamRepo/issues/42",
                "state": "open",
                "labels": [{"name": "bug"}],
                "user": {"login": "upstream-author"},
                "comments": 3,
                "created_at": "2026-06-10T12:00:00Z",
                "updated_at": "2026-06-11T12:00:00Z",
                "assignee": None,
                "assignees": []
            }
        ]
        mock_get.return_value = mock_response

        # Execute discovery task
        with patch("app.services.discovery.SessionLocal", return_value=db):
            discover_repository_issues_task(repo_id=repo_id, github_token="real-token-stub")

        # Verify it redirected upstream in the request call
        mock_get.assert_called_once()
        called_url = mock_get.call_args[0][0]
        self.assertEqual(called_url, "https://api.github.com/repos/UpstreamOwner/UpstreamRepo/issues")

        # Verify issue was saved in our DB with correct mappings
        db.expire_all()
        issue = db.query(Issue).filter(Issue.repository_id == repo_id).first()
        self.assertIsNotNone(issue)
        self.assertEqual(issue.number, 42)
        self.assertEqual(issue.title, "Bug in upstream")
        self.assertEqual(issue.author_username, "upstream-author")
        self.assertEqual(issue.comments_count, 3)
        self.assertEqual(issue.status, "open")
        self.assertEqual(issue.assignment_status, "unassigned")
        self.assertEqual(issue.github_created_at.replace(tzinfo=timezone.utc), datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc))

        db.close()

    def test_issues_api_filtering(self):
        # 1. Login mock user to get auth token
        response = self.client.get("/api/v1/auth/callback?mock_username=test_filter_user")
        self.assertEqual(response.status_code, 200)
        token = response.json()["access_token"]
        user_id = response.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup mock db and register a repository
        db = TestingSessionLocal()
        
        repo = Repository(
            user_id=user_id,
            owner="test_filter_user",
            name="FilterRepo",
            url="https://github.com/test_filter_user/FilterRepo",
            language="javascript"
        )
        db.add(repo)
        db.commit()
        repo_id = repo.id # Capture while session is active

        # Add issues with different states and labels
        issue1 = Issue(
            repository_id=repo_id,
            github_issue_id=12345,
            number=1,
            title="JavaScript bug in UI",
            description="The frontend crashes on loading.",
            url="https://github.com/test_filter_user/FilterRepo/issues/1",
            labels=["bug", "frontend"],
            difficulty="easy",
            score=80,
            status="open",
            assignment_status="unassigned"
        )
        issue2 = Issue(
            repository_id=repo_id,
            github_issue_id=12346,
            number=2,
            title="TypeScript documentation mismatch",
            description="Docs are outdated.",
            url="https://github.com/test_filter_user/FilterRepo/issues/2",
            labels=["docs", "good-first-issue"],
            difficulty="easy",
            score=70,
            status="closed",
            assignment_status="unassigned"
        )
        db.add(issue1)
        db.add(issue2)
        db.commit()
        db.close()

        # Test state filtering: 'open'
        res_open = self.client.get(f"/api/v1/issues?repository_id={repo_id}&state=open", headers=headers)
        self.assertEqual(res_open.status_code, 200)
        self.assertEqual(len(res_open.json()), 1)
        self.assertEqual(res_open.json()[0]["number"], 1)

        # Test state filtering: 'closed'
        res_closed = self.client.get(f"/api/v1/issues?repository_id={repo_id}&state=closed", headers=headers)
        self.assertEqual(res_closed.status_code, 200)
        self.assertEqual(len(res_closed.json()), 1)
        self.assertEqual(res_closed.json()[0]["number"], 2)

        # Test state filtering: 'all'
        res_all = self.client.get(f"/api/v1/issues?repository_id={repo_id}&state=all", headers=headers)
        self.assertEqual(res_all.status_code, 200)
        self.assertEqual(len(res_all.json()), 2)

        # Test label filtering
        res_label = self.client.get(f"/api/v1/issues?repository_id={repo_id}&label=docs&state=all", headers=headers)
        self.assertEqual(res_label.status_code, 200)
        self.assertEqual(len(res_label.json()), 1)
        self.assertEqual(res_label.json()[0]["number"], 2)

        # Test keyword search
        res_search = self.client.get(f"/api/v1/issues?repository_id={repo_id}&search=outdated&state=all", headers=headers)
        self.assertEqual(res_search.status_code, 200)
        self.assertEqual(len(res_search.json()), 1)
        self.assertEqual(res_search.json()[0]["number"], 2)

if __name__ == "__main__":
    unittest.main()
