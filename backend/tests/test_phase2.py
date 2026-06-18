import os
import sys
import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.database import Base, get_db
from app.models.repository import Repository
from app.models.user import User

# Test database setup (isolated test database)
TEST_DATABASE_URL = "sqlite:///./test_agent_platform_temp_p2.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override the get_db dependency inside setUpClass

class TestPhase2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib
        importlib.import_module("app.models")
        Base.metadata.create_all(bind=test_engine)
        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if get_db in app.dependency_overrides:
            del app.dependency_overrides[get_db]
        Base.metadata.drop_all(bind=test_engine)
        if os.path.exists("./test_agent_platform_temp_p2.db"):
            try:
                os.remove("./test_agent_platform_temp_p2.db")
            except Exception:
                pass

    def test_url_cleaning_in_schema(self):
        # Test schema validation removes .git and trailing slashes
        from app.schemas.repository import RepositoryCreate
        
        c1 = RepositoryCreate(url="https://github.com/owner/repo.git")
        self.assertEqual(c1.url, "https://github.com/owner/repo")
        
        c2 = RepositoryCreate(url="https://github.com/owner/repo/")
        self.assertEqual(c2.url, "https://github.com/owner/repo")
        
        c3 = RepositoryCreate(url="https://github.com/owner/repo.git/")
        self.assertEqual(c3.url, "https://github.com/owner/repo")

    def test_github_discovery_and_registration(self):
        # 1. Login mock user
        response = self.client.get("/api/v1/auth/callback?mock_username=phase2-test-user")
        self.assertEqual(response.status_code, 200)
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get GitHub Repositories List (Discovery)
        discovery_response = self.client.get("/api/v1/repositories/github", headers=headers)
        self.assertEqual(discovery_response.status_code, 200)
        repos = discovery_response.json()
        self.assertEqual(len(repos), 2)
        self.assertEqual(repos[0]["name"], "College_Companion")
        self.assertTrue(repos[0]["fork"])
        self.assertEqual(repos[1]["name"], "Backend")
        self.assertFalse(repos[1]["fork"])

        # 3. Register a repository with .git extension
        register_payload = {
            "url": "https://github.com/phase2-test-user/College_Companion.git"
        }
        reg_response = self.client.post("/api/v1/repositories/register", json=register_payload, headers=headers)
        self.assertEqual(reg_response.status_code, 201)
        repo_data = reg_response.json()
        
        # Verify URL is clean and metadata is populated
        self.assertEqual(repo_data["name"], "College_Companion")
        self.assertEqual(repo_data["url"], "https://github.com/phase2-test-user/College_Companion")
        self.assertIsNotNone(repo_data["meta_info"])
        self.assertIn("github_metadata", repo_data["meta_info"])
        self.assertTrue(repo_data["meta_info"]["github_metadata"]["fork"])
        self.assertEqual(repo_data["meta_info"]["github_metadata"]["stargazers_count"], 42)
        
        repo_id = repo_data["id"]

        # 4. Test Sync Repository
        sync_response = self.client.post(f"/api/v1/repositories/{repo_id}/sync", headers=headers)
        self.assertEqual(sync_response.status_code, 200)
        sync_data = sync_response.json()
        self.assertEqual(sync_data["meta_info"]["github_metadata"]["stargazers_count"], 100) # mock sync value

        # Clean up
        self.client.delete(f"/api/v1/repositories/{repo_id}", headers=headers)

if __name__ == "__main__":
    unittest.main()
