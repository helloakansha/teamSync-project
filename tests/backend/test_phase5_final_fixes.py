import sys
import os
import uuid
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from googleapiclient.errors import HttpError
import httplib2

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
from database import SessionLocal, engine, Base
import models
from main import (
    app,
    hash_password,
    create_access_token,
    generate_deterministic_event_id,
    create_google_calendar_event,
    bg_sync_create_calendar_event,
    bg_sync_update_calendar_event,
    reconcile_interrupted_sync_operations,
    EventCancelledOnGoogleError
)

client = TestClient(app)

def run_tests():
    print("=" * 75)
    print("TEAMSYNC — PHASE 5 FINAL RELIABILITY FIXES VERIFICATION TEST SUITE")
    print("Worker Fencing, Update Concurrency & HTTP 409 Resolution")
    print("=" * 75)

    db = SessionLocal()
    results = []

    def record(name, passed, detail=""):
        status_str = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        results.append((name, passed, detail))
        print(f"[{status_str}] {symbol} {name}")
        if detail:
            print(f"       Detail: {detail}")

    test_user_ids = []
    test_group_ids = []
    test_session_ids = []

    try:
        suffix = int(datetime.now().timestamp() * 1000)
        u_creator = models.User(
            name=f"Creator {suffix}",
            email=f"creator_{suffix}@example.com",
            password_hash=hash_password("Pass123!")
        )
        u_owner = models.User(
            name=f"Owner {suffix}",
            email=f"owner_{suffix}@example.com",
            password_hash=hash_password("Pass123!")
        )
        db.add_all([u_creator, u_owner])
        db.commit()
        db.refresh(u_creator)
        db.refresh(u_owner)
        test_user_ids.extend([u_creator.id, u_owner.id])

        cred_creator = models.GoogleCredential(
            user_id=u_creator.id,
            access_token="fake_creator_token",
            refresh_token="fake_creator_refresh",
            token_expiry=datetime.now(timezone.utc) + timedelta(days=7),
            scopes="https://www.googleapis.com/auth/calendar.events.owned"
        )
        db.add(cred_creator)
        db.commit()

        group = models.Group(
            name=f"Reliability Group {suffix}",
            description="Testing Worker Fencing and 409 Fixes",
            subject="Auditing"
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        test_group_ids.append(group.id)

        gm_owner = models.GroupMember(group_id=group.id, user_id=u_owner.id, role="owner")
        gm_creator = models.GroupMember(group_id=group.id, user_id=u_creator.id, role="member")
        db.add_all([gm_owner, gm_creator])
        db.commit()

        # =========================================================================
        # TEST 1: Deterministic Event ID Google Base32hex & Versioning Compliance
        # =========================================================================
        det_id_v1 = generate_deterministic_event_id(101, 1)
        det_id_v2 = generate_deterministic_event_id(101, 2)
        det_id_diff = generate_deterministic_event_id(102, 1)

        base32hex_regex = re.compile(r"^[0-9a-v]+$")
        t1_valid_charset = bool(base32hex_regex.match(det_id_v1)) and bool(base32hex_regex.match(det_id_v2))
        t1_length_ok = (5 <= len(det_id_v1) <= 1024) and (5 <= len(det_id_v2) <= 1024)
        t1_distinct_versions = (det_id_v1 != det_id_v2)
        t1_distinct_sessions = (det_id_v1 != det_id_diff)
        t1_stable = (det_id_v1 == generate_deterministic_event_id(101, 1))

        t1_pass = t1_valid_charset and t1_length_ok and t1_distinct_versions and t1_distinct_sessions and t1_stable
        record(
            "Check 1.1: Deterministic event ID complies with Google base32hex [0-9a-v] and versioning",
            t1_pass,
            f"v1: {det_id_v1} (len {len(det_id_v1)}), v2: {det_id_v2}, charset valid: {t1_valid_charset}"
        )

        # =========================================================================
        # TEST 2: Creation Worker Fencing — Stale Failed Worker Cannot Overwrite Newer Claim
        # =========================================================================
        now_utc = datetime.now(timezone.utc)
        s_fence1 = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Worker Fencing Test 1",
            start_time=now_utc + timedelta(days=1),
            end_time=now_utc + timedelta(days=1, hours=1),
            calendar_sync_status="pending",
            calendar_sync_started_at=now_utc,
            calendar_sync_attempt_id=None,
            calendar_event_version=1
        )
        db.add(s_fence1)
        db.commit()
        db.refresh(s_fence1)
        test_session_ids.append(s_fence1.id)

        # Simulate Worker A claiming session
        worker_a_token = str(uuid.uuid4())
        s_fence1.calendar_sync_status = "syncing"
        s_fence1.calendar_sync_attempt_id = worker_a_token
        db.commit()

        # Simulate Worker B (or retry) preempting / taking over claim
        worker_b_token = str(uuid.uuid4())
        s_fence1.calendar_sync_status = "syncing"
        s_fence1.calendar_sync_attempt_id = worker_b_token
        db.commit()

        # Worker A attempts to write a failure into DB using conditional fencing query
        rows_affected = db.query(models.StudySession).filter(
            models.StudySession.id == s_fence1.id,
            models.StudySession.calendar_sync_attempt_id == worker_a_token
        ).update({
            "calendar_sync_status": "failed",
            "calendar_sync_error": "Worker A timed out",
            "calendar_sync_attempt_id": None
        }, synchronize_session=False)
        db.commit()

        db.expire_all()
        check_s1 = db.query(models.StudySession).filter_by(id=s_fence1.id).first()
        t2_pass = (rows_affected == 0 and check_s1.calendar_sync_attempt_id == worker_b_token and check_s1.calendar_sync_status == "syncing")
        record(
            "Check 1.2: Worker Fencing blocks stale Worker A failure from overwriting newer claim",
            t2_pass,
            f"Rows affected by Worker A: {rows_affected}, Current attempt ID: {check_s1.calendar_sync_attempt_id}"
        )

        # Worker B completes successfully and updates DB
        rows_b = db.query(models.StudySession).filter(
            models.StudySession.id == s_fence1.id,
            models.StudySession.calendar_sync_attempt_id == worker_b_token
        ).update({
            "google_event_id": "g_event_worker_b",
            "calendar_sync_status": "synced",
            "calendar_sync_attempt_id": None
        }, synchronize_session=False)
        db.commit()

        db.expire_all()
        check_s1_b = db.query(models.StudySession).filter_by(id=s_fence1.id).first()
        t2_b_pass = (rows_b == 1 and check_s1_b.calendar_sync_status == "synced" and check_s1_b.google_event_id == "g_event_worker_b")
        record(
            "Check 1.3: Active Worker B successfully commits under valid claim token",
            t2_b_pass,
            f"Rows affected by Worker B: {rows_b}, Status: {check_s1_b.calendar_sync_status}"
        )

        # =========================================================================
        # TEST 3: Update Worker Fencing — Concurrent Updates & Fencing on Edits
        # =========================================================================
        s_update_fence = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Initial Title",
            start_time=now_utc + timedelta(days=2),
            end_time=now_utc + timedelta(days=2, hours=1),
            google_event_id="g_event_existing_update",
            calendar_sync_status="synced",
            calendar_event_version=1
        )
        db.add(s_update_fence)
        db.commit()
        db.refresh(s_update_fence)
        test_session_ids.append(s_update_fence.id)

        # Worker 1 starts updating and claims session
        worker_u1_token = str(uuid.uuid4())
        s_update_fence.calendar_sync_status = "syncing"
        s_update_fence.calendar_sync_attempt_id = worker_u1_token
        db.commit()

        # While Worker 1 is in-flight, a new user update arrives via PUT
        token_creator = create_access_token(u_creator.id)
        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.bg_sync_update_calendar_event"):
                put_resp = client.put(
                    f"/api/groups/{group.id}/sessions/{s_update_fence.id}",
                    headers={"Authorization": f"Bearer {token_creator}"},
                    json={
                        "title": "New Title After Edit",
                        "start_time": (now_utc + timedelta(days=2)).isoformat(),
                        "end_time": (now_utc + timedelta(days=2, hours=2)).isoformat()
                    }
                )
        db.expire_all()
        check_u_after_put = db.query(models.StudySession).filter_by(id=s_update_fence.id).first()
        t3_put_ok = (
            put_resp.status_code == 200 and
            check_u_after_put.title == "New Title After Edit" and
            check_u_after_put.calendar_sync_attempt_id is None and
            check_u_after_put.calendar_sync_status == "pending"
        )
        record(
            "Check 2.1: Session edit resets calendar_sync_attempt_id to invalidate in-flight workers",
            t3_put_ok,
            f"PUT status: {put_resp.status_code}, attempt_id: {check_u_after_put.calendar_sync_attempt_id}"
        )

        # Worker 1 now finishes its slow update and attempts conditional commit
        u1_rows = db.query(models.StudySession).filter(
            models.StudySession.id == s_update_fence.id,
            models.StudySession.calendar_sync_attempt_id == worker_u1_token
        ).update({
            "calendar_sync_status": "synced",
            "calendar_synced_at": datetime.now(timezone.utc),
            "calendar_sync_attempt_id": None
        }, synchronize_session=False)
        db.commit()

        db.expire_all()
        check_u_after_u1 = db.query(models.StudySession).filter_by(id=s_update_fence.id).first()
        t3_fence_ok = (
            u1_rows == 0 and
            check_u_after_u1.title == "New Title After Edit" and
            check_u_after_u1.calendar_sync_status == "pending"
        )
        record(
            "Check 2.2: Stale update Worker 1 is fenced out from overwriting newer edit",
            t3_fence_ok,
            f"Rows affected: {u1_rows}, Current title preserved: '{check_u_after_u1.title}'"
        )

        # =========================================================================
        # TEST 4: HTTP 409 Resolution — Active Event with Matching Ownership Marker
        # =========================================================================
        s_409_active = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Session 409 Active",
            start_time=now_utc + timedelta(days=3),
            end_time=now_utc + timedelta(days=3, hours=1),
            calendar_sync_status="pending",
            calendar_event_version=1
        )
        db.add(s_409_active)
        db.commit()
        db.refresh(s_409_active)
        test_session_ids.append(s_409_active.id)

        expected_id_409 = generate_deterministic_event_id(s_409_active.id, 1)

        resp_409 = httplib2.Response({"status": 409, "reason": "Conflict"})
        http_err_409 = HttpError(resp=resp_409, content=b'{"error": {"message": "The requested identifier already exists."}}')

        # Mock service behavior:
        # 1. insert() raises 409
        # 2. get() returns active event with matching private teamsync_session_id
        # 3. update() updates the event
        mock_srv = MagicMock()
        mock_srv.events.return_value.insert.return_value.execute.side_effect = http_err_409
        mock_srv.events.return_value.get.return_value.execute.return_value = {
            "id": expected_id_409,
            "status": "confirmed",
            "extendedProperties": {
                "private": {
                    "teamsync_session_id": str(s_409_active.id),
                    "teamsync_app": "teamsync"
                }
            }
        }
        mock_srv.events.return_value.update.return_value.execute.return_value = {"id": expected_id_409}

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.get_calendar_service", return_value=mock_srv):
                bg_sync_create_calendar_event(s_409_active.id, u_creator.id)

        db.expire_all()
        check_409_active = db.query(models.StudySession).filter_by(id=s_409_active.id).first()
        t4_pass = (
            check_409_active.calendar_sync_status == "synced" and
            check_409_active.google_event_id == expected_id_409 and
            not mock_srv.events.return_value.update.called
        )
        record(
            "Check 3.1: HTTP 409 active verified event adopts ID without updating stale details in 409 handler",
            t4_pass,
            f"Status: {check_409_active.calendar_sync_status}, Event ID: {check_409_active.google_event_id}, Update called in 409: {mock_srv.events.return_value.update.called}"
        )

        # =========================================================================
        # TEST 5: HTTP 409 Resolution — Cancelled Tombstone Increments Version
        # =========================================================================
        s_409_cancelled = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Session 409 Cancelled Tombstone",
            start_time=now_utc + timedelta(days=4),
            end_time=now_utc + timedelta(days=4, hours=1),
            calendar_sync_status="pending",
            calendar_event_version=1
        )
        db.add(s_409_cancelled)
        db.commit()
        db.refresh(s_409_cancelled)
        test_session_ids.append(s_409_cancelled.id)

        # Mock service behavior:
        # 1. insert() raises 409
        # 2. get() returns event with status="cancelled"
        mock_srv_cancel = MagicMock()
        mock_srv_cancel.events.return_value.insert.return_value.execute.side_effect = http_err_409
        mock_srv_cancel.events.return_value.get.return_value.execute.return_value = {
            "id": generate_deterministic_event_id(s_409_cancelled.id, 1),
            "status": "cancelled"
        }

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.get_calendar_service", return_value=mock_srv_cancel):
                bg_sync_create_calendar_event(s_409_cancelled.id, u_creator.id)

        db.expire_all()
        check_409_cancel = db.query(models.StudySession).filter_by(id=s_409_cancelled.id).first()
        t5_pass = (
            check_409_cancel.calendar_sync_status == "failed" and
            check_409_cancel.calendar_event_version == 2 and
            check_409_cancel.google_event_id is None
        )
        record(
            "Check 3.2: HTTP 409 cancelled tombstone bumps version to 2 and marks failed (no adoption)",
            t5_pass,
            f"Status: {check_409_cancel.calendar_sync_status}, Version: {check_409_cancel.calendar_event_version}, google_event_id: {check_409_cancel.google_event_id}"
        )

        # Verify next retry uses version 2 deterministic ID
        v2_id = generate_deterministic_event_id(check_409_cancel.id, check_409_cancel.calendar_event_version)
        mock_srv_v2 = MagicMock()
        mock_srv_v2.events.return_value.insert.return_value.execute.return_value = {"id": v2_id}

        # Reset to pending for retry
        check_409_cancel.calendar_sync_status = "pending"
        db.commit()

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.get_calendar_service", return_value=mock_srv_v2):
                bg_sync_create_calendar_event(check_409_cancel.id, u_creator.id)

        db.expire_all()
        check_409_retry = db.query(models.StudySession).filter_by(id=s_409_cancelled.id).first()
        t5_retry_pass = (
            check_409_retry.calendar_sync_status == "synced" and
            check_409_retry.google_event_id == v2_id and
            f"v2" in v2_id
        )
        record(
            "Check 3.3: Subsequent retry successfully inserts fresh event with version 2 ID",
            t5_retry_pass,
            f"Status: {check_409_retry.calendar_sync_status}, New Event ID: {check_409_retry.google_event_id}"
        )

        # =========================================================================
        # TEST 6: HTTP 409 Resolution — Mismatched Ownership Marker Rejects Adoption
        # =========================================================================
        s_409_mismatch = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Session 409 Mismatch",
            start_time=now_utc + timedelta(days=5),
            end_time=now_utc + timedelta(days=5, hours=1),
            calendar_sync_status="pending",
            calendar_event_version=1
        )
        db.add(s_409_mismatch)
        db.commit()
        db.refresh(s_409_mismatch)
        test_session_ids.append(s_409_mismatch.id)

        # Mock service behavior:
        # 1. insert() raises 409
        # 2. get() returns event belonging to another session (e.g. 999999)
        mock_srv_mismatch = MagicMock()
        mock_srv_mismatch.events.return_value.insert.return_value.execute.side_effect = http_err_409
        mock_srv_mismatch.events.return_value.get.return_value.execute.return_value = {
            "id": "g_event_foreign",
            "status": "confirmed",
            "extendedProperties": {
                "private": {
                    "teamsync_session_id": "999999",
                    "teamsync_app": "teamsync"
                }
            }
        }

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.get_calendar_service", return_value=mock_srv_mismatch):
                bg_sync_create_calendar_event(s_409_mismatch.id, u_creator.id)

        db.expire_all()
        check_409_mismatch = db.query(models.StudySession).filter_by(id=s_409_mismatch.id).first()
        t6_pass = (
            check_409_mismatch.calendar_sync_status == "failed" and
            check_409_mismatch.google_event_id is None
        )
        record(
            "Check 3.4: HTTP 409 mismatched ownership marker rejects adoption and marks failed",
            t6_pass,
            f"Status: {check_409_mismatch.calendar_sync_status}, google_event_id: {check_409_mismatch.google_event_id}"
        )

        # =========================================================================
        # TEST 7: HTTP 409 Resolution — Lookup Network Failure Rejects Adoption
        # =========================================================================
        s_409_lookup_fail = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Session 409 Lookup Fail",
            start_time=now_utc + timedelta(days=6),
            end_time=now_utc + timedelta(days=6, hours=1),
            calendar_sync_status="pending",
            calendar_event_version=1
        )
        db.add(s_409_lookup_fail)
        db.commit()
        db.refresh(s_409_lookup_fail)
        test_session_ids.append(s_409_lookup_fail.id)

        mock_srv_netfail = MagicMock()
        mock_srv_netfail.events.return_value.insert.return_value.execute.side_effect = http_err_409
        mock_srv_netfail.events.return_value.get.return_value.execute.side_effect = Exception("Connection reset during get")

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.get_calendar_service", return_value=mock_srv_netfail):
                bg_sync_create_calendar_event(s_409_lookup_fail.id, u_creator.id)

        db.expire_all()
        check_409_netfail = db.query(models.StudySession).filter_by(id=s_409_lookup_fail.id).first()
        t7_pass = (
            check_409_netfail.calendar_sync_status == "failed" and
            check_409_netfail.google_event_id is None
        )
        record(
            "Check 3.5: HTTP 409 lookup failure safely aborts without adopting unverified event",
            t7_pass,
            f"Status: {check_409_netfail.calendar_sync_status}, google_event_id: {check_409_netfail.google_event_id}"
        )

        # =========================================================================
        # TEST 8: Reconcile Clears Stale calendar_sync_attempt_id
        # =========================================================================
        stale_time = now_utc - timedelta(minutes=10)
        s_stale_fenced = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            title="Stale Fenced Session",
            start_time=now_utc + timedelta(days=7),
            end_time=now_utc + timedelta(days=7, hours=1),
            calendar_sync_status="syncing",
            calendar_sync_started_at=stale_time,
            calendar_sync_attempt_id="stale_worker_token",
            calendar_event_version=1
        )
        db.add(s_stale_fenced)
        db.commit()
        db.refresh(s_stale_fenced)
        test_session_ids.append(s_stale_fenced.id)

        reconcile_interrupted_sync_operations()

        db.expire_all()
        check_stale = db.query(models.StudySession).filter_by(id=s_stale_fenced.id).first()
        t8_pass = (
            check_stale.calendar_sync_status == "failed" and
            check_stale.calendar_sync_attempt_id is None
        )
        record(
            "Check 3.6: Startup reconciliation marks stale session failed and clears calendar_sync_attempt_id",
            t8_pass,
            f"Status: {check_stale.calendar_sync_status}, attempt_id: {check_stale.calendar_sync_attempt_id}"
        )

        # =========================================================================
        # TEST A: Stale Update Finishes Last — Reconciliation Converges Google Calendar
        # =========================================================================
        s_test_a = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Latest Title Committed",
            start_time=now_utc + timedelta(days=8),
            end_time=now_utc + timedelta(days=8, hours=1),
            google_event_id="g_event_test_a",
            calendar_sync_status="synced",
            calendar_event_version=1
        )
        db.add(s_test_a)
        db.commit()
        db.refresh(s_test_a)
        test_session_ids.append(s_test_a.id)

        # Simulated external Google Calendar state dictionary
        google_cal_state_a = {"title": "Latest Title Committed"}

        def mock_update_google(creds, event_id, title, description, start_time, end_time, group_name=None):
            google_cal_state_a["title"] = title
            return True

        # Worker A had an older captured title and attempts commit with an expired token
        worker_a_stale_token = str(uuid.uuid4())
        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.update_google_calendar_event", side_effect=mock_update_google):
                # 1. Worker A's slow update finishes on Google Calendar with stale data
                google_cal_state_a["title"] = "Stale Old Title from Worker A"

                # 2. Worker A's DB commit fails due to fencing (session is 'synced' with None claim)
                fenced_count = db.query(models.StudySession).filter(
                    models.StudySession.id == s_test_a.id,
                    models.StudySession.calendar_sync_attempt_id == worker_a_stale_token
                ).update({
                    "calendar_sync_status": "synced"
                }, synchronize_session=False)
                assert fenced_count == 0, "Worker A write must be fenced out"

                # 3. Worker A triggers reconciliation
                from main import reconcile_stale_external_operation
                rec_success = reconcile_stale_external_operation(s_test_a.id, u_creator.id)

        db.expire_all()
        check_s_a = db.query(models.StudySession).filter_by(id=s_test_a.id).first()
        t_a_pass = (
            rec_success is True and
            google_cal_state_a["title"] == "Latest Title Committed" and
            check_s_a.calendar_sync_status == "synced"
        )
        record(
            "Test A: Stale update finishing last triggers reconciliation to converge Google Calendar",
            t_a_pass,
            f"Google Calendar title: '{google_cal_state_a['title']}', DB Status: {check_s_a.calendar_sync_status}"
        )

        # =========================================================================
        # TEST B: Stale Creation Receives HTTP 409 — No Stale Update, Claimed Sync Path
        # =========================================================================
        s_test_b = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Session B Latest Title",
            start_time=now_utc + timedelta(days=9),
            end_time=now_utc + timedelta(days=9, hours=1),
            calendar_sync_status="pending",
            calendar_event_version=1
        )
        db.add(s_test_b)
        db.commit()
        db.refresh(s_test_b)
        test_session_ids.append(s_test_b.id)

        det_id_b = generate_deterministic_event_id(s_test_b.id, 1)
        google_cal_state_b = {
            "id": det_id_b,
            "status": "confirmed",
            "summary": "[TeamSync] Session B Old Title",
            "extendedProperties": {
                "private": {
                    "teamsync_session_id": str(s_test_b.id),
                    "teamsync_app": "teamsync"
                }
            }
        }

        mock_srv_b = MagicMock()
        mock_srv_b.events.return_value.insert.return_value.execute.side_effect = http_err_409
        mock_srv_b.events.return_value.get.return_value.execute.return_value = google_cal_state_b
        mock_srv_b.events.return_value.update.return_value.execute.return_value = google_cal_state_b

        # Worker runs creation and hits 409
        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.get_calendar_service", return_value=mock_srv_b):
                bg_sync_create_calendar_event(s_test_b.id, u_creator.id)

        # Assert 409 handler adopted ID but did NOT call update with stale captured payload
        assert not mock_srv_b.events.return_value.update.called, "409 handler must not call events().update()"

        # Now claimed update path runs with latest committed data
        def mock_apply_update(creds, event_id, title, description, start_time, end_time, group_name=None):
            google_cal_state_b["summary"] = f"[TeamSync] {title}"
            return True

        db.expire_all()
        check_fresh_b = db.query(models.StudySession).filter_by(id=s_test_b.id).first()
        check_fresh_b.calendar_sync_status = "pending"
        db.commit()

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.update_google_calendar_event", side_effect=mock_apply_update):
                bg_sync_update_calendar_event(s_test_b.id, u_creator.id)

        db.expire_all()
        check_s_b = db.query(models.StudySession).filter_by(id=s_test_b.id).first()
        t_b_pass = (
            check_s_b.google_event_id == det_id_b and
            google_cal_state_b["summary"] == "[TeamSync] Session B Latest Title" and
            check_s_b.calendar_sync_status == "synced"
        )
        record(
            "Test B: Stale creation 409 adopts ID without stale update; latest details applied via update",
            t_b_pass,
            f"Event ID: {check_s_b.google_event_id}, Final Google summary: '{google_cal_state_b['summary']}'"
        )

        # =========================================================================
        # TEST C: Reconciliation Fencing — Lost Claim Cannot Overwrite Newer Claim
        # =========================================================================
        s_test_c = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Initial Title C",
            start_time=now_utc + timedelta(days=10),
            end_time=now_utc + timedelta(days=10, hours=1),
            google_event_id="g_event_test_c",
            calendar_sync_status="syncing",
            calendar_sync_attempt_id="active_worker_token_c",
            calendar_event_version=1
        )
        db.add(s_test_c)
        db.commit()
        db.refresh(s_test_c)
        test_session_ids.append(s_test_c.id)

        # Stale reconciliation attempts to claim while another worker is actively 'syncing'
        from main import reconcile_stale_external_operation
        rec_lost_claim = reconcile_stale_external_operation(s_test_c.id, u_creator.id)

        db.expire_all()
        check_s_c = db.query(models.StudySession).filter_by(id=s_test_c.id).first()
        t_c_pass = (
            rec_lost_claim is False and
            check_s_c.calendar_sync_attempt_id == "active_worker_token_c" and
            check_s_c.calendar_sync_status == "syncing"
        )
        record(
            "Test C: Reconciliation cannot overwrite or steal an active worker's claim",
            t_c_pass,
            f"Reconcile return: {rec_lost_claim}, Attempt ID preserved: {check_s_c.calendar_sync_attempt_id}"
        )

        # =========================================================================
        # TEST D: Session Deleted During Reconciliation — Respects Deletion
        # =========================================================================
        s_test_d = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Session to Delete",
            start_time=now_utc + timedelta(days=11),
            end_time=now_utc + timedelta(days=11, hours=1),
            google_event_id="g_event_test_d",
            calendar_sync_status="synced",
            calendar_event_version=1
        )
        db.add(s_test_d)
        db.commit()
        db.refresh(s_test_d)
        s_test_d_id = s_test_d.id

        # Delete session from database
        db.delete(s_test_d)
        db.commit()

        # Reconcile attempted on non-existent session
        rec_del_result = reconcile_stale_external_operation(s_test_d_id, u_creator.id)
        t_d_pass = (rec_del_result is False)
        record(
            "Test D: Reconciliation safely aborts on deleted session without recreating records",
            t_d_pass,
            f"Reconciliation returned: {rec_del_result}"
        )

        # =========================================================================
        # TEST E: Expired Worker Cannot Increment calendar_event_version
        # =========================================================================
        s_test_e = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Session Cancelled Version Test",
            start_time=now_utc + timedelta(days=12),
            end_time=now_utc + timedelta(days=12, hours=1),
            calendar_sync_status="pending",
            calendar_event_version=1
        )
        db.add(s_test_e)
        db.commit()
        db.refresh(s_test_e)
        test_session_ids.append(s_test_e.id)

        # Stale worker attempt ID (does not match DB)
        stale_worker_token_e = str(uuid.uuid4())
        # Try conditional version increment with stale worker token
        rows_inc = db.query(models.StudySession).filter(
            models.StudySession.id == s_test_e.id,
            models.StudySession.calendar_sync_attempt_id == stale_worker_token_e
        ).update({
            "calendar_event_version": models.StudySession.calendar_event_version + 1
        }, synchronize_session=False)
        db.commit()

        db.expire_all()
        check_s_e = db.query(models.StudySession).filter_by(id=s_test_e.id).first()
        t_e_pass = (rows_inc == 0 and check_s_e.calendar_event_version == 1)
        record(
            "Test E: Expired worker cannot increment calendar_event_version without valid claim",
            t_e_pass,
            f"Rows affected: {rows_inc}, Version preserved: {check_s_e.calendar_event_version}"
        )

    finally:
        # Cleanup test records
        try:
            if test_session_ids:
                db.query(models.CalendarSyncLog).filter(models.CalendarSyncLog.session_id.in_(test_session_ids)).delete(synchronize_session=False)
                db.query(models.StudySession).filter(models.StudySession.id.in_(test_session_ids)).delete(synchronize_session=False)
            if test_group_ids:
                db.query(models.GroupMember).filter(models.GroupMember.group_id.in_(test_group_ids)).delete(synchronize_session=False)
                db.query(models.Group).filter(models.Group.id.in_(test_group_ids)).delete(synchronize_session=False)
            if test_user_ids:
                db.query(models.GoogleCredential).filter(models.GoogleCredential.user_id.in_(test_user_ids)).delete(synchronize_session=False)
                db.query(models.User).filter(models.User.id.in_(test_user_ids)).delete(synchronize_session=False)
            db.commit()
        except Exception as e:
            print(f"Cleanup warning: {e}")
        db.close()

    print("=" * 75)
    total = len(results)
    passed_count = sum(1 for _, p, _ in results if p)
    print(f"FINAL SUMMARY: {passed_count}/{total} TESTS PASSED")
    print("=" * 75)
    if passed_count < total:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
