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
from main import app, create_access_token
from database import SessionLocal
import models
from datetime import datetime, timezone, timedelta

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
    print("STARTING TEST SUITE: UPCOMING SESSION FILTERING")
    print("==================================================")

    # 1. Setup authenticated user and group
    user = db.query(models.User).filter(models.User.id == 3).first() or db.query(models.User).first()
    assert user is not None, "Test user not found"

    # Find a group the user belongs to
    membership = db.query(models.GroupMember).filter(models.GroupMember.user_id == user.id).first()
    assert membership is not None, "Test user has no group membership"
    group = db.query(models.Group).filter(models.Group.id == membership.group_id).first()
    assert group is not None, "Test group not found"

    token = create_access_token(user.id)
    auth_headers = {"Authorization": f"Bearer {token}"}

    print(f"User: {user.name} (id={user.id}) | Group: {group.name} (id={group.id})")

    # Baseline counts before creating test sessions
    res_base_group = client.get(f"/api/groups/{group.id}", headers=auth_headers)
    assert res_base_group.status_code == 200
    base_group_sessions = res_base_group.json()["group"]["session_count"]

    res_base_dash = client.get("/api/sessions", headers=auth_headers)
    assert res_base_dash.status_code == 200
    base_dash_sessions = res_base_dash.json()["count"]

    now = datetime.now(timezone.utc)

    # -----------------------------------------------------------------
    # A. Create a FUTURE session: start in +2h, end in +3h
    # -----------------------------------------------------------------
    future_session = models.StudySession(
        group_id=group.id,
        created_by=user.id,
        title="[TEST] Future Study Session",
        description="Starts in 2h, ends in 3h",
        start_time=now + timedelta(hours=2),
        end_time=now + timedelta(hours=3)
    )
    db.add(future_session)
    db.commit()
    db.refresh(future_session)
    created_session_ids.append(future_session.id)

    # -----------------------------------------------------------------
    # B. Create an ONGOING session: started 30m ago, ends in 30m
    # -----------------------------------------------------------------
    ongoing_session = models.StudySession(
        group_id=group.id,
        created_by=user.id,
        title="[TEST] Ongoing Study Session",
        description="Started 30m ago, ends in 30m",
        start_time=now - timedelta(minutes=30),
        end_time=now + timedelta(minutes=30)
    )
    db.add(ongoing_session)
    db.commit()
    db.refresh(ongoing_session)
    created_session_ids.append(ongoing_session.id)

    # -----------------------------------------------------------------
    # C. Create a RECENTLY ENDED session: ended 20m ago (would have passed now - 1h)
    # -----------------------------------------------------------------
    ended_session = models.StudySession(
        group_id=group.id,
        created_by=user.id,
        title="[TEST] Recently Ended Session",
        description="Started 1h20m ago, ended 20m ago",
        start_time=now - timedelta(hours=1, minutes=20),
        end_time=now - timedelta(minutes=20)
    )
    db.add(ended_session)
    db.commit()
    db.refresh(ended_session)
    created_session_ids.append(ended_session.id)

    # -----------------------------------------------------------------
    # TEST 1: Future Session is included in all upcoming views
    # -----------------------------------------------------------------
    res_dash = client.get("/api/sessions", headers=auth_headers)
    dash_ids = [s["id"] for s in res_dash.json().get("sessions", [])]
    test1_pass = (future_session.id in dash_ids)
    record_result("1. Future session included in GET /api/sessions", test1_pass, f"Session {future_session.id} found in dashboard sessions")

    # -----------------------------------------------------------------
    # TEST 2: Ongoing Session is included in all upcoming views
    # -----------------------------------------------------------------
    test2_pass = (ongoing_session.id in dash_ids)
    record_result("2. Ongoing session included in GET /api/sessions", test2_pass, f"Ongoing session {ongoing_session.id} (ends in +30m) retained")

    # -----------------------------------------------------------------
    # TEST 3: Recently Ended Session is EXCLUDED from GET /api/sessions
    # -----------------------------------------------------------------
    test3_pass = (ended_session.id not in dash_ids)
    record_result("3. Recently ended session EXCLUDED from GET /api/sessions", test3_pass, f"Session {ended_session.id} (ended 20m ago) correctly excluded")

    # -----------------------------------------------------------------
    # TEST 4: Group Details (/api/groups/{id}) filtering consistency
    # -----------------------------------------------------------------
    res_group = client.get(f"/api/groups/{group.id}", headers=auth_headers)
    group_data = res_group.json()["group"]
    group_session_ids = [s["id"] for s in group_data.get("sessions", [])]

    test4_pass = (
        (future_session.id in group_session_ids) and
        (ongoing_session.id in group_session_ids) and
        (ended_session.id not in group_session_ids) and
        (group_data["session_count"] == len(group_session_ids)) and
        (group_data["sessions_count"] == len(group_session_ids))
    )
    record_result(
        "4. Group Details upcoming sessions and badge count consistency",
        test4_pass,
        f"Group session_count={group_data['session_count']}; future & ongoing present, ended excluded"
    )

    # -----------------------------------------------------------------
    # TEST 5: Group Cards (/api/groups) session_count filtering consistency
    # -----------------------------------------------------------------
    res_groups = client.get("/api/groups", headers=auth_headers)
    groups_list = res_groups.json().get("groups", [])
    matching_group_card = next((g for g in groups_list if g["id"] == group.id), None)

    test5_pass = (
        matching_group_card is not None and
        matching_group_card["session_count"] == group_data["session_count"] and
        matching_group_card["sessions_count"] == group_data["sessions_count"]
    )
    record_result(
        "5. Group Cards (/api/groups) session_count matches Group Details",
        test5_pass,
        f"Card count={matching_group_card['session_count'] if matching_group_card else None} matches Details count={group_data['session_count']}"
    )

    # -----------------------------------------------------------------
    # TEST 6: Chronological ordering (start_time ASC)
    # -----------------------------------------------------------------
    # Ongoing started 30m ago, future starts in 2h -> Ongoing MUST precede Future
    ongoing_idx = group_session_ids.index(ongoing_session.id)
    future_idx = group_session_ids.index(future_session.id)
    test6_pass = (ongoing_idx < future_idx)
    record_result(
        "6. Chronological ordering preserved",
        test6_pass,
        f"Ongoing session (idx {ongoing_idx}) precedes future session (idx {future_idx})"
    )

    # -----------------------------------------------------------------
    # TEST 7: Serialization tags ("Past" vs "Upcoming")
    # -----------------------------------------------------------------
    from main import serialize_session
    future_s = serialize_session(future_session)
    ongoing_s = serialize_session(ongoing_session)
    ended_s = serialize_session(ended_session)

    test7_pass = (
        future_s["tag"] == "Upcoming" and
        ongoing_s["tag"] == "Upcoming" and
        ended_s["tag"] == "Past"
    )
    record_result(
        "7. Dynamic session serialization tagging",
        test7_pass,
        f"Future='{future_s['tag']}', Ongoing='{ongoing_s['tag']}', Ended='{ended_s['tag']}'"
    )

    # -----------------------------------------------------------------
    # TEST 8: GET /api/groups/{id}/sessions optional upcoming_only filter
    # -----------------------------------------------------------------
    res_all_sessions = client.get(f"/api/groups/{group.id}/sessions", headers=auth_headers)
    all_ids = [s["id"] for s in res_all_sessions.json().get("sessions", [])]

    res_up_sessions = client.get(f"/api/groups/{group.id}/sessions?upcoming_only=true", headers=auth_headers)
    up_ids = [s["id"] for s in res_up_sessions.json().get("sessions", [])]

    test8_pass = (
        (ended_session.id in all_ids) and
        (ended_session.id not in up_ids) and
        (future_session.id in up_ids) and
        (ongoing_session.id in up_ids)
    )
    record_result(
        "8. GET /api/groups/{id}/sessions parameter check",
        test8_pass,
        f"Unfiltered contains ended={ended_session.id in all_ids}; upcoming_only excludes ended={ended_session.id not in up_ids}"
    )

    # -----------------------------------------------------------------
    # TEST 9: Timezone-aware comparisons with UTC offsets
    # -----------------------------------------------------------------
    # Ensure querying with explicit timezone offsets doesn't raise offset-naive/aware errors
    tz_aware_now = datetime.now(timezone(timedelta(hours=5, minutes=30))) # IST offset
    try:
        ist_sessions = db.query(models.StudySession).filter(
            models.StudySession.group_id == group.id,
            models.StudySession.end_time >= tz_aware_now
        ).all()
        test9_pass = isinstance(ist_sessions, list)
        record_result("9. Timezone-aware PostgreSQL comparison", test9_pass, f"Evaluated with IST datetime object without error")
    except Exception as e:
        record_result("9. Timezone-aware PostgreSQL comparison", False, str(e))

    # -----------------------------------------------------------------
    # TEST 10: Cancellation remaining_sessions_count uses upcoming filter
    # -----------------------------------------------------------------
    # Delete the future session via endpoint and check remaining_sessions_count
    res_del = client.delete(f"/api/groups/{group.id}/sessions/{future_session.id}", headers=auth_headers)
    del_data = res_del.json()
    rem_count = del_data.get("remaining_sessions_count")
    # remaining count should equal group_data['session_count'] - 1
    test10_pass = (res_del.status_code == 200 and rem_count == group_data["session_count"] - 1)
    record_result(
        "10. DELETE endpoint returns accurate remaining upcoming sessions count",
        test10_pass,
        f"remaining_sessions_count={rem_count} matches expected {group_data['session_count'] - 1}"
    )

finally:
    # Cleanup all created test sessions
    print("\nCleaning up test sessions...")
    for sid in created_session_ids:
        try:
            s_to_del = db.query(models.StudySession).filter(models.StudySession.id == sid).first()
            if s_to_del:
                db.delete(s_to_del)
                db.commit()
        except Exception:
            db.rollback()
    db.close()
    print(f"Cleaned up {len(created_session_ids)} test records.")

print("==================================================")
print(f"RESULTS SUMMARY: {len(test_results['passed'])} PASSED, {len(test_results['failed'])} FAILED")
print("==================================================")

if test_results["failed"]:
    sys.exit(1)
else:
    sys.exit(0)

