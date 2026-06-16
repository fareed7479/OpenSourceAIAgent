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

# Test database setup (isolated test database)
TEST_DATABASE_URL = "sqlite:///./test_agent_platform_temp.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override the get_db dependency in the application
app.dependency_overrides[get_db] = override_get_db

class TestPhase1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create tables
        Base.metadata.create_all(bind=test_engine)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        # Drop tables and remove file
        Base.metadata.drop_all(bind=test_engine)
        if os.path.exists("./test_agent_platform_temp.db"):
            try:
                os.remove("./test_agent_platform_temp.db")
            except Exception:
                pass

    def test_oauth_login_redirect(self):
        # Trigger developer mock login bypass redirect
        response = self.client.get("/api/v1/auth/login?developer_mode=true", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        redirect_url = response.headers.get("location")
        self.assertIn("auth/callback", redirect_url)
        self.assertIn("mock=true", redirect_url)

    def test_mock_callback_and_auth_flow(self):
        # 1. Trigger callback token exchange
        response = self.client.get("/api/v1/auth/callback?mock_username=test-suite-user")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertEqual(data["user"]["username"], "test-suite-user")
        
        token = data["access_token"]
        
        # 2. Test fetching auth profile (/me) using token
        headers = {"Authorization": f"Bearer {token}"}
        me_response = self.client.get("/api/v1/auth/me", headers=headers)
        self.assertEqual(me_response.status_code, 200)
        me_data = me_response.json()
        self.assertEqual(me_data["username"], "test-suite-user")

    def test_repository_registration_flow(self):
        # Log in mock user
        response = self.client.get("/api/v1/auth/callback?mock_username=test-suite-user")
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 1. Verify list initially empty
        list_response = self.client.get("/api/v1/repositories", headers=headers)
        self.assertEqual(list_response.status_code, 200)
        initial_count = len(list_response.json())
        
        # 2. Register a new repository
        # Using mock mode register bypass
        register_payload = {
            "url": "https://github.com/test-owner/test-repo.git"
        }
        reg_response = self.client.post("/api/v1/repositories/register", json=register_payload, headers=headers)
        self.assertEqual(reg_response.status_code, 201)
        repo_data = reg_response.json()
        self.assertEqual(repo_data["name"], "test-repo.git")
        repo_id = repo_data["id"]
        
        # 3. Verify repository shows in list
        list_response = self.client.get("/api/v1/repositories", headers=headers)
        self.assertEqual(len(list_response.json()), initial_count + 1)
        
        # 4. Remove repository
        del_response = self.client.delete(f"/api/v1/repositories/{repo_id}", headers=headers)
        self.assertEqual(del_response.status_code, 204)
        
        # 5. Verify repository is removed
        list_response = self.client.get("/api/v1/repositories", headers=headers)
        self.assertEqual(len(list_response.json()), initial_count)

if __name__ == "__main__":
    unittest.main()
