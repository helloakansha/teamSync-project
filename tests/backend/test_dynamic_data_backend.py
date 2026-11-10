"""
TeamSync - Platform Stats Backend Automated Test Suite
Verifies:
1. GET /api/platform/stats returns HTTP 200 and success: True.
2. Accurate counts matching PostgreSQL database records for users, groups, and sessions.
3. No leakage of user emails, passwords, tokens, or names.
4. Correct response data structure and types.
"""

# -------------------------------------------------------------
# Consistent Project Root & Backend Environment Setup
# -------------------------------------------------------------
from pathlib import Path
import sys
import os
from dotenv import load_dotenv

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = None
for candidate in [CURRENT_DIR.parent.parent, CURRENT_DIR.parent, CURRENT_DIR]:
    if (candidate / "backend").is_dir() and (candidate / "frontend").is_dir():
        PROJECT_ROOT = candidate
        break
if not PROJECT_ROOT:
    PROJECT_ROOT = CURRENT_DIR.parent.parent

BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(1, str(PROJECT_ROOT))

# Load environment variables from backend/.env or project root .env
if (BACKEND_DIR / ".env").is_file():
    load_dotenv(dotenv_path=BACKEND_DIR / ".env")
elif (PROJECT_ROOT / ".env").is_file():
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from main import app, get_db
import models
from sqlalchemy.orm import Session

def run_tests():
    print("=" * 70)
    print("TEAMSYNC - BACKEND PLATFORM STATS ENDPOINT VERIFICATION")
    print("=" * 70)

    client = TestClient(app)
    db: Session = next(get_db())

    try:
        # 1. Direct DB count queries
        db_user_count = db.query(models.User).count()
        db_group_count = db.query(models.Group).count()
        db_session_count = db.query(models.StudySession).count()

        print(f"[DB COUNTS] Users: {db_user_count}, Groups: {db_group_count}, Sessions: {db_session_count}")

        # 2. Call endpoint
        response = client.get("/api/platform/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        print(f"[API RESPONSE] {data}")

        # 3. Verify success flag
        assert data.get("success") is True, "Expected success: True"
        print("✓ Test 1 Passed: Endpoint returned HTTP 200 with success: True")

        # 4. Verify accuracy
        assert data.get("students_count") == db_user_count, f"Expected {db_user_count}, got {data.get('students_count')}"
        assert data.get("groups_count") == db_group_count, f"Expected {db_group_count}, got {data.get('groups_count')}"
        assert data.get("sessions_count") == db_session_count, f"Expected {db_session_count}, got {data.get('sessions_count')}"
        print("✓ Test 2 Passed: Endpoint counts match live PostgreSQL database counts exactly")

        # 5. Verify security / privacy (no sensitive keys)
        allowed_keys = {"success", "students_count", "groups_count", "sessions_count"}
        assert set(data.keys()) == allowed_keys, f"Unexpected keys in response: {set(data.keys()) - allowed_keys}"
        for sensitive in ["password", "hashed_password", "email", "token", "users", "groups", "sessions"]:
            assert sensitive not in data, f"Found sensitive key: {sensitive}"
        print("✓ Test 3 Passed: Endpoint does not leak sensitive user or group details")

        # 6. Verify types
        assert isinstance(data["students_count"], int), "students_count must be int"
        assert isinstance(data["groups_count"], int), "groups_count must be int"
        assert isinstance(data["sessions_count"], int), "sessions_count must be int"
        print("✓ Test 4 Passed: All returned count values are integer types")

        print("=" * 70)
        print("ALL BACKEND PLATFORM STATS TESTS PASSED!")
        print("=" * 70)

    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
