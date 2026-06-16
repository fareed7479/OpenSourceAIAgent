import os
import sys
import unittest
from datetime import datetime, timezone
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
from app.models.assignment import Assignment
from app.models.user import User
from app.models.settings import Setting
from app.services.assignment import request_issue_assignment, monitor_assignments_task
from app.db.init_db import run_migrations
from app.core.encryption import encrypt_token

# Test database setup (isolated test database)
TEST_DATABASE_URL = "sqlite:///./test_agent_platform_temp_p4.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestPhase4(unittest.TestCase):
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
        if os.path.exists("./test_agent_platform_temp_p4.db"):
            try:
                os.remove("./test_agent_platform_temp_p4.db")
            except Exception:
                pass

    def test_database_migration_columns(self):
        inspector = inspect(test_engine)
        
        # Verify columns exist in issues table
        issue_cols = [col["name"] for col in inspector.get_columns("issues")]
        self.assertIn("source_owner", issue_cols)
        self.assertIn("source_repo", issue_cols)
        
        # Verify columns exist in assignments table
        assign_cols = [col["name"] for col in inspector.get_columns("assignments")]
        self.assertIn("comment_url", assign_cols)
        self.assertIn("issue_url", assign_cols)
        self.assertIn("repository_url", assign_cols)

    @patch("httpx.post")
    def test_assignment_commenting_redirection_and_template(self, mock_post):
        # 1. Login user
        login_res = self.client.get("/api/v1/auth/callback?mock_username=test_p4_user")
        self.assertEqual(login_res.status_code, 200)
        user_id = login_res.json()["user"]["id"]
        
        db = TestingSessionLocal()
        
        # Change user github_id so it doesn't start with "mock-" to execute the real HTTP path
        user_rec = db.query(User).filter(User.id == user_id).first()
        user_rec.github_id = "real-github-id-123"
        user_rec.access_token = encrypt_token("real-github-access-token-stub")
        db.commit()
        
        # Create a fork repository
        repo = Repository(
            user_id=user_id,
            owner="test_p4_user",
            name="ForkedRepo",
            url="https://github.com/test_p4_user/ForkedRepo",
            language="python"
        )
        db.add(repo)
        db.commit()
        
        # Create an issue representing an upstream issue
        issue = Issue(
            repository_id=repo.id,
            github_issue_id=777801,
            number=42,
            title="Upstream bug description",
            description="Fix upstream bug.",
            url="https://github.com/UpstreamOwner/UpstreamRepo/issues/42",
            labels=["bug"],
            difficulty="easy",
            score=85,
            status="open",
            assignment_status="unassigned",
            source_owner="UpstreamOwner",
            source_repo="UpstreamRepo"
        )
        db.add(issue)
        db.commit()
        
        # Setup custom comment template in Settings
        custom_template = "Requesting assignment on issue #{number} for user {username}"
        setting = Setting(
            user_id=user_id,
            key="assignment_comment_template",
            value=custom_template
        )
        db.add(setting)
        db.commit()
        
        # Mock GitHub comment post response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": 999222,
            "html_url": "https://github.com/UpstreamOwner/UpstreamRepo/issues/42#issuecomment-999222"
        }
        mock_post.return_value = mock_response

        # Execute assignment request
        with patch("app.services.assignment.SessionLocal", return_value=db):
            assignment = request_issue_assignment(issue_id=issue.id, user_id=user_id, db=db)

        # Verify correct upstream repository was targeted instead of ForkedRepo
        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        self.assertEqual(called_url, "https://api.github.com/repos/UpstreamOwner/UpstreamRepo/issues/42/comments")

        # Verify comment body matches the template formatting
        called_payload = mock_post.call_args[1]["json"]
        self.assertEqual(called_payload["body"], "Requesting assignment on issue #42 for user test_p4_user")

        # Verify database fields are populated correctly
        self.assertEqual(assignment.status, "comment_posted")
        self.assertEqual(assignment.request_comment_id, 999222)
        self.assertEqual(assignment.comment_url, "https://github.com/UpstreamOwner/UpstreamRepo/issues/42#issuecomment-999222")
        self.assertEqual(assignment.issue_url, issue.url)
        self.assertEqual(assignment.repository_url, "https://github.com/UpstreamOwner/UpstreamRepo")

        db.close()

    @patch("httpx.get")
    def test_assignment_polling_state_machine(self, mock_get):
        # Setup database
        db = TestingSessionLocal()
        
        # Create user & repo
        user = User(
            username="test_poll_user",
            github_id="poll-user-github-id",
            email="poll@example.com",
            access_token=encrypt_token("real-oauth-token-stub")
        )
        db.add(user)
        db.commit()
        
        repo = Repository(
            user_id=user.id,
            owner="UpstreamOwner",
            name="UpstreamRepo",
            url="https://github.com/UpstreamOwner/UpstreamRepo"
        )
        db.add(repo)
        db.commit()
        
        issue = Issue(
            repository_id=repo.id,
            github_issue_id=777805,
            number=99,
            title="Poll test issue",
            description="Testing states.",
            url="https://github.com/UpstreamOwner/UpstreamRepo/issues/99",
            status="open",
            assignment_status="comment_posted",
            source_owner="UpstreamOwner",
            source_repo="UpstreamRepo"
        )
        db.add(issue)
        db.commit()
        
        assignment = Assignment(
            user_id=user.id,
            issue_id=issue.id,
            status="comment_posted",
            request_comment_id=999333,
            comment_url="https://github.com/UpstreamOwner/UpstreamRepo/issues/99#issuecomment-999333"
        )
        db.add(assignment)
        db.commit()
        
        assignment_id = assignment.id
        issue_id = issue.id

        # Mock GitHub API returning assigned state (assigned to test_poll_user)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "state": "open",
            "assignee": {"login": "test_poll_user"}
        }
        mock_get.return_value = mock_response

        # Execute polling monitor task
        with patch("app.services.assignment.SessionLocal", return_value=db), \
             patch("app.services.assignment._trigger_agent_run") as mock_trigger:
            monitor_assignments_task()
            
            # Verify status transitions to "assigned"
            db2 = TestingSessionLocal()
            assignment_check = db2.query(Assignment).filter(Assignment.id == assignment_id).first()
            issue_check = db2.query(Issue).filter(Issue.id == issue_id).first()
            
            self.assertEqual(assignment_check.status, "assigned")
            self.assertEqual(issue_check.assignment_status, "assigned")
            mock_trigger.assert_called_once()
            db2.close()

        db.close()

if __name__ == "__main__":
    unittest.main()
