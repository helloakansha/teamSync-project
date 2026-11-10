import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
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
from database import SessionLocal, engine, Base
import models
from main import app, hash_password, create_access_token

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print("TEAMSYNC — PHASE 5 (STEPS 5B.2 & 5C) AUTOMATED VERIFICATION SUITE")
    print("Background Sync, Sync Status & Manual Retry")
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
        # Create test users
        suffix = int(datetime.now().timestamp() * 1000)
        u1 = models.User(
            name=f"Creator User {suffix}",
            email=f"creator_{suffix}@example.com",
            password_hash=hash_password("Pass123!")
        )
        u2 = models.User(
            name=f"Member User {suffix}",
            email=f"member_{suffix}@example.com",
            password_hash=hash_password("Pass123!")
        )
        u3 = models.User(
            name=f"Disconnected User {suffix}",
            email=f"disconn_{suffix}@example.com",
            password_hash=hash_password("Pass123!")
        )
        db.add_all([u1, u2, u3])
        db.commit()
        db.refresh(u1)
        db.refresh(u2)
        db.refresh(u3)
        test_user_ids.extend([u1.id, u2.id, u3.id])

        # Attach mock Google credentials for u1 and u2
        cred1 = models.GoogleCredential(
            user_id=u1.id,
            access_token="fake_token_1",
            refresh_token="fake_refresh_1",
            token_expiry=datetime.now(timezone.utc) + timedelta(days=7),
            scopes="https://www.googleapis.com/auth/calendar.events"
        )
        cred2 = models.GoogleCredential(
            user_id=u2.id,
            access_token="fake_token_2",
            refresh_token="fake_refresh_2",
            token_expiry=datetime.now(timezone.utc) + timedelta(days=7),
            scopes="https://www.googleapis.com/auth/calendar.events"
        )
        db.add_all([cred1, cred2])
        db.commit()

        # Create test group with u1 as owner and u2 as member
        group = models.Group(
            name=f"Sync Test Group {suffix}",
            description="Testing background sync and retry",
            subject="Integration"
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        test_group_ids.append(group.id)

        gm1 = models.GroupMember(group_id=group.id, user_id=u1.id, role="owner")
        gm2 = models.GroupMember(group_id=group.id, user_id=u2.id, role="member")
        db.add_all([gm1, gm2])
        db.commit()

        token1 = create_access_token(u1.id)
        token2 = create_access_token(u2.id)
        token3 = create_access_token(u3.id)

        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        headers3 = {"Authorization": f"Bearer {token3}"}

        now = datetime.now(timezone.utc)

        # ----------------------------------------------------
        # TEST 1: Session creation with Google connection schedules background sync
        # ----------------------------------------------------
        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.create_google_calendar_event", return_value="g_event_1001") as mock_create:
                res1 = client.post(
                    f"/api/groups/{group.id}/sessions",
                    headers=headers1,
                    json={
                        "title": "Background Sync Session 1",
                        "description": "Testing immediate return and bg sync",
                        "start_time": (now + timedelta(days=1)).isoformat(),
                        "end_time": (now + timedelta(days=1, hours=2)).isoformat()
                    }
                )
                data1 = res1.json()
                s1_id = data1.get("session", {}).get("id")
                test_session_ids.append(s1_id)

                # Check TestClient executed background task
                db_s1 = db.query(models.StudySession).filter_by(id=s1_id).first()
                t1_pass = (
                    res1.status_code == 200 and
                    data1.get("success") is True and
                    data1.get("session", {}).get("calendar_sync_status") in ("pending", "synced") and
                    db_s1.calendar_sync_status == "synced" and
                    db_s1.google_event_id == "g_event_1001" and
                    db_s1.calendar_synced_at is not None
                )
                record("1. Session creation schedules background task & updates DB to 'synced'", t1_pass, f"DB Status: {db_s1.calendar_sync_status}, Event ID: {db_s1.google_event_id}")

        # ----------------------------------------------------
        # TEST 2: Session creation with disconnected user sets 'not_connected'
        # ----------------------------------------------------
        # Add u3 to group
        gm3 = models.GroupMember(group_id=group.id, user_id=u3.id, role="member")
        db.add(gm3)
        db.commit()

        res2 = client.post(
            f"/api/groups/{group.id}/sessions",
            headers=headers3,
            json={
                "title": "Disconnected User Session",
                "start_time": (now + timedelta(days=2)).isoformat(),
                "end_time": (now + timedelta(days=2, hours=1)).isoformat()
            }
        )
        data2 = res2.json()
        s2_id = data2.get("session", {}).get("id")
        test_session_ids.append(s2_id)
        db_s2 = db.query(models.StudySession).filter_by(id=s2_id).first()

        t2_pass = (
            res2.status_code == 200 and
            data2.get("session", {}).get("calendar_sync_status") == "not_connected" and
            db_s2.calendar_sync_status == "not_connected" and
            db_s2.google_event_id is None
        )
        record("2. Session creation by disconnected user sets status to 'not_connected'", t2_pass, f"DB Status: {db_s2.calendar_sync_status}")

        # ----------------------------------------------------
        # TEST 3: Google API failure during background creation records 'failed' & error message
        # ----------------------------------------------------
        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.create_google_calendar_event", return_value=None):
                res3 = client.post(
                    f"/api/groups/{group.id}/sessions",
                    headers=headers1,
                    json={
                        "title": "Failing Sync Session",
                        "start_time": (now + timedelta(days=3)).isoformat(),
                        "end_time": (now + timedelta(days=3, hours=1)).isoformat()
                    }
                )
                data3 = res3.json()
                s3_id = data3.get("session", {}).get("id")
                test_session_ids.append(s3_id)
                db.expire_all()
                db_s3 = db.query(models.StudySession).filter_by(id=s3_id).first()

                t3_pass = (
                    res3.status_code == 200 and
                    db_s3 is not None and
                    db_s3.calendar_sync_status == "failed" and
                    db_s3.calendar_sync_error is not None and
                    len(db_s3.calendar_sync_error) > 0
                )
                record("3. Background sync failure sets status to 'failed' and records error message", t3_pass, f"DB Status: {db_s3.calendar_sync_status}, Error: {db_s3.calendar_sync_error}")

        # ----------------------------------------------------
        # TEST 4: GET sync-status endpoint returns accurate synchronization state
        # ----------------------------------------------------
        res4 = client.get(
            f"/api/groups/{group.id}/sessions/{s3_id}/sync-status",
            headers=headers1
        )
        data4 = res4.json()
        t4_pass = (
            res4.status_code == 200 and
            data4.get("success") is True and
            data4.get("session_id") == s3_id and
            data4.get("calendar_sync_status") == "failed" and
            data4.get("calendar_sync_error") is not None
        )
        record("4. GET /api/groups/{id}/sessions/{id}/sync-status reports current status & error", t4_pass, f"Reported: {data4}")

        # ----------------------------------------------------
        # TEST 5: Manual retry endpoint (POST .../sync) queues background sync and succeeds
        # ----------------------------------------------------
        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.create_google_calendar_event", return_value="g_event_retry_success"):
                res5 = client.post(
                    f"/api/groups/{group.id}/sessions/{s3_id}/sync",
                    headers=headers1
                )
                data5 = res5.json()
                db.expire_all()
                db_s3_retried = db.query(models.StudySession).filter_by(id=s3_id).first()

                t5_pass = (
                    res5.status_code == 200 and
                    data5.get("success") is True and
                    db_s3_retried.calendar_sync_status == "synced" and
                    db_s3_retried.google_event_id == "g_event_retry_success" and
                    db_s3_retried.calendar_sync_error is None
                )
                record("5. Manual retry recovers failed session and updates status to 'synced'", t5_pass, f"New DB Status: {db_s3_retried.calendar_sync_status}, Event ID: {db_s3_retried.google_event_id}")

        # ----------------------------------------------------
        # TEST 6: Manual retry on already synced session returns cleanly without duplicate
        # ----------------------------------------------------
        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.create_google_calendar_event") as mock_dup:
                res6 = client.post(
                    f"/api/groups/{group.id}/sessions/{s3_id}/sync",
                    headers=headers1
                )
                data6 = res6.json()
                t6_pass = (
                    res6.status_code == 200 and
                    "already synchronized" in data6.get("message", "").lower() and
                    mock_dup.call_count == 0
                )
                record("6. Manual retry on already synced session prevents duplicate event creation", t6_pass, f"Message: {data6.get('message')}")

        # ----------------------------------------------------
        # TEST 7: Manual retry authorization: non-owner / non-creator member is forbidden (403)
        # ----------------------------------------------------
        # u3 is a member, but didn't create s3 (u1 created s3, u1 is owner)
        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            res7 = client.post(
                f"/api/groups/{group.id}/sessions/{s3_id}/sync",
                headers=headers3
            )
            t7_pass = (
                res7.status_code == 403 and
                "permission denied" in res7.json().get("detail", "").lower()
            )
            record("7. Unauthorized member cannot retry session sync (HTTP 403)", t7_pass, f"Status: {res7.status_code}")

        # ----------------------------------------------------
        # TEST 8: Session cancellation tracks Google Calendar deletion in calendar_sync_logs
        # ----------------------------------------------------
        # Cancel session s1 (which has google_event_id="g_event_1001")
        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.delete_google_calendar_event", return_value=True) as mock_del:
                res8 = client.delete(
                    f"/api/groups/{group.id}/sessions/{s1_id}",
                    headers=headers1
                )
                data8 = res8.json()

                # Session should be deleted from PostgreSQL
                db.expire_all()
                deleted_session = db.query(models.StudySession).filter_by(id=s1_id).first()

                # CalendarSyncLog should have recorded deletion
                log_entry = db.query(models.CalendarSyncLog).filter_by(
                    google_event_id="g_event_1001",
                    operation="delete"
                ).first()

                t8_pass = (
                    res8.status_code == 200 and
                    data8.get("success") is True and
                    deleted_session is None and
                    log_entry is not None and
                    log_entry.status == "success"
                )
                record("8. Session cancellation executes background deletion & logs outcome", t8_pass, f"Log status: {log_entry.status if log_entry else None}, Operation: {log_entry.operation if log_entry else None}")

        # ----------------------------------------------------
        # TEST 9: Session edit schedules background Google update and updates session
        # ----------------------------------------------------
        with patch("main.get_valid_google_credentials", return_value=MagicMock()):
            with patch("main.update_google_calendar_event", return_value=True) as mock_upd:
                res9 = client.put(
                    f"/api/groups/{group.id}/sessions/{s3_id}",
                    headers=headers1,
                    json={
                        "title": "Updated Background Session Title",
                        "description": "Updated description",
                        "start_time": (now + timedelta(days=4)).isoformat(),
                        "end_time": (now + timedelta(days=4, hours=2)).isoformat()
                    }
                )
                data9 = res9.json()
                db.expire_all()
                db_s3_upd = db.query(models.StudySession).filter_by(id=s3_id).first()

                t9_pass = (
                    res9.status_code == 200 and
                    data9.get("success") is True and
                    db_s3_upd.title == "Updated Background Session Title" and
                    mock_upd.called and
                    db_s3_upd.calendar_sync_status == "synced"
                )
                record("9. Session editing schedules background update & maintains 'synced' status", t9_pass, f"Title in DB: {db_s3_upd.title}, Status: {db_s3_upd.calendar_sync_status}")

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
