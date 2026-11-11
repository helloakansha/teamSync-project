import sys
import os
import uuid
import time
import threading
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

try:
    from database import SessionLocal, engine
    import models
    from main import (
        session_calendar_mutex,
        bg_sync_create_calendar_event,
        bg_sync_update_calendar_event,
        bg_sync_delete_calendar_event,
        reconcile_stale_external_operation,
        hash_password,
        encrypt_google_token
    )
except ImportError:
    from backend.database import SessionLocal, engine
    import backend.models as models
    from backend.main import (
        session_calendar_mutex,
        bg_sync_create_calendar_event,
        bg_sync_update_calendar_event,
        bg_sync_delete_calendar_event,
        reconcile_stale_external_operation,
        hash_password,
        encrypt_google_token
    )

def run_advisory_lock_tests():
    print("=" * 75)
    print("TEAMSYNC — PHASE 5 PER-SESSION ADVISORY LOCKING CONCURRENCY TESTS")
    print("Tests A through F: Google Calendar Mutation Serialization")
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
        user = models.User(
            name=f"LockUser_{suffix}",
            email=f"lock_{suffix}@example.com",
            password_hash=hash_password("Pass123!")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        test_user_ids.append(user.id)

        cred = models.GoogleCredential(
            user_id=user.id,
            access_token=encrypt_google_token("fake_lock_access"),
            refresh_token=encrypt_google_token("fake_lock_refresh"),
            token_expiry=datetime.now(timezone.utc) + timedelta(days=7),
            scopes="https://www.googleapis.com/auth/calendar.events.owned"
        )
        db.add(cred)
        db.commit()

        group = models.Group(
            name=f"LockGroup_{suffix}",
            description="Testing Advisory Lock Concurrency",
            subject="Concurrency"
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        test_group_ids.append(group.id)

        gm = models.GroupMember(group_id=group.id, user_id=user.id, role="owner")
        db.add(gm)
        db.commit()

        # =========================================================================
        # TEST A: Reconciliation versus a newer edit
        # =========================================================================
        now_utc = datetime.now(timezone.utc)
        sess_a = models.StudySession(
            group_id=group.id,
            created_by=user.id,
            calendar_owner_id=user.id,
            title="Session A Original Title",
            start_time=now_utc + timedelta(days=1),
            end_time=now_utc + timedelta(days=1, hours=1),
            calendar_sync_status="synced",
            google_event_id="gevent_test_a",
            calendar_id="primary"
        )
        db.add(sess_a)
        db.commit()
        db.refresh(sess_a)
        test_session_ids.append(sess_a.id)

        google_events_store = {
            "gevent_test_a": {"summary": "[TeamSync] Session A Original Title"}
        }

        a_external_started = threading.Event()
        a_can_finish = threading.Event()
        execution_order = []

        def mock_update_a(creds, event_id, title, description, start_time, end_time, group_name):
            thread_name = threading.current_thread().name
            execution_order.append((thread_name, "enter", time.time(), title))
            if thread_name == "ReconcileWorkerA":
                a_external_started.set()
                a_can_finish.wait(timeout=5.0)
            google_events_store[event_id] = {"summary": f"[TeamSync] {title}"}
            execution_order.append((thread_name, "exit", time.time(), title))
            return True

        with patch("main.get_valid_google_credentials", return_value=MagicMock()), \
             patch("main.update_google_calendar_event", side_effect=mock_update_a):
            # Thread 1: Reconciliation A
            t1 = threading.Thread(
                target=reconcile_stale_external_operation,
                args=(sess_a.id, user.id),
                name="ReconcileWorkerA"
            )
            t1.start()

            # Wait until ReconcileWorkerA is inside its locked critical section
            a_external_started.wait(timeout=3.0)

            # In main thread: user edits session to "Session A Newer Edit Title"
            edit_db = SessionLocal()
            edit_db.query(models.StudySession).filter_by(id=sess_a.id).update({
                "title": "Session A Newer Edit Title",
                "calendar_sync_status": "pending",
                "calendar_sync_attempt_id": None
            })
            edit_db.commit()
            edit_db.close()

            # Thread 2: Worker B claims update
            b_finished = threading.Event()
            def run_worker_b():
                bg_sync_update_calendar_event(sess_a.id, user.id)
                b_finished.set()

            t2 = threading.Thread(target=run_worker_b, name="UpdateWorkerB")
            t2.start()

            # Let Worker B wait on the advisory lock for 0.1s
            time.sleep(0.1)

            # Now allow ReconcileWorkerA to finish
            a_can_finish.set()
            t1.join(timeout=3.0)
            t2.join(timeout=3.0)

        # Check execution order: Worker B must have entered AFTER ReconcileWorkerA exited
        a_exits = [item for item in execution_order if item[0] == "ReconcileWorkerA" and item[1] == "exit"]
        b_enters = [item for item in execution_order if item[0] == "UpdateWorkerB" and item[1] == "enter"]
        
        non_overlapping = False
        if a_exits and b_enters:
            non_overlapping = (b_enters[0][2] >= a_exits[0][2])

        db.expire_all()
        sess_a_final = db.query(models.StudySession).filter_by(id=sess_a.id).first()
        final_google_title = google_events_store.get("gevent_test_a", {}).get("summary")

        test_a_pass = (
            non_overlapping and
            sess_a_final.calendar_sync_status == "synced" and
            final_google_title == "[TeamSync] Session A Newer Edit Title"
        )
        record(
            "Test A: Reconciliation vs newer edit serializes; Worker B updates with latest details",
            test_a_pass,
            f"Non-overlapping: {non_overlapping}, Final Google Title: {final_google_title}"
        )

        # =========================================================================
        # TEST B: Two simultaneous updates on the same session
        # =========================================================================
        sess_b = models.StudySession(
            group_id=group.id,
            created_by=user.id,
            calendar_owner_id=user.id,
            title="Session B Initial",
            start_time=now_utc + timedelta(days=2),
            end_time=now_utc + timedelta(days=2, hours=1),
            calendar_sync_status="pending",
            google_event_id="gevent_test_b",
            calendar_id="primary"
        )
        db.add(sess_b)
        db.commit()
        db.refresh(sess_b)
        test_session_ids.append(sess_b.id)

        concurrent_count = 0
        max_concurrent_b = 0
        counter_lock = threading.Lock()

        def mock_update_b(creds, event_id, title, description, start_time, end_time, group_name):
            nonlocal concurrent_count, max_concurrent_b
            with counter_lock:
                concurrent_count += 1
                if concurrent_count > max_concurrent_b:
                    max_concurrent_b = concurrent_count
            time.sleep(0.15)
            with counter_lock:
                concurrent_count -= 1
            return True

        with patch("main.get_valid_google_credentials", return_value=MagicMock()), \
             patch("main.update_google_calendar_event", side_effect=mock_update_b):
            # Launch two concurrent workers for the same session
            t_b1 = threading.Thread(target=bg_sync_update_calendar_event, args=(sess_b.id, user.id))
            t_b2 = threading.Thread(target=bg_sync_update_calendar_event, args=(sess_b.id, user.id))
            t_b1.start()
            t_b2.start()
            t_b1.join(timeout=5.0)
            t_b2.join(timeout=5.0)

        db.expire_all()
        sess_b_final = db.query(models.StudySession).filter_by(id=sess_b.id).first()
        test_b_pass = (max_concurrent_b == 1 and sess_b_final.calendar_sync_status == "synced")
        record(
            "Test B: Two simultaneous updates on same session serialize (max concurrent Google calls = 1)",
            test_b_pass,
            f"Max concurrent Google calls: {max_concurrent_b}, Final status: {sess_b_final.calendar_sync_status}"
        )

        # =========================================================================
        # TEST C: Independent sessions execute concurrently (no global lock)
        # =========================================================================
        sess_c1 = models.StudySession(
            group_id=group.id,
            created_by=user.id,
            calendar_owner_id=user.id,
            title="Session C1",
            start_time=now_utc + timedelta(days=3),
            end_time=now_utc + timedelta(days=3, hours=1),
            calendar_sync_status="pending",
            google_event_id="gevent_test_c1",
            calendar_id="primary"
        )
        sess_c2 = models.StudySession(
            group_id=group.id,
            created_by=user.id,
            calendar_owner_id=user.id,
            title="Session C2",
            start_time=now_utc + timedelta(days=4),
            end_time=now_utc + timedelta(days=4, hours=1),
            calendar_sync_status="pending",
            google_event_id="gevent_test_c2",
            calendar_id="primary"
        )
        db.add_all([sess_c1, sess_c2])
        db.commit()
        db.refresh(sess_c1)
        db.refresh(sess_c2)
        test_session_ids.extend([sess_c1.id, sess_c2.id])

        concurrent_count_c = 0
        max_concurrent_c = 0
        barrier_c = threading.Barrier(2)

        def mock_update_c(creds, event_id, title, description, start_time, end_time, group_name):
            nonlocal concurrent_count_c, max_concurrent_c
            with counter_lock:
                concurrent_count_c += 1
                if concurrent_count_c > max_concurrent_c:
                    max_concurrent_c = concurrent_count_c
            # Both threads reach this barrier simultaneously to prove concurrency
            try:
                barrier_c.wait(timeout=3.0)
            except threading.BrokenBarrierError:
                pass
            time.sleep(0.05)
            with counter_lock:
                concurrent_count_c -= 1
            return True

        with patch("main.get_valid_google_credentials", return_value=MagicMock()), \
             patch("main.update_google_calendar_event", side_effect=mock_update_c):
            t_c1 = threading.Thread(target=bg_sync_update_calendar_event, args=(sess_c1.id, user.id))
            t_c2 = threading.Thread(target=bg_sync_update_calendar_event, args=(sess_c2.id, user.id))
            t_c1.start()
            t_c2.start()
            t_c1.join(timeout=5.0)
            t_c2.join(timeout=5.0)

        test_c_pass = (max_concurrent_c == 2)
        record(
            "Test C: Independent sessions execute concurrently without blocking each other",
            test_c_pass,
            f"Max concurrent Google calls across distinct sessions: {max_concurrent_c}"
        )

        # =========================================================================
        # TEST D: Create versus Delete serialization on same session
        # =========================================================================
        sess_d = models.StudySession(
            group_id=group.id,
            created_by=user.id,
            calendar_owner_id=user.id,
            title="Session D Create-Delete Test",
            start_time=now_utc + timedelta(days=5),
            end_time=now_utc + timedelta(days=5, hours=1),
            calendar_sync_status="pending"
        )
        db.add(sess_d)
        db.commit()
        db.refresh(sess_d)
        test_session_ids.append(sess_d.id)

        del_log = models.CalendarSyncLog(
            user_id=user.id,
            session_id=sess_d.id,
            calendar_owner_id=user.id,
            google_event_id="gevent_test_d",
            operation="delete",
            status="pending"
        )
        db.add(del_log)
        db.commit()
        db.refresh(del_log)

        create_started_d = threading.Event()
        create_finish_d = threading.Event()
        order_d = []

        def mock_create_d(creds, title, description, start_time, end_time, group_name, event_id, session_id):
            order_d.append(("create", "enter", time.time()))
            create_started_d.set()
            create_finish_d.wait(timeout=3.0)
            order_d.append(("create", "exit", time.time()))
            return "gevent_test_d"

        def mock_delete_d(creds, event_id):
            order_d.append(("delete", "enter", time.time()))
            time.sleep(0.05)
            order_d.append(("delete", "exit", time.time()))
            return True

        with patch("main.get_valid_google_credentials", return_value=MagicMock()), \
             patch("main.create_google_calendar_event", side_effect=mock_create_d), \
             patch("main.delete_google_calendar_event", side_effect=mock_delete_d):

            t_d_create = threading.Thread(target=bg_sync_create_calendar_event, args=(sess_d.id, user.id))
            t_d_delete = threading.Thread(
                target=bg_sync_delete_calendar_event,
                args=(del_log.id, "gevent_test_d", user.id, "Session D", sess_d.id)
            )

            t_d_create.start()
            create_started_d.wait(timeout=3.0)

            # Start delete worker while create worker is inside the critical section
            t_d_delete.start()
            time.sleep(0.1)

            create_finish_d.set()
            t_d_create.join(timeout=5.0)
            t_d_delete.join(timeout=5.0)

        create_exit_time = next((t for op, action, t in order_d if op == "create" and action == "exit"), 0)
        delete_enter_time = next((t for op, action, t in order_d if op == "delete" and action == "enter"), 0)
        d_serialized = (delete_enter_time >= create_exit_time)

        db.expire_all()
        del_log_final = db.query(models.CalendarSyncLog).filter_by(id=del_log.id).first()
        test_d_pass = (d_serialized and del_log_final.status == "success")
        record(
            "Test D: Create vs Delete on same session serializes; Delete waits until Create finishes",
            test_d_pass,
            f"Serialized: {d_serialized}, Delete log status: {del_log_final.status}"
        )

        # =========================================================================
        # TEST E: Claim superseded while waiting for advisory lock
        # =========================================================================
        sess_e = models.StudySession(
            group_id=group.id,
            created_by=user.id,
            calendar_owner_id=user.id,
            title="Session E Claim Test",
            start_time=now_utc + timedelta(days=6),
            end_time=now_utc + timedelta(days=6, hours=1),
            calendar_sync_status="pending",
            google_event_id="gevent_test_e",
            calendar_id="primary"
        )
        db.add(sess_e)
        db.commit()
        db.refresh(sess_e)
        test_session_ids.append(sess_e.id)

        holder_lock_started = threading.Event()
        can_release_holder = threading.Event()

        def lock_holder():
            with session_calendar_mutex(sess_e.id) as acquired:
                if acquired:
                    holder_lock_started.set()
                    can_release_holder.wait(timeout=3.0)

        t_holder = threading.Thread(target=lock_holder)
        t_holder.start()
        holder_lock_started.wait(timeout=3.0)

        google_called_e = False
        def mock_update_e(*args, **kwargs):
            nonlocal google_called_e
            google_called_e = True
            return True

        with patch("main.get_valid_google_credentials", return_value=MagicMock()), \
             patch("main.update_google_calendar_event", side_effect=mock_update_e):
            worker_b_done = threading.Event()

            # Worker B thread runs bg_sync_update_calendar_event
            def run_worker_b_superseded():
                bg_sync_update_calendar_event(sess_e.id, user.id)
                worker_b_done.set()

            t_worker_b = threading.Thread(target=run_worker_b_superseded)
            t_worker_b.start()

            # Wait a moment for Worker B to claim session in DB and start waiting for advisory lock
            time.sleep(0.1)

            # Invalidate Worker B's claim by simulating a user edit (which clears or replaces attempt_id)
            edit_db = SessionLocal()
            edit_db.query(models.StudySession).filter_by(id=sess_e.id).update({
                "title": "Session E User Edited",
                "calendar_sync_attempt_id": "superseding_token_xyz"
            })
            edit_db.commit()
            edit_db.close()

            # Release the lock so Worker B acquires it
            can_release_holder.set()
            t_holder.join(timeout=3.0)
            t_worker_b.join(timeout=3.0)

        test_e_pass = (not google_called_e)
        record(
            "Test E: Worker B detects claim superseded after acquiring lock and aborts without mutation",
            test_e_pass,
            f"Google API called by Worker B: {google_called_e}"
        )

        # =========================================================================
        # TEST F: Lock cleanup and recovery on Google API or DB failure
        # =========================================================================
        sess_f = models.StudySession(
            group_id=group.id,
            created_by=user.id,
            calendar_owner_id=user.id,
            title="Session F Error Recovery Test",
            start_time=now_utc + timedelta(days=7),
            end_time=now_utc + timedelta(days=7, hours=1),
            calendar_sync_status="pending",
            google_event_id="gevent_test_f",
            calendar_id="primary"
        )
        db.add(sess_f)
        db.commit()
        db.refresh(sess_f)
        test_session_ids.append(sess_f.id)

        # Worker 1 encounters an exception inside the lock
        def mock_error_f(*args, **kwargs):
            raise RuntimeError("Simulated network timeout/socket error")

        with patch("main.get_valid_google_credentials", return_value=MagicMock()), \
             patch("main.update_google_calendar_event", side_effect=mock_error_f):
            bg_sync_update_calendar_event(sess_f.id, user.id)

        db.expire_all()
        sess_f_after_err = db.query(models.StudySession).filter_by(id=sess_f.id).first()
        status_after_worker1 = sess_f_after_err.calendar_sync_status

        # Worker 2 runs immediately on the same session; lock must be free immediately
        worker2_acquired_time = None
        start_time_w2 = time.time()
        with patch("main.get_valid_google_credentials", return_value=MagicMock()), \
             patch("main.update_google_calendar_event", return_value=True):
            bg_sync_update_calendar_event(sess_f.id, user.id)
            worker2_acquired_time = time.time() - start_time_w2

        db.expire_all()
        sess_f_final = db.query(models.StudySession).filter_by(id=sess_f.id).first()

        test_f_pass = (
            status_after_worker1 == "failed" and
            worker2_acquired_time is not None and
            worker2_acquired_time < 1.0 and
            sess_f_final.calendar_sync_status == "synced"
        )
        record(
            "Test F: Lock is cleanly released on error; subsequent worker acquires immediately (<1s)",
            test_f_pass,
            f"status_after_worker1={status_after_worker1}, duration={worker2_acquired_time:.3f}s, final_status={sess_f_final.calendar_sync_status}"
        )

    finally:
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
    print(f"CONCURRENCY SUMMARY: {passed_count}/{total} TESTS PASSED")
    print("=" * 75)
    if passed_count < total:
        sys.exit(1)

if __name__ == "__main__":
    run_advisory_lock_tests()
