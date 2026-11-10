import os
import sys
import socket
from pathlib import Path
from dotenv import load_dotenv
from unittest.mock import patch, MagicMock

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
from main import (
    app,
    create_access_token,
    GOOGLE_API_SOCKET_TIMEOUT,
    get_calendar_service,
    TimeoutGoogleAuthRequest,
    create_google_calendar_event,
    update_google_calendar_event,
    delete_google_calendar_event,
)
from database import SessionLocal
import models
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

client = TestClient(app)
db = SessionLocal()

created_session_ids = []

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
    print("STARTING TEST SUITE: PHASE 5 - STEP 5B.1")
    print("Google Calendar API Hardening (Timeouts & Classification)")
    print("==================================================")

    dummy_creds = Credentials(token="test_token_hardening")

    # -------------------------------------------------------------
    # TEST 1: Explicit 5-second timeout configuration
    # -------------------------------------------------------------
    service = get_calendar_service(dummy_creds)
    # Check underlying http transport timeout
    http_transport = getattr(service._http, 'http', None) or getattr(service, '_http', None)
    timeout_configured = (
        GOOGLE_API_SOCKET_TIMEOUT == 5.0 and
        http_transport is not None and
        getattr(http_transport, 'timeout', None) == 5.0
    )
    auth_req = TimeoutGoogleAuthRequest(timeout=5.0)
    test1_pass = timeout_configured and (auth_req.timeout == 5.0)
    record_result(
        "1. Explicit 5-second socket timeout configuration",
        test1_pass,
        f"Transport timeout={getattr(http_transport, 'timeout', None)}s, AuthRequest timeout={auth_req.timeout}s"
    )

    # -------------------------------------------------------------
    # TEST 2: HTTP 429 and 503 error classification
    # -------------------------------------------------------------
    resp_429 = MagicMock(status=429, reason="Too Many Requests")
    err_429 = HttpError(resp=resp_429, content=b'{"error": "rate_limit_exceeded"}')

    resp_503 = MagicMock(status=503, reason="Service Unavailable")
    err_503 = HttpError(resp=resp_503, content=b'{"error": "backend_error"}')

    now = datetime.now(timezone.utc)
    with patch("main.get_calendar_service") as mock_srv_builder:
        mock_srv = MagicMock()
        mock_srv.events().insert().execute.side_effect = err_429
        mock_srv_builder.return_value = mock_srv

        # 429 on create
        res_create_429 = create_google_calendar_event(dummy_creds, "Test", None, now, now + timedelta(hours=1))

        # 503 on create
        mock_srv.events().insert().execute.side_effect = err_503
        res_create_503 = create_google_calendar_event(dummy_creds, "Test", None, now, now + timedelta(hours=1))

    test2_pass = (res_create_429 is None and res_create_503 is None)
    record_result(
        "2. HTTP 429 and 503 error classification",
        test2_pass,
        "429 rate limit and 503 server errors classified and caught gracefully"
    )

    # -------------------------------------------------------------
    # TEST 3: HTTP 401 and 403 handling
    # -------------------------------------------------------------
    resp_401 = MagicMock(status=401, reason="Unauthorized")
    err_401 = HttpError(resp=resp_401, content=b'{"error": "invalid_credentials"}')

    resp_403 = MagicMock(status=403, reason="Forbidden")
    err_403 = HttpError(resp=resp_403, content=b'{"error": "insufficient_permissions"}')

    with patch("main.get_calendar_service") as mock_srv_builder:
        mock_srv = MagicMock()
        mock_srv_builder.return_value = mock_srv

        mock_srv.events().update().execute.side_effect = err_401
        res_up_401 = update_google_calendar_event(dummy_creds, "evt1", "Test", None, now, now + timedelta(hours=1))

        mock_srv.events().delete().execute.side_effect = err_403
        res_del_403 = delete_google_calendar_event(dummy_creds, "evt1")

    test3_pass = (res_up_401 is False and res_del_403 is False)
    record_result(
        "3. HTTP 401 and 403 handling",
        test3_pass,
        "Auth (401) and permission (403) errors caught cleanly without crash"
    )

    # -------------------------------------------------------------
    # TEST 4: Network timeout handling (TimeoutError & socket.timeout)
    # -------------------------------------------------------------
    with patch("main.get_calendar_service") as mock_srv_builder:
        mock_srv = MagicMock()
        mock_srv_builder.return_value = mock_srv

        mock_srv.events().insert().execute.side_effect = TimeoutError("Connection timed out after 5.0 seconds")
        res_to_create = create_google_calendar_event(dummy_creds, "Test", None, now, now + timedelta(hours=1))

        mock_srv.events().update().execute.side_effect = socket.timeout("Socket timed out after 5.0 seconds")
        res_to_update = update_google_calendar_event(dummy_creds, "evt1", "Test", None, now, now + timedelta(hours=1))

        mock_srv.events().delete().execute.side_effect = TimeoutError("Delete timed out")
        res_to_delete = delete_google_calendar_event(dummy_creds, "evt1")

    test4_pass = (res_to_create is None and res_to_update is False and res_to_delete is False)
    record_result(
        "4. Network socket timeout handling",
        test4_pass,
        "5-second socket timeouts in create, update, delete caught safely"
    )

    # -------------------------------------------------------------
    # TEST 5: No automatic retry of event creation (Prevent duplicates)
    # -------------------------------------------------------------
    with patch("main.get_calendar_service") as mock_srv_builder:
        mock_srv = MagicMock()
        mock_srv_builder.return_value = mock_srv
        mock_srv.events().insert().execute.return_value = {"id": "google_evt_unique_1"}

        create_google_calendar_event(dummy_creds, "Unique Test", None, now, now + timedelta(hours=1))
        # Verify execute was called with num_retries=0
        insert_execute_args = mock_srv.events().insert().execute.call_args
        num_retries_arg = insert_execute_args.kwargs.get("num_retries") if insert_execute_args else None

    test5_pass = (num_retries_arg == 0)
    record_result(
        "5. No automatic retry of event creation",
        test5_pass,
        f"events.insert execute called with num_retries={num_retries_arg} to prevent duplicates"
    )

    # -------------------------------------------------------------
    # TEST 6: Safe retry behavior for eligible update/delete operations
    # -------------------------------------------------------------
    with patch("main.get_calendar_service") as mock_srv_builder:
        mock_srv = MagicMock()
        mock_srv_builder.return_value = mock_srv
        mock_srv.events().update().execute.return_value = {"id": "google_evt_unique_1"}
        mock_srv.events().delete().execute.return_value = {}

        update_google_calendar_event(dummy_creds, "evt1", "Test", None, now, now + timedelta(hours=1))
        up_kwargs = mock_srv.events().update().execute.call_args.kwargs if mock_srv.events().update().execute.call_args else {}

        delete_google_calendar_event(dummy_creds, "evt1")
        del_kwargs = mock_srv.events().delete().execute.call_args.kwargs if mock_srv.events().delete().execute.call_args else {}

        # Also test HTTP 404 on delete returns True immediately (preserves existing 404/410 handling)
        resp_404 = MagicMock(status=404, reason="Not Found")
        mock_srv.events().delete().execute.side_effect = HttpError(resp=resp_404, content=b'{"error": "not_found"}')
        del_404_res = delete_google_calendar_event(dummy_creds, "evt_already_gone")

    test6_pass = (
        up_kwargs.get("num_retries") == 1 and
        del_kwargs.get("num_retries") == 1 and
        del_404_res is True
    )
    record_result(
        "6. Safe retry behavior for update/delete operations",
        test6_pass,
        f"update num_retries={up_kwargs.get('num_retries')}, delete num_retries={del_kwargs.get('num_retries')}, 404 delete returns True"
    )

    # -------------------------------------------------------------
    # TEST 7: Database persistence when Google synchronization fails
    # -------------------------------------------------------------
    user = db.query(models.User).filter(models.User.id == 3).first() or db.query(models.User).first()
    membership = db.query(models.GroupMember).filter(models.GroupMember.user_id == user.id).first()
    group = db.query(models.Group).filter(models.Group.id == membership.group_id).first()
    token = create_access_token(user.id)
    auth_headers = {"Authorization": f"Bearer {token}"}

    session_payload = {
        "title": "Persistent Session Despite Google 503",
        "description": "DB row must be safely committed even when Google API fails",
        "start_time": (now + timedelta(days=2)).isoformat(),
        "end_time": (now + timedelta(days=2, hours=1)).isoformat()
    }

    with patch("main.get_valid_google_credentials") as mock_get_creds, \
         patch("main.create_google_calendar_event") as mock_create_evt:
        mock_get_creds.return_value = dummy_creds
        # Simulate Google 503 Service Unavailable / Timeout
        mock_create_evt.return_value = None

        res7 = client.post(f"/api/groups/{group.id}/sessions", headers=auth_headers, json=session_payload)

    if res7.status_code == 200:
        data7 = res7.json()
        s_obj = data7.get("session", {})
        session_id_7 = s_obj.get("id")
        created_session_ids.append(session_id_7)

        # Verify DB row exists in PostgreSQL
        db_session = db.query(models.StudySession).filter(models.StudySession.id == session_id_7).first()
        test7_pass = (
            db_session is not None and
            db_session.title == "Persistent Session Despite Google 503" and
            db_session.google_event_id is None
        )
        record_result(
            "7. Database persistence when Google synchronization fails",
            test7_pass,
            f"Session {session_id_7} safely created in PostgreSQL without Google event ID"
        )
    else:
        record_result("7. Database persistence when Google synchronization fails", False, f"HTTP {res7.status_code}: {res7.text}")

    # -------------------------------------------------------------
    # TEST 8: Frontend double-click submission guard verification
    # -------------------------------------------------------------
    js_path = PROJECT_ROOT / "frontend" / "script.js"
    with open(js_path, "r", encoding="utf-8") as f:
        js_code = f.read()

    test8_pass = (
        "isSubmittingScheduleSession" in js_code and
        "if (isSubmittingScheduleSession) return;" in js_code and
        "isSubmittingEditSession" in js_code and
        "if (isSubmittingEditSession) return;" in js_code
    )
    record_result(
        "8. Double-click submission guard in frontend",
        test8_pass,
        "isSubmittingScheduleSession & isSubmittingEditSession guards present in script.js"
    )

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
    db.close()
    print("Cleanup complete. Zero test residues.")

print("==================================================")
print(f"RESULTS SUMMARY: {len(test_results['passed'])} PASSED, {len(test_results['failed'])} FAILED")
print("==================================================")

if test_results["failed"]:
    sys.exit(1)
else:
    sys.exit(0)

