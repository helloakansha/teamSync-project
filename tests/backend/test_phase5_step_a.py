import os
import sys
from pathlib import Path
from dotenv import load_dotenv

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
from main import app, create_access_token, encrypt_google_token
from database import SessionLocal
import models
from datetime import datetime, timezone, timedelta

client = TestClient(app)
db = SessionLocal()

created_session_ids = []
created_credential_user_ids = []

test_results = {
    "passed": [],
    "failed": []
}

def record_result(test_name, passed, message=""):
    if passed:
        test_results["passed"].append(test_name)
        print(f"[PASS] {test_name} - {message}")
    else:
        test_results["failed"].append((test_name, message))
        print(f"[FAIL] {test_name} - {message}")

try:
    print("==================================================")
    print("STARTING TEST SUITE: PHASE 5 - STEP 5A")
    print("Google Calendar Disconnect, Reconnect & Status")
    print("==================================================")

    # 1. Setup two test users (User A and User B)
    users = db.query(models.User).all()
    assert len(users) >= 2, "Need at least 2 users in DB to test isolation"
    user_a = users[0]
    user_b = users[1]

    token_a = create_access_token(user_a.id)
    token_b = create_access_token(user_b.id)
    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    print(f"User A: {user_a.name} (id={user_a.id}) | User B: {user_b.name} (id={user_b.id})")

    # -------------------------------------------------------------
    # TEST 1: Unauthenticated disconnect returns 401
    # -------------------------------------------------------------
    res1_no_token = client.post("/auth/google/disconnect")
    res1_bad_token = client.post("/auth/google/disconnect", headers={"Authorization": "Bearer invalidtoken123"})
    test1_pass = (res1_no_token.status_code == 401 and res1_bad_token.status_code == 401)
    record_result("1. Unauthenticated disconnect returns 401", test1_pass, "Missing & invalid tokens rejected with 401")

    # -------------------------------------------------------------
    # TEST 2: Disconnecting an already-disconnected account
    # -------------------------------------------------------------
    # Ensure user_a has no credentials initially
    existing_cred_a = db.query(models.GoogleCredential).filter(models.GoogleCredential.user_id == user_a.id).first()
    if existing_cred_a:
        db.delete(existing_cred_a)
        db.commit()

    res2 = client.post("/auth/google/disconnect", headers=auth_a)
    test2_pass = (
        res2.status_code == 200 and
        res2.json().get("success") is True and
        res2.json().get("connected") is False and
        "not connected" in res2.json().get("message", "").lower()
    )
    record_result("2. Disconnecting an already-disconnected account", test2_pass, f"Returned graceful 200: {res2.json().get('message')}")

    # -------------------------------------------------------------
    # TEST 3: Status endpoint for disconnected user
    # -------------------------------------------------------------
    res3 = client.get("/auth/google/status", headers=auth_a)
    data3 = res3.json()
    test3_pass = (
        res3.status_code == 200 and
        data3.get("connected") is False and
        data3.get("status") == "disconnected" and
        data3.get("requires_reconnect") is False
    )
    record_result("3. Status endpoint for disconnected user", test3_pass, f"status='{data3.get('status')}', connected={data3.get('connected')}")

    # -------------------------------------------------------------
    # TEST 4: Status endpoint distinguishes 'requires_reconnect'
    # -------------------------------------------------------------
    # Insert an expired credential with NO refresh token for user_a
    past_expiry = datetime.now(timezone.utc) - timedelta(days=2)
    cred_expired = models.GoogleCredential(
        user_id=user_a.id,
        access_token=encrypt_google_token("dummy_expired_token_abc"),
        refresh_token=None,
        token_expiry=past_expiry,
        scopes="https://www.googleapis.com/auth/calendar.events.owned"
    )
    db.add(cred_expired)
    db.commit()
    created_credential_user_ids.append(user_a.id)

    res4 = client.get("/auth/google/status", headers=auth_a)
    data4 = res4.json()
    test4_pass = (
        res4.status_code == 200 and
        data4.get("connected") is False and
        data4.get("status") == "requires_reconnect" and
        data4.get("requires_reconnect") is True and
        "reconnect" in data4.get("message", "").lower()
    )
    record_result("4. Status endpoint reports requires_reconnect when credentials invalid", test4_pass, f"status='{data4.get('status')}', requires_reconnect={data4.get('requires_reconnect')}")

    # -------------------------------------------------------------
    # TEST 5: Authenticated disconnect removes credentials
    # -------------------------------------------------------------
    res5 = client.post("/auth/google/disconnect", headers=auth_a)
    cred_in_db = db.query(models.GoogleCredential).filter(models.GoogleCredential.user_id == user_a.id).first()
    test5_pass = (
        res5.status_code == 200 and
        res5.json().get("success") is True and
        res5.json().get("connected") is False and
        cred_in_db is None
    )
    record_result("5. Authenticated disconnect removes user credentials", test5_pass, "PostgreSQL row deleted cleanly")

    # -------------------------------------------------------------
    # TEST 6: User isolation (User A cannot disconnect User B)
    # -------------------------------------------------------------
    # Set up credentials for User B
    existing_cred_b = db.query(models.GoogleCredential).filter(models.GoogleCredential.user_id == user_b.id).first()
    if not existing_cred_b:
        future_expiry = datetime.now(timezone.utc) + timedelta(days=5)
        existing_cred_b = models.GoogleCredential(
            user_id=user_b.id,
            access_token=encrypt_google_token("user_b_token_xyz"),
            refresh_token=encrypt_google_token("user_b_refresh_xyz"),
            token_expiry=future_expiry,
            scopes="https://www.googleapis.com/auth/calendar.events.owned"
        )
        db.add(existing_cred_b)
        db.commit()
        created_credential_user_ids.append(user_b.id)

    # User A calls disconnect
    res6 = client.post("/auth/google/disconnect", headers=auth_a)

    # Check that User B's credential is STILL intact
    b_cred_after = db.query(models.GoogleCredential).filter(models.GoogleCredential.user_id == user_b.id).first()
    test6_pass = (b_cred_after is not None and b_cred_after.user_id == user_b.id)
    record_result("6. User isolation enforced", test6_pass, f"User B credentials remained intact after User A disconnect")

    # -------------------------------------------------------------
    # TEST 7: Existing study sessions and event IDs remain intact
    # -------------------------------------------------------------
    # Find any group user_a belongs to
    membership = db.query(models.GroupMember).filter(models.GroupMember.user_id == user_a.id).first()
    if not membership:
        membership = db.query(models.GroupMember).first()
        user_a = db.query(models.User).filter(models.User.id == membership.user_id).first()
        token_a = create_access_token(user_a.id)
        auth_a = {"Authorization": f"Bearer {token_a}"}

    test_session = models.StudySession(
        group_id=membership.group_id,
        created_by=user_a.id,
        title="[TEST] Session Preserved After Disconnect",
        description="Verifying sessions are never deleted by disconnect",
        start_time=datetime.now(timezone.utc) + timedelta(days=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=1),
        google_event_id="preserved_google_event_id_777",
        calendar_id="primary"
    )
    db.add(test_session)
    db.commit()
    db.refresh(test_session)
    created_session_ids.append(test_session.id)

    # Disconnect user_a
    client.post("/auth/google/disconnect", headers=auth_a)

    # Verify session still exists with its google_event_id intact
    session_check = db.query(models.StudySession).filter(models.StudySession.id == test_session.id).first()
    test7_pass = (
        session_check is not None and
        session_check.title == "[TEST] Session Preserved After Disconnect" and
        session_check.google_event_id == "preserved_google_event_id_777"
    )
    record_result("7. Existing study sessions and Google event IDs remain intact", test7_pass, f"Session {test_session.id} untouched")

    # -------------------------------------------------------------
    # TEST 8: Reconnection capability after disconnect
    # -------------------------------------------------------------
    res8 = client.get("/auth/google/connect", headers=auth_a)
    test8_pass = (
        res8.status_code == 200 and
        "authorization_url" in res8.json() and
        "accounts.google.com" in res8.json()["authorization_url"]
    )
    record_result("8. Reconnection flow accessible after disconnect", test8_pass, "Fresh OAuth authorization_url generated successfully")

finally:
    # Cleanup test sessions
    print("\nCleaning up test artifacts...")
    for sid in created_session_ids:
        try:
            s = db.query(models.StudySession).filter(models.StudySession.id == sid).first()
            if s:
                db.delete(s)
                db.commit()
        except Exception:
            db.rollback()

    for uid in created_credential_user_ids:
        try:
            c = db.query(models.GoogleCredential).filter(models.GoogleCredential.user_id == uid).first()
            if c:
                db.delete(c)
                db.commit()
        except Exception:
            db.rollback()

    db.close()
    print("Cleanup complete. Zero test residues.")

print("==================================================")
print(f"RESULTS SUMMARY: {len(test_results['passed'])} PASSED, {len(test_results['failed'])} FAILED")
print("==================================================")

if test_results["failed"]:
    sys.exit(1)
else:
    sys.exit(0)

