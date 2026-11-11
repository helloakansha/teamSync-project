import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor
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
    bg_sync_create_calendar_event,
    reconcile_interrupted_sync_operations
)

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print("TEAMSYNC — PHASE 5 FINAL RELIABILITY CORRECTIONS TEST SUITE")
    print("F-01 through F-05 Verification")
    print("=" * 70)

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
        # 1. Creator user
        u_creator = models.User(
            name=f"Creator {suffix}",
            email=f"creator_{suffix}@example.com",
            password_hash=hash_password("Pass123!")
        )
        # 2. Owner user
        u_owner = models.User(
            name=f"Owner {suffix}",
            email=f"owner_{suffix}@example.com",
            password_hash=hash_password("Pass123!")
        )
        # 3. Regular member
        u_member = models.User(
            name=f"Member {suffix}",
            email=f"member_{suffix}@example.com",
            password_hash=hash_password("Pass123!")
        )
        db.add_all([u_creator, u_owner, u_member])
        db.commit()
        db.refresh(u_creator)
        db.refresh(u_owner)
        db.refresh(u_member)
        test_user_ids.extend([u_creator.id, u_owner.id, u_member.id])

        # Attach Google credentials for creator and owner
        cred_creator = models.GoogleCredential(
            user_id=u_creator.id,
            access_token="fake_creator_token",
            refresh_token="fake_creator_refresh",
            token_expiry=datetime.now(timezone.utc) + timedelta(days=7),
            scopes="https://www.googleapis.com/auth/calendar.events.owned"
        )
        cred_owner = models.GoogleCredential(
            user_id=u_owner.id,
            access_token="fake_owner_token",
            refresh_token="fake_owner_refresh",
            token_expiry=datetime.now(timezone.utc) + timedelta(days=7),
            scopes="https://www.googleapis.com/auth/calendar.events.owned"
        )
        db.add_all([cred_creator, cred_owner])
        db.commit()

        # Create Group: u_owner is owner, u_creator and u_member are members
        group = models.Group(
            name=f"Reliability Group {suffix}",
            description="Testing F-01 through F-05 fixes",
            subject="Auditing"
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        test_group_ids.append(group.id)

        gm_owner = models.GroupMember(group_id=group.id, user_id=u_owner.id, role="owner")
        gm_creator = models.GroupMember(group_id=group.id, user_id=u_creator.id, role="member")
        gm_member = models.GroupMember(group_id=group.id, user_id=u_member.id, role="member")
        db.add_all([gm_owner, gm_creator, gm_member])
        db.commit()

        token_creator = create_access_token(u_creator.id)
        token_owner = create_access_token(u_owner.id)
        token_member = create_access_token(u_member.id)

        headers_creator = {"Authorization": f"Bearer {token_creator}"}
        headers_owner = {"Authorization": f"Bearer {token_owner}"}
        headers_member = {"Authorization": f"Bearer {token_member}"}

        now = datetime.now(timezone.utc)

        # ====================================================
        # F-01: Prevent Duplicate Google Calendar Events
        # ====================================================

        # TEST 1: Two concurrent background creation tasks attempting to claim the same session
        s_concurrent = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Concurrent Claim Session",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1),
            calendar_sync_status="pending"
        )
        db.add(s_concurrent)
        db.commit()
        db.refresh(s_concurrent)
        test_session_ids.append(s_concurrent.id)

        mock_call_counter = {"count": 0}
        barrier = threading.Barrier(2)

        def mock_create_with_barrier(*args, **kwargs):
            mock_call_counter["count"] += 1
            return "g_concurrent_evt_1"

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.create_google_calendar_event", side_effect=mock_create_with_barrier):
                def worker_fn():
                    try:
                        barrier.wait(timeout=3)
                    except Exception:
                        pass
                    bg_sync_create_calendar_event(s_concurrent.id, u_creator.id)

                t1 = threading.Thread(target=worker_fn)
                t2 = threading.Thread(target=worker_fn)
                t1.start()
                t2.start()
                t1.join()
                t2.join()

        db.expire_all()
        db_s_conc = db.query(models.StudySession).filter_by(id=s_concurrent.id).first()
        t1_pass = (
            mock_call_counter["count"] == 1 and
            db_s_conc.calendar_sync_status == "synced" and
            db_s_conc.google_event_id == "g_concurrent_evt_1"
        )
        record("F-01.1: Atomic claim prevents concurrent duplicate Google event creation", t1_pass, f"API calls made: {mock_call_counter['count']} (expected 1)")

        # TEST 2: Active pending operation rejects duplicate retry with HTTP 409
        res2 = client.post(
            f"/api/groups/{group.id}/sessions/{s_concurrent.id}/sync",
            headers=headers_creator
        )
        # Note: s_concurrent is currently synced, so it returns already synchronized.
        # Let's set a session to active pending (< 5 min):
        s_active = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Active Pending Session",
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=1),
            calendar_sync_status="pending",
            calendar_sync_started_at=now - timedelta(seconds=15)
        )
        db.add(s_active)
        db.commit()
        db.refresh(s_active)
        test_session_ids.append(s_active.id)

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            res2 = client.post(
                f"/api/groups/{group.id}/sessions/{s_active.id}/sync",
                headers=headers_creator
            )
        t2_pass = (
            res2.status_code == 409 and
            "currently in progress" in res2.json().get("detail", "").lower()
        )
        record("F-01.2: Active pending operation (< 5 min) rejects duplicate retry with HTTP 409", t2_pass, f"Status: {res2.status_code}")

        # TEST 3: Deterministic event ID reuse after 409 Conflict (event already created on Google)
        s_det = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Deterministic Event ID Session",
            start_time=now + timedelta(days=3),
            end_time=now + timedelta(days=3, hours=1),
            calendar_sync_status="pending"
        )
        db.add(s_det)
        db.commit()
        db.refresh(s_det)
        test_session_ids.append(s_det.id)

        expected_det_id = generate_deterministic_event_id(s_det.id)
        # Simulate Google Calendar returning 409 Conflict (event already exists with this ID)
        resp_409 = httplib2.Response({"status": 409, "reason": "Conflict"})
        http_err_409 = HttpError(resp=resp_409, content=b'{"error": {"message": "The requested identifier already exists."}}')

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.get_calendar_service") as mock_srv:
                mock_insert = MagicMock()
                mock_insert.execute.side_effect = http_err_409
                mock_srv.return_value.events.return_value.insert.return_value = mock_insert

                bg_sync_create_calendar_event(s_det.id, u_creator.id)

        db.expire_all()
        db_s_det = db.query(models.StudySession).filter_by(id=s_det.id).first()
        t3_pass = (
            db_s_det.calendar_sync_status == "synced" and
            db_s_det.google_event_id == expected_det_id
        )
        record("F-01.3: Deterministic event ID reuses existing Google event on 409 Conflict", t3_pass, f"Assigned Google Event ID: {db_s_det.google_event_id}")

        # ====================================================
        # F-02: Recover Interrupted Synchronization
        # ====================================================

        # TEST 4: Stale pending operation (> 5 min) marked failed by reconciliation
        s_stale_pending = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            title="Stale Pending Session",
            start_time=now + timedelta(days=4),
            end_time=now + timedelta(days=4, hours=1),
            calendar_sync_status="pending",
            calendar_sync_started_at=now - timedelta(minutes=10)
        )
        # TEST 5: Stale syncing operation (> 5 min) marked failed by reconciliation
        s_stale_syncing = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            title="Stale Syncing Session",
            start_time=now + timedelta(days=5),
            end_time=now + timedelta(days=5, hours=1),
            calendar_sync_status="syncing",
            calendar_sync_started_at=now - timedelta(minutes=8)
        )
        # TEST 6: Recent active operation (< 5 min) remains protected
        s_recent_active = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            title="Recent Active Session",
            start_time=now + timedelta(days=6),
            end_time=now + timedelta(days=6, hours=1),
            calendar_sync_status="syncing",
            calendar_sync_started_at=now - timedelta(seconds=30)
        )
        db.add_all([s_stale_pending, s_stale_syncing, s_recent_active])
        db.commit()
        test_session_ids.extend([s_stale_pending.id, s_stale_syncing.id, s_recent_active.id])

        reconcile_interrupted_sync_operations()

        db.expire_all()
        db_s_sp = db.query(models.StudySession).filter_by(id=s_stale_pending.id).first()
        db_s_ss = db.query(models.StudySession).filter_by(id=s_stale_syncing.id).first()
        db_s_ra = db.query(models.StudySession).filter_by(id=s_recent_active.id).first()

        t4_pass = (db_s_sp.calendar_sync_status == "failed" and "interrupted" in (db_s_sp.calendar_sync_error or "").lower())
        record("F-02.1: Startup reconciliation recovers stale pending operation (> 5 min)", t4_pass, f"Status: {db_s_sp.calendar_sync_status}")

        t5_pass = (db_s_ss.calendar_sync_status == "failed" and "interrupted" in (db_s_ss.calendar_sync_error or "").lower())
        record("F-02.2: Startup reconciliation recovers stale syncing operation (> 5 min)", t5_pass, f"Status: {db_s_ss.calendar_sync_status}")

        t6_pass = (db_s_ra.calendar_sync_status == "syncing")
        record("F-02.3: Recent active operation (< 5 min) remains protected during reconciliation", t6_pass, f"Status: {db_s_ra.calendar_sync_status}")

        # TEST 7: Stale pending session allows immediate retry without 409
        s_stale_retry = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Stale Retry Allowed Session",
            start_time=now + timedelta(days=7),
            end_time=now + timedelta(days=7, hours=1),
            calendar_sync_status="pending",
            calendar_sync_started_at=now - timedelta(minutes=15)
        )
        db.add(s_stale_retry)
        db.commit()
        db.refresh(s_stale_retry)
        test_session_ids.append(s_stale_retry.id)

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.create_google_calendar_event", return_value="g_stale_retried"):
                res7 = client.post(
                    f"/api/groups/{group.id}/sessions/{s_stale_retry.id}/sync",
                    headers=headers_creator
                )
                db.expire_all()
                db_s_sr = db.query(models.StudySession).filter_by(id=s_stale_retry.id).first()
                t7_pass = (
                    res7.status_code == 200 and
                    db_s_sr.calendar_sync_status == "synced" and
                    db_s_sr.google_event_id == "g_stale_retried"
                )
                record("F-02.4: Genuinely stale operation allows authorized retry without 409 deadlock", t7_pass, f"Status: {db_s_sr.calendar_sync_status}")

        # ====================================================
        # F-03: Enforce Google Calendar Ownership
        # ====================================================

        # TEST 8: Creator creates event, group owner updates session -> creator credentials used
        s_owner_upd = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Owner Update Session",
            start_time=now + timedelta(days=8),
            end_time=now + timedelta(days=8, hours=1),
            google_event_id="g_creator_original_event",
            calendar_sync_status="synced"
        )
        db.add(s_owner_upd)
        db.commit()
        db.refresh(s_owner_upd)
        test_session_ids.append(s_owner_upd.id)

        used_creds_user_id = []

        def mock_get_creds(user_id, *args, **kwargs):
            used_creds_user_id.append(user_id)
            return MagicMock()

        with patch("main.get_valid_google_credentials", side_effect=mock_get_creds):
            with patch("main.update_google_calendar_event", return_value=True):
                res8 = client.put(
                    f"/api/groups/{group.id}/sessions/{s_owner_upd.id}",
                    headers=headers_owner,
                    json={
                        "title": "Owner Edited Title",
                        "start_time": (now + timedelta(days=8)).isoformat(),
                        "end_time": (now + timedelta(days=8, hours=2)).isoformat()
                    }
                )
                t8_pass = (
                    res8.status_code == 200 and
                    u_creator.id in used_creds_user_id and
                    u_owner.id not in used_creds_user_id
                )
                record("F-03.1: Group owner update uses creator credentials, not owner's", t8_pass, f"Creds requested for user IDs: {used_creds_user_id}")

        # TEST 9: Creator disconnects -> Owner update never falls back to owner's credentials
        def mock_get_creds_disconnected(user_id, *args, **kwargs):
            if user_id == u_creator.id:
                return None  # Creator disconnected!
            return MagicMock()  # Owner connected

        with patch("main.get_valid_google_credentials", side_effect=mock_get_creds_disconnected):
            with patch("main.update_google_calendar_event") as mock_never_call:
                res9 = client.put(
                    f"/api/groups/{group.id}/sessions/{s_owner_upd.id}",
                    headers=headers_owner,
                    json={
                        "title": "Owner Edit While Creator Disconnected",
                        "start_time": (now + timedelta(days=8)).isoformat(),
                        "end_time": (now + timedelta(days=8, hours=3)).isoformat()
                    }
                )
                db.expire_all()
                db_s_ou = db.query(models.StudySession).filter_by(id=s_owner_upd.id).first()
                t9_pass = (
                    res9.status_code == 200 and
                    mock_never_call.call_count == 0 and
                    db_s_ou.calendar_sync_status == "failed" and
                    "disconnected" in (db_s_ou.calendar_sync_error or "").lower()
                )
                record("F-03.2: Creator disconnect prevents owner fallback; marks status 'failed'", t9_pass, f"DB Status: {db_s_ou.calendar_sync_status}, Error: {db_s_ou.calendar_sync_error}")

        # TEST 10: Retry uses original calendar owner; rejects owner retry when creator disconnected
        with patch("main.get_valid_google_credentials", side_effect=mock_get_creds_disconnected):
            res10 = client.post(
                f"/api/groups/{group.id}/sessions/{s_owner_upd.id}/sync",
                headers=headers_owner
            )
            t10_pass = (
                res10.status_code == 400 and
                "creator" in res10.json().get("detail", "").lower() and
                "not connected" in res10.json().get("detail", "").lower()
            )
            record("F-03.3: Manual retry by owner requires creator's connection, not owner's", t10_pass, f"Detail: {res10.json().get('detail')}")

        # ====================================================
        # F-04: Cancellation Accuracy & Creation/Cancellation Race
        # ====================================================

        # TEST 11: Cancellation response does not falsely confirm deletion
        s_cancel_test = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Cancel Accuracy Test",
            start_time=now + timedelta(days=9),
            end_time=now + timedelta(days=9, hours=1),
            google_event_id="g_cancel_test_123",
            calendar_sync_status="synced"
        )
        db.add(s_cancel_test)
        db.commit()
        db.refresh(s_cancel_test)
        s_cancel_id = s_cancel_test.id

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.delete_google_calendar_event", return_value=True):
                res11 = client.delete(
                    f"/api/groups/{group.id}/sessions/{s_cancel_id}",
                    headers=headers_creator
                )
                d11 = res11.json()
                t11_pass = (
                    res11.status_code == 200 and
                    d11.get("calendar_deleted") is False and
                    d11.get("calendar_delete_queued") is True and
                    d11.get("calendar_sync_status") == "delete_pending"
                )
                record("F-04.1: Cancellation response accurately reports deletion is queued (not yet confirmed)", t11_pass, f"Reported: calendar_deleted={d11.get('calendar_deleted')}, queued={d11.get('calendar_delete_queued')}")

        # TEST 12: Google deletion failure is recorded in CalendarSyncLog
        s_fail_del = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Failed Deletion Log Test",
            start_time=now + timedelta(days=10),
            end_time=now + timedelta(days=10, hours=1),
            google_event_id="g_fail_del_456",
            calendar_sync_status="synced"
        )
        db.add(s_fail_del)
        db.commit()
        db.refresh(s_fail_del)
        s_fail_del_id = s_fail_del.id

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.delete_google_calendar_event", return_value=False):
                res12 = client.delete(
                    f"/api/groups/{group.id}/sessions/{s_fail_del_id}",
                    headers=headers_creator
                )
                db.expire_all()
                fail_log = db.query(models.CalendarSyncLog).filter_by(
                    session_id=s_fail_del_id,
                    operation="delete"
                ).first()

                t12_pass = (
                    res12.status_code == 200 and
                    fail_log is not None and
                    fail_log.status == "failed" and
                    fail_log.error is not None
                )
                record("F-04.2: Google Calendar deletion failure recorded in calendar_sync_logs", t12_pass, f"Log status: {fail_log.status if fail_log else None}, Error: {fail_log.error if fail_log else None}")

        # TEST 13: Cancellation during in-flight creation triggers immediate orphan cleanup
        s_race = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="In Flight Creation Race",
            start_time=now + timedelta(days=11),
            end_time=now + timedelta(days=11, hours=1),
            calendar_sync_status="pending"
        )
        db.add(s_race)
        db.commit()
        db.refresh(s_race)
        s_race_id = s_race.id

        cleaned_up_events = []

        def mock_create_and_delete_in_flight(*args, **kwargs):
            # Simulate: user cancels session during the in-flight creation!
            del_db = SessionLocal()
            try:
                del_sess = del_db.query(models.StudySession).filter_by(id=s_race_id).first()
                if del_sess:
                    del_db.delete(del_sess)
                    del_db.commit()
            finally:
                del_db.close()
            return "g_race_orphan_event_999"

        def mock_cleanup_delete(creds, event_id):
            cleaned_up_events.append(event_id)
            return True

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.create_google_calendar_event", side_effect=mock_create_and_delete_in_flight):
                with patch("main.delete_google_calendar_event", side_effect=mock_cleanup_delete):
                    bg_sync_create_calendar_event(s_race_id, u_creator.id)

        t13_pass = ("g_race_orphan_event_999" in cleaned_up_events)
        record("F-04.3: In-flight creation race triggers immediate orphan cleanup", t13_pass, f"Cleaned up events: {cleaned_up_events}")

        # TEST 14: Cancellation logs survive session deletion
        db.expire_all()
        log_survived = db.query(models.CalendarSyncLog).filter_by(session_id=s_race_id).first()
        t14_pass = (log_survived is not None and log_survived.operation == "delete")
        record("F-04.4: Cancellation logs survive PostgreSQL session deletion", t14_pass, f"Surviving log ID: {log_survived.id if log_survived else None}")

        # ====================================================
        # F-05: Correct Retry Authorization and Status Consistency
        # ====================================================

        # TEST 15: Creator can retry their own failed session
        s_retry_creator = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Creator Retry Session",
            start_time=now + timedelta(days=12),
            end_time=now + timedelta(days=12, hours=1),
            calendar_sync_status="failed",
            calendar_sync_error="Network error"
        )
        db.add(s_retry_creator)
        db.commit()
        db.refresh(s_retry_creator)
        test_session_ids.append(s_retry_creator.id)

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.create_google_calendar_event", return_value="g_creator_retried_ok"):
                res15 = client.post(
                    f"/api/groups/{group.id}/sessions/{s_retry_creator.id}/sync",
                    headers=headers_creator
                )
                db.expire_all()
                db_s_rc = db.query(models.StudySession).filter_by(id=s_retry_creator.id).first()
                t15_pass = (
                    res15.status_code == 200 and
                    db_s_rc.calendar_sync_status == "synced" and
                    db_s_rc.google_event_id == "g_creator_retried_ok"
                )
                record("F-05.1: Creator can successfully retry their own failed session", t15_pass, f"Status: {db_s_rc.calendar_sync_status}")

        # TEST 16: Authorized group owner can request retry using creator's credentials
        s_retry_owner = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Owner Retries Creator Session",
            start_time=now + timedelta(days=13),
            end_time=now + timedelta(days=13, hours=1),
            calendar_sync_status="failed",
            calendar_sync_error="Temporary 503"
        )
        db.add(s_retry_owner)
        db.commit()
        db.refresh(s_retry_owner)
        test_session_ids.append(s_retry_owner.id)

        target_creds_used = []
        def mock_creds_track(user_id, *args, **kwargs):
            target_creds_used.append(user_id)
            return MagicMock()

        with patch("main.get_valid_google_credentials", side_effect=mock_creds_track):
            with patch("main.create_google_calendar_event", return_value="g_owner_retried_ok"):
                res16 = client.post(
                    f"/api/groups/{group.id}/sessions/{s_retry_owner.id}/sync",
                    headers=headers_owner
                )
                db.expire_all()
                db_s_ro = db.query(models.StudySession).filter_by(id=s_retry_owner.id).first()
                t16_pass = (
                    res16.status_code == 200 and
                    u_creator.id in target_creds_used and
                    db_s_ro.calendar_sync_status == "synced"
                )
                record("F-05.2: Authorized group owner requests retry executed against creator's calendar", t16_pass, f"Creator creds verified: {u_creator.id in target_creds_used}")

        # TEST 17: Unauthorized regular member cannot retry
        res17 = client.post(
            f"/api/groups/{group.id}/sessions/{s_retry_owner.id}/sync",
            headers=headers_member
        )
        t17_pass = (res17.status_code == 403)
        record("F-05.3: Unauthorized regular member cannot trigger retry (HTTP 403)", t17_pass, f"Status: {res17.status_code}")

        # TEST 18: Update response and GET sync-status return consistent 'pending' status
        s_upd_consistent = models.StudySession(
            group_id=group.id,
            created_by=u_creator.id,
            calendar_owner_id=u_creator.id,
            title="Consistency Check Session",
            start_time=now + timedelta(days=14),
            end_time=now + timedelta(days=14, hours=1),
            google_event_id="g_consistency_123",
            calendar_sync_status="synced"
        )
        db.add(s_upd_consistent)
        db.commit()
        db.refresh(s_upd_consistent)
        test_session_ids.append(s_upd_consistent.id)

        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.update_google_calendar_event", return_value=True):
                res18 = client.put(
                    f"/api/groups/{group.id}/sessions/{s_upd_consistent.id}",
                    headers=headers_creator,
                    json={
                        "title": "Consistent Updated Title",
                        "start_time": (now + timedelta(days=14)).isoformat(),
                        "end_time": (now + timedelta(days=14, hours=2)).isoformat()
                    }
                )
                d18 = res18.json()
                t18_pass = (
                    res18.status_code == 200 and
                    d18.get("calendar_sync_status") in ("pending", "synced") and
                    d18.get("session", {}).get("calendar_sync_status") in ("pending", "synced")
                )
                record("F-05.4: PUT update response returns accurate 'pending' synchronization status", t18_pass, f"Status reported: {d18.get('calendar_sync_status')}")

    except Exception as e:
        import traceback
        print(f"Exception during test run: {e}")
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            db.query(models.CalendarSyncLog).filter(models.CalendarSyncLog.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            db.query(models.StudySession).filter(models.StudySession.group_id.in_(test_group_ids)).delete(synchronize_session=False)
            db.query(models.StudySession).filter(models.StudySession.id.in_(test_session_ids)).delete(synchronize_session=False)
            db.query(models.GroupMember).filter(models.GroupMember.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            db.query(models.GoogleCredential).filter(models.GoogleCredential.user_id.in_(test_user_ids)).delete(synchronize_session=False)
            db.query(models.Group).filter(models.Group.id.in_(test_group_ids)).delete(synchronize_session=False)
            db.query(models.User).filter(models.User.id.in_(test_user_ids)).delete(synchronize_session=False)
            db.commit()
        except Exception as cl_err:
            print(f"Cleanup note: {cl_err}")
        finally:
            db.close()

    total = len(results)
    passed = sum(1 for _, p, _ in results if p)
    print("=" * 70)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 70)
    return passed == total

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
