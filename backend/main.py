from contextlib import contextmanager

from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks

from fastapi.responses import RedirectResponse

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from sqlalchemy.orm import Session

from sqlalchemy import text

from datetime import datetime, timezone, timedelta

from typing import Optional, List

from urllib.parse import urlencode, quote_plus

import hashlib

import uuid



import secrets



import string



import threading



import time



import os

from pathlib import Path

from dotenv import load_dotenv

from jose import jwt, JWTError

from cryptography.fernet import Fernet, InvalidToken



import socket

import httplib2

import google_auth_httplib2

from google_auth_oauthlib.flow import Flow

from google.oauth2.credentials import Credentials

from google.auth.transport.requests import Request as GoogleAuthRequest

from googleapiclient.discovery import build

from googleapiclient.errors import HttpError



from database import Base, engine, SessionLocal

import models

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired





env_path = Path(__file__).resolve().parent / ".env"

load_dotenv(dotenv_path=env_path)





# Google Calendar OAuth Configuration



GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")



GOOGLE_TOKEN_ENCRYPTION_KEY = os.getenv(

    "GOOGLE_TOKEN_ENCRYPTION_KEY"

)



if not GOOGLE_TOKEN_ENCRYPTION_KEY:

    raise RuntimeError(

        "GOOGLE_TOKEN_ENCRYPTION_KEY is missing from .env"

    )



fernet = Fernet(GOOGLE_TOKEN_ENCRYPTION_KEY.encode())



def encrypt_google_token(token: str) -> str:

    return fernet.encrypt(token.encode()).decode()





def decrypt_google_token(encrypted_token: str) -> str:

    try:

        return fernet.decrypt(encrypted_token.encode()).decode()

    except InvalidToken:

        raise HTTPException(

            status_code=500,

            detail="Unable to decrypt Google credentials."

        )



STATE_SECRET = os.getenv("JWT_SECRET")



state_serializer = URLSafeTimedSerializer(STATE_SECRET)



# Server-side temporary storage for PKCE verification

_oauth_pkce_store = {}

_oauth_pkce_lock = threading.Lock()

OAUTH_STATE_MAX_AGE_SECONDS = 900  # 15 minutes





def generate_pkce_verifier() -> str:

    """Generates a cryptographically secure 128-character PKCE code_verifier per RFC 7636."""

    chars = string.ascii_letters + string.digits + "-._~"

    return "".join(secrets.choice(chars) for _ in range(128))





def store_pkce_verifier(state_token: str, user_id: int, code_verifier: str) -> None:

    """

    Securely stores the PKCE code_verifier bound to the signed state and user_id.

    Automatically purges expired records.

    """

    now = time.time()

    with _oauth_pkce_lock:

        expired_keys = [

            k for k, v in _oauth_pkce_store.items()

            if v.get("expires_at", 0) <= now

        ]

        for k in expired_keys:

            _oauth_pkce_store.pop(k, None)



        _oauth_pkce_store[state_token] = {

            "user_id": user_id,

            "code_verifier": code_verifier,

            "created_at": now,

            "expires_at": now + OAUTH_STATE_MAX_AGE_SECONDS,

        }





def retrieve_and_remove_pkce_verifier(state_token: str, user_id: int) -> Optional[str]:

    """

    Retrieves and immediately removes the PKCE code_verifier for the given state and user.

    Enforces TTL expiration and user binding.

    """

    now = time.time()

    with _oauth_pkce_lock:

        entry = _oauth_pkce_store.pop(state_token, None)

        if not entry:

            return None



        if entry.get("expires_at", 0) <= now:

            return None



        if entry.get("user_id") != user_id:

            return None



        return entry.get("code_verifier")





def remove_pkce_verifier(state_token: Optional[str]) -> None:

    """Removes temporary PKCE data on cancellation or failure."""

    if not state_token:

        return

    with _oauth_pkce_lock:

        _oauth_pkce_store.pop(state_token, None)





GOOGLE_REDIRECT_URI = (os.getenv("GOOGLE_REDIRECT_URI") or "").strip() or "http://127.0.0.1:8000/auth/google/callback"



GOOGLE_SCOPES = [

    "https://www.googleapis.com/auth/calendar.events.owned"

]



DEFAULT_FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500/frontend/index.html")





def build_frontend_redirect(base_url: str, params: dict) -> str:

    target = base_url.strip() if base_url and base_url.strip() else DEFAULT_FRONTEND_URL

    hash_part = ""

    if "#" in target:

        target, hash_part = target.split("#", 1)

        hash_part = f"#{hash_part}"



    query_str = urlencode(params)

    separator = "&" if "?" in target else "?"

    return f"{target}{separator}{query_str}{hash_part}"





class EventCancelledOnGoogleError(Exception):

    """Raised when an existing deterministic event on Google Calendar is in 'cancelled' (deleted) status."""

    pass





class TimeoutGoogleAuthRequest(GoogleAuthRequest):

    """

    Wraps GoogleAuthRequest to enforce an explicit 5.0-second network socket timeout

    during Google OAuth token refresh operations.

    """

    def __init__(self, timeout: float = 5.0, session=None):

        super().__init__(session=session)

        self.timeout = timeout



    def __call__(self, *args, **kwargs):

        kwargs.setdefault('timeout', self.timeout)

        return super().__call__(*args, **kwargs)





def get_valid_google_credentials(user_id: int, db: Session) -> Optional[Credentials]:

    """

    Retrieves and decrypts Google OAuth credentials for the specified user.

    If the access token has expired and a refresh token is present, it automatically

    refreshes the access token using Google's token endpoint and updates PostgreSQL.

    Returns valid Credentials or None.

    """

    google_credential = db.query(models.GoogleCredential).filter(

        models.GoogleCredential.user_id == user_id

    ).first()



    if not google_credential or not google_credential.access_token:

        return None



    try:

        access_token = decrypt_google_token(google_credential.access_token)

        refresh_token = (

            decrypt_google_token(google_credential.refresh_token)

            if google_credential.refresh_token

            else None

        )

    except Exception as e:

        print("Error decrypting Google credentials for user:", user_id, type(e).__name__)

        return None



    expiry_val = google_credential.token_expiry

    creds = Credentials(

        token=access_token,

        refresh_token=refresh_token,

        token_uri="https://oauth2.googleapis.com/token",

        client_id=GOOGLE_CLIENT_ID,

        client_secret=GOOGLE_CLIENT_SECRET,

        scopes=GOOGLE_SCOPES,

        expiry=expiry_val

    )



    # Check whether the access token has expired or is expiring soon (within 60 seconds)

    is_expired = False

    if expiry_val:

        now_utc = datetime.now(timezone.utc)

        expiry_dt = expiry_val

        if expiry_dt.tzinfo is None:

            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)

        if expiry_dt <= now_utc + timedelta(seconds=60):

            is_expired = True

    elif creds.expired:

        is_expired = True



    if is_expired:

        if not creds.refresh_token:

            print(f"User {user_id} Google access token is expired with no refresh token available.")

            return None



        try:

            auth_request = TimeoutGoogleAuthRequest(timeout=5.0)

            creds.refresh(auth_request)



            # Update the re-encrypted access token and expiry in PostgreSQL

            google_credential.access_token = encrypt_google_token(creds.token)

            if creds.expiry:

                google_credential.token_expiry = creds.expiry

            db.commit()

            print(f"Successfully refreshed Google access token for user {user_id}")

        except Exception as refresh_err:

            db.rollback()

            err_str = str(refresh_err).lower()

            if "invalid_grant" in err_str:

                print(f"User {user_id} Google refresh token revoked or expired (invalid_grant).")

            elif "timeout" in err_str:

                print(f"User {user_id} Google token refresh timed out (5s exceeded).")

            else:

                print(f"Failed to refresh Google access token for user {user_id}: {type(refresh_err).__name__}")

            return None



    return creds



app = FastAPI(title="TeamSync API")

# Explicit allowed origins for production and local development
allowed_origins = [
    "https://teamsync-mu-snowy.vercel.app",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

# Allow additional custom origins via environment variable if provided
_extra_origins = os.getenv("ALLOWED_ORIGINS") or os.getenv("CORS_ALLOWED_ORIGINS") or ""
if _extra_origins.strip():
    for _origin in _extra_origins.split(","):
        _cleaned = _origin.strip()
        if _cleaned and _cleaned not in allowed_origins:
            allowed_origins.append(_cleaned)

# If FRONTEND_URL environment variable is provided, ensure its origin is allowed
_env_frontend = os.getenv("FRONTEND_URL")
if _env_frontend and _env_frontend.strip():
    from urllib.parse import urlparse
    _parsed = urlparse(_env_frontend.strip())
    if _parsed.scheme and _parsed.netloc:
        _fe_origin = f"{_parsed.scheme}://{_parsed.netloc}"
        if _fe_origin not in allowed_origins:
            allowed_origins.append(_fe_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Create database tables if they don't exist

Base.metadata.create_all(bind=engine)





def run_sessions_table_migration():

    """

    Safely adds description, created_by, created_at, updated_at, and Phase 5 sync columns

    to PostgreSQL sessions table without dropping the table or losing any existing records.

    """

    from sqlalchemy import text

    try:

        with engine.connect() as conn:

            conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS description TEXT;"))

            conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id) ON DELETE SET NULL;"))

            conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))

            conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))

            # Phase 5: Google Calendar Reliability & Synchronization columns

            conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS calendar_sync_status VARCHAR(30) DEFAULT 'not_connected';"))

            conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS calendar_sync_error TEXT;"))

            conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS calendar_synced_at TIMESTAMP WITH TIME ZONE;"))

            conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS calendar_sync_started_at TIMESTAMP WITH TIME ZONE;"))

            conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS calendar_sync_attempt_id VARCHAR(64);"))

            conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS calendar_event_version INTEGER DEFAULT 1;"))

            conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS calendar_owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL;"))

            conn.execute(text("UPDATE sessions SET calendar_event_version = 1 WHERE calendar_event_version IS NULL;"))



            # Backfill existing data

            conn.execute(text("UPDATE sessions SET calendar_sync_status = 'synced' WHERE google_event_id IS NOT NULL AND (calendar_sync_status IS NULL OR calendar_sync_status = 'not_connected');"))

            conn.execute(text("UPDATE sessions SET calendar_sync_status = 'not_connected' WHERE google_event_id IS NULL AND calendar_sync_status IS NULL;"))

            conn.execute(text("UPDATE sessions SET calendar_synced_at = updated_at WHERE calendar_synced_at IS NULL AND google_event_id IS NOT NULL;"))

            conn.execute(text("UPDATE sessions SET calendar_owner_id = created_by WHERE calendar_owner_id IS NULL AND created_by IS NOT NULL;"))



            # Ensure calendar_sync_logs table exists

            conn.execute(text("""

                CREATE TABLE IF NOT EXISTS calendar_sync_logs (

                    id SERIAL PRIMARY KEY,

                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

                    session_id INTEGER,

                    calendar_owner_id INTEGER,

                    session_title VARCHAR(150),

                    google_event_id VARCHAR(255),

                    operation VARCHAR(30) NOT NULL,

                    status VARCHAR(30) NOT NULL DEFAULT 'pending',

                    error TEXT,

                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP

                );

            """))

            conn.execute(text("ALTER TABLE calendar_sync_logs ADD COLUMN IF NOT EXISTS session_id INTEGER;"))

            conn.execute(text("ALTER TABLE calendar_sync_logs ADD COLUMN IF NOT EXISTS calendar_owner_id INTEGER;"))

            conn.commit()

    except Exception as e:

        print("Note on sessions table migration:", type(e).__name__, str(e))





def reconcile_interrupted_sync_operations():

    """

    Reconciles orphaned or interrupted synchronization operations from prior server runs.

    Only marks operations as failed if they have been in 'syncing' or 'pending' state

    for longer than 5 minutes (STALE_SYNC_THRESHOLD_MINUTES), preventing false failures

    across multiple workers or immediate restarts.

    """

    from sqlalchemy import text

    try:

        with engine.connect() as conn:

            conn.execute(text("""

                UPDATE sessions

                SET calendar_sync_status = 'failed',

                    calendar_sync_error = 'Synchronization timed out or was interrupted by a server restart. Please retry.',

                    calendar_sync_attempt_id = NULL

                WHERE calendar_sync_status IN ('pending', 'syncing')

                  AND google_event_id IS NULL

                  AND (

                      (calendar_sync_started_at IS NOT NULL AND calendar_sync_started_at < CURRENT_TIMESTAMP - INTERVAL '5 minutes')

                      OR (calendar_sync_started_at IS NULL AND updated_at < CURRENT_TIMESTAMP - INTERVAL '5 minutes')

                  );

            """))

            conn.commit()

    except Exception as e:

        print("Note on sync reconciliation:", type(e).__name__, str(e))





run_sessions_table_migration()

reconcile_interrupted_sync_operations()





# Database session dependency

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()





# ── Authentication & Security Helpers ──

security = HTTPBearer(auto_error=False)







JWT_SECRET = os.getenv("JWT_SECRET")

if not JWT_SECRET or not JWT_SECRET.strip():

    raise RuntimeError("JWT_SECRET environment variable is missing or empty in .env. Please configure it before starting the backend.")



JWT_ALGORITHM = "HS256"





def create_access_token(user_id: int) -> str:

    payload = {

        "sub": str(user_id),

        "exp": datetime.now(timezone.utc) + timedelta(days=30)

    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)





def get_current_user(

    auth: HTTPAuthorizationCredentials = Depends(security),

    db: Session = Depends(get_db)

) -> models.User:

    if not auth or not auth.credentials:

        raise HTTPException(status_code=401, detail="Please log in to perform this action.")

    try:

        payload = jwt.decode(auth.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        user_id_str = payload.get("sub")

        if not user_id_str:

            raise HTTPException(status_code=401, detail="Invalid authentication token.")

        user_id = int(user_id_str)

    except (JWTError, ValueError):

        raise HTTPException(status_code=401, detail="Session expired or invalid. Please log in again.")



    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:

        raise HTTPException(status_code=401, detail="User not found.")

    return user





@app.get("/auth/google/connect")

def google_connect(

    return_url: Optional[str] = None,

    current_user: models.User = Depends(get_current_user)

):

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:

        raise HTTPException(

            status_code=500,

            detail="Google OAuth credentials are not configured in backend .env."

        )



    # 1. Generate PKCE code_verifier for this authorization session per RFC 7636

    code_verifier = generate_pkce_verifier()



    # 2. Encrypt code_verifier with server Fernet key for secondary tamper-proof state storage

    encrypted_verifier = encrypt_google_token(code_verifier)



    # 3. Securely encode user identity, return URL, and encrypted verifier into signed state

    state_payload = {

        "user_id": current_user.id,

        "enc_verifier": encrypted_verifier

    }

    if return_url and return_url.strip():

        state_payload["return_url"] = return_url.strip()



    state = state_serializer.dumps(

        state_payload,

        salt="google-oauth-state"

    )



    # 4. Store in server-side PKCE memory cache with expiration bound to state & user

    store_pkce_verifier(state, current_user.id, code_verifier)



    # 5. Initialize Google Flow with the generated PKCE verifier

    flow = Flow.from_client_config(

        {

            "web": {

                "client_id": GOOGLE_CLIENT_ID,

                "client_secret": GOOGLE_CLIENT_SECRET,

                "auth_uri": "https://accounts.google.com/o/oauth2/auth",

                "token_uri": "https://oauth2.googleapis.com/token",

                "redirect_uris": [GOOGLE_REDIRECT_URI]

            }

        },

        scopes=GOOGLE_SCOPES,

        state=state

    )



    flow.redirect_uri = GOOGLE_REDIRECT_URI

    flow.code_verifier = code_verifier



    authorization_url, _ = flow.authorization_url(

        access_type="offline",

        include_granted_scopes="true",

        prompt="consent"

    )



    return {"authorization_url": authorization_url}





@app.get("/auth/google/status")

def get_google_status(

    current_user: models.User = Depends(get_current_user),

    db: Session = Depends(get_db)

):

    """

    Checks the user's Google Calendar connection status and credential health.

    Distinguishes:

    - Connected with usable credentials

    - Disconnected (no credentials stored)

    - Requires reconnection (expired credentials with no valid refresh token, or revoked)

    """

    google_credential = db.query(models.GoogleCredential).filter(

        models.GoogleCredential.user_id == current_user.id

    ).first()



    if not google_credential or not google_credential.access_token:

        return {

            "connected": False,

            "status": "disconnected",

            "requires_reconnect": False,

            "message": "Google Calendar is not connected."

        }



    # Validate credential usability without unnecessary external calls

    # get_valid_google_credentials only makes an external Google call if token is expired and refresh is attempted

    creds = get_valid_google_credentials(current_user.id, db)

    if not creds:

        return {

            "connected": False,

            "status": "requires_reconnect",

            "requires_reconnect": True,

            "message": "Google authorization has expired or was revoked. Please reconnect."

        }



    return {

        "connected": True,

        "status": "connected",

        "requires_reconnect": False,

        "token_expiry": google_credential.token_expiry.isoformat() if google_credential.token_expiry else None,

        "scopes": google_credential.scopes,

        "message": "Google Calendar is connected and active."

    }





@app.post("/auth/google/disconnect")

def google_disconnect(

    current_user: models.User = Depends(get_current_user),

    db: Session = Depends(get_db)

):

    """

    Disconnects the authenticated user's Google Calendar by safely removing their

    encrypted credentials from PostgreSQL. Preserves all TeamSync study sessions

    and existing Google Calendar event IDs.

    """

    google_credential = db.query(models.GoogleCredential).filter(

        models.GoogleCredential.user_id == current_user.id

    ).first()



    if not google_credential:

        return {

            "success": True,

            "message": "Google Calendar was not connected.",

            "connected": False

        }



    db.delete(google_credential)

    db.commit()



    return {

        "success": True,

        "message": "Google Calendar disconnected successfully.",

        "connected": False

    }





def get_optional_user(

    auth: HTTPAuthorizationCredentials = Depends(security),

    db: Session = Depends(get_db)

):

    if not auth or not auth.credentials:

        return None

    try:

        payload = jwt.decode(auth.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        user_id = int(payload.get("sub"))

        return db.query(models.User).filter(models.User.id == user_id).first()

    except Exception:

        return None





def generate_invite_code() -> str:

    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    code = "".join(secrets.choice(alphabet) for _ in range(6))

    return f"TS-{code}"





def hash_password(password: str) -> str:

    salt = secrets.token_hex(16)

    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)

    return salt + ":" + key.hex()





def verify_password(password: str, hashed: str) -> bool:

    try:

        salt, key_hex = hashed.split(":")

        test_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)

        return secrets.compare_digest(test_key.hex(), key_hex)

    except Exception:

        return False





# ── Request Body Schemas ──

class GroupCreate(BaseModel):

    name: str

    subject: str = ""

    description: str





class TaskCreate(BaseModel):

    title: str

    description: Optional[str] = ""

    assigned_to: Optional[int] = None

    due_date: Optional[str] = None

    status: Optional[str] = "pending"





class TaskStatusUpdate(BaseModel):

    status: str





def parse_due_date(due_str: Optional[str]) -> Optional[datetime]:

    if not due_str or not str(due_str).strip():

        return None

    cleaned = str(due_str).strip()

    try:

        dt = datetime.fromisoformat(cleaned)

        if dt.tzinfo is None:

            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except Exception:

        pass

    try:

        dt = datetime.strptime(cleaned, "%Y-%m-%d")

        return dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

    except Exception:

        pass

    try:

        dt = datetime.strptime(cleaned, "%Y-%m-%dT%H:%M")

        return dt.replace(tzinfo=timezone.utc)

    except Exception:

        pass

    return None





def serialize_task(t: models.Task):

    is_overdue = False

    if t.due_date and (t.status or "pending").lower() != "completed":

        now = datetime.now(timezone.utc)

        is_overdue = t.due_date < now



    return {

        "id": t.id,

        "group_id": t.group_id,

        "title": t.title,

        "description": t.description or "",

        "status": (t.status or "pending").lower(),

        "due_date": t.due_date.isoformat() if t.due_date else None,

        "due_date_formatted": t.due_date.strftime("%b %d, %Y") if t.due_date else None,

        "due_date_iso": t.due_date.strftime("%Y-%m-%d") if t.due_date else None,

        "is_overdue": is_overdue,

        "assigned_to": t.assigned_to,

        "assignee": {

            "id": t.assignee.id,

            "name": t.assignee.name,

            "email": t.assignee.email

        } if t.assignee else None

    }





def get_group_task_stats(db: Session, group_id: int):

    tasks = db.query(models.Task).filter(models.Task.group_id == group_id).all()

    total = len(tasks)

    pending = sum(1 for t in tasks if (t.status or "").lower() == "pending")

    in_progress = sum(1 for t in tasks if (t.status or "").lower() == "in_progress")

    completed = sum(1 for t in tasks if (t.status or "").lower() == "completed")

    rate = round((completed / total) * 100) if total > 0 else 0

    active = pending + in_progress

    return {

        "total": total,

        "pending": pending,

        "in_progress": in_progress,

        "completed": completed,

        "active": active,

        "completion_rate": rate

    }





class SessionCreate(BaseModel):

    title: str

    description: Optional[str] = None

    start_time: datetime

    end_time: datetime





class SessionUpdate(BaseModel):

    title: str

    description: Optional[str] = None

    start_time: datetime

    end_time: datetime





class JoinGroupRequest(BaseModel):

    invite_code: str





class UserSignup(BaseModel):

    name: str

    email: str

    password: str





class UserLogin(BaseModel):

    email: str

    password: str





# ── General Routes ──

@app.get("/")

def home():

    return {"message": "TeamSync backend is running!"}





@app.get("/api/platform/stats")

def get_platform_stats(db: Session = Depends(get_db)):

    """

    Returns platform-wide aggregate counts for landing page statistics.

    Does not expose sensitive or user-identifying information.

    """

    students_count = db.query(models.User).count()

    groups_count = db.query(models.Group).count()

    sessions_count = db.query(models.StudySession).count()

    return {

        "success": True,

        "students_count": students_count,

        "groups_count": groups_count,

        "sessions_count": sessions_count

    }





# ── Google Calendar & Session Helpers ──

GOOGLE_API_SOCKET_TIMEOUT = 5.0



def get_calendar_service(creds: Credentials):

    """

    Builds a Google Calendar API v3 service client with an explicit 5.0-second socket timeout.

    Uses httplib2.Http(timeout=5.0) and AuthorizedHttp to ensure hanging network connections

    never block FastAPI requests beyond the configured limit.

    """

    http_transport = httplib2.Http(timeout=GOOGLE_API_SOCKET_TIMEOUT)

    authorized_http = google_auth_httplib2.AuthorizedHttp(creds, http=http_transport)

    return build("calendar", "v3", http=authorized_http, cache_discovery=False)





def generate_deterministic_event_id(session_id: int, version: int = 1) -> str:

    """

    Generates a deterministic Google Calendar event ID compliant with Google's base32hex specification:

    - Length between 5 and 1024 characters.

    - Only lowercase characters [0-9a-v].

    - Stable across retries for the same TeamSync session ID and version to prevent duplicate event insertion.

    - Incrementing version produces a fresh unique ID if a previous event was deleted/cancelled on Google.

    """

    v = max(1, int(version or 1))

    digest = hashlib.md5(f"teamsync_session_{session_id}_v{v}".encode("utf-8")).hexdigest()[:14]

    return f"tsess{session_id:08d}v{v}{digest}"





def create_google_calendar_event(

    creds: Credentials,

    title: str,

    description: Optional[str],

    start_time: datetime,

    end_time: datetime,

    group_name: Optional[str] = None,

    event_id: Optional[str] = None,

    session_id: Optional[int] = None

) -> Optional[str]:

    """

    Creates an event in the user's primary Google Calendar with a 5-second socket timeout.

    Does NOT automatically retry on failure (num_retries=0) to prevent duplicate calendar events.

    Supports deterministic client-generated event_id to prevent duplicates on retries.

    Returns the google_event_id if successful, or None if creation fails.

    """

    try:

        service = get_calendar_service(creds)



        summary = f"[TeamSync] {title}"

        desc = description or ""

        if group_name:

            desc = f"Study Group: {group_name}\n\n{desc}".strip()



        # Format datetimes to ISO 8601 strings with timezone

        if start_time.tzinfo is None:

            start_iso = start_time.replace(tzinfo=timezone.utc).isoformat()

        else:

            start_iso = start_time.isoformat()



        if end_time.tzinfo is None:

            end_iso = end_time.replace(tzinfo=timezone.utc).isoformat()

        else:

            end_iso = end_time.isoformat()



        event_body = {

            "summary": summary,

            "description": desc,

            "start": {

                "dateTime": start_iso,

            },

            "end": {

                "dateTime": end_iso,

            },

        }

        if event_id:

            event_body["id"] = event_id

        if session_id is not None:

            event_body["extendedProperties"] = {

                "private": {

                    "teamsync_session_id": str(session_id),

                    "teamsync_app": "teamsync"

                }

            }



        # Do NOT auto-retry event creation to prevent duplicate events if response was lost

        created_event = service.events().insert(

            calendarId="primary",

            body=event_body

        ).execute(num_retries=0)



        return created_event.get("id")

    except HttpError as http_err:

        status_code = http_err.resp.status if hasattr(http_err, 'resp') else None

        if status_code == 409 and event_id:

            # Deterministic ID already exists on Google Calendar!

            print(f"Google Calendar event {event_id} already exists (409 Conflict). Verifying existing event...")

            try:

                get_call = service.events().get(

                    calendarId="primary",

                    eventId=event_id

                )

                existing_event = get_call.execute(num_retries=1) if hasattr(get_call, "execute") else get_call

            except Exception as get_err:

                print(f"Failed to fetch conflicting event {event_id}: {type(get_err).__name__}: {str(get_err)}")

                return None



            if isinstance(existing_event, dict):

                event_status = existing_event.get("status")

                if event_status == "cancelled":

                    print(f"Conflicting event {event_id} is marked cancelled/deleted on Google Calendar.")

                    raise EventCancelledOnGoogleError(f"Event {event_id} is cancelled on Google Calendar.")



                ext_props = existing_event.get("extendedProperties", {}).get("private", {})

                owner_session_id = ext_props.get("teamsync_session_id") if isinstance(ext_props, dict) else None

                if session_id is not None and (owner_session_id is None or str(owner_session_id) != str(session_id)):

                    print(f"Conflict verification failed: Event {event_id} has session {owner_session_id}, not {session_id}! Rejecting.")

                    return None



            # Active verified event belonging to this TeamSync session!

            # Do NOT update Google Calendar inside the 409 handler with this worker's potentially stale payload.

            # Return the verified event_id. Any necessary update of event details is handled by a separately

            # claimed synchronization path using the latest committed database values.

            return event_id

        if status_code == 429:

            print("Google Calendar API 429: Rate limit exceeded. Skipping automatic creation retry.")

        elif status_code and 500 <= status_code < 600:

            print(f"Google Calendar API {status_code}: Temporary Google server error. Creation not retried.")

        elif status_code == 401:

            print("Google Calendar API 401: Authentication credentials invalid on creation.")

        elif status_code == 403:

            print("Google Calendar API 403: Permission denied on creation.")

        else:

            print(f"Google Calendar API error {status_code}: Request failed.")

        return None

    except EventCancelledOnGoogleError:

        raise

    except (TimeoutError, socket.timeout) as timeout_err:

        print(f"Google Calendar network timeout (5s socket timeout exceeded during creation): {type(timeout_err).__name__}")

        return None

    except Exception as e:

        print("Failed to create Google Calendar event:", type(e).__name__, str(e))

        return None





def update_google_calendar_event(

    creds: Credentials,

    event_id: str,

    title: str,

    description: Optional[str],

    start_time: datetime,

    end_time: datetime,

    group_name: Optional[str] = None

) -> bool:

    """

    Updates an existing event in the user's primary Google Calendar with a 5-second socket timeout.

    Allows at most one retry for transient errors (HTTP 429/5xx).

    Returns True if update succeeded, False otherwise.

    """

    try:

        service = get_calendar_service(creds)



        summary = f"[TeamSync] {title}"

        desc = description or ""

        if group_name:

            desc = f"Study Group: {group_name}\n\n{desc}".strip()



        if start_time.tzinfo is None:

            start_iso = start_time.replace(tzinfo=timezone.utc).isoformat()

        else:

            start_iso = start_time.isoformat()



        if end_time.tzinfo is None:

            end_iso = end_time.replace(tzinfo=timezone.utc).isoformat()

        else:

            end_iso = end_time.isoformat()



        event_body = {

            "summary": summary,

            "description": desc,

            "start": {

                "dateTime": start_iso,

            },

            "end": {

                "dateTime": end_iso,

            },

        }



        # Allow at most 1 retry for transient server failures (HTTP 429/5xx)

        service.events().update(

            calendarId="primary",

            eventId=event_id,

            body=event_body

        ).execute(num_retries=1)



        return True

    except HttpError as http_err:

        status_code = http_err.resp.status if hasattr(http_err, 'resp') else None

        if status_code in (404, 410):

            print(f"Google Calendar API {status_code}: Event {event_id} not found on Google Calendar to update.")

        elif status_code == 401:

            print("Google Calendar API 401: Authentication credentials invalid on update.")

        elif status_code == 403:

            print("Google Calendar API 403: Permission denied on update.")

        elif status_code == 429:

            print("Google Calendar API 429: Rate limit exceeded during update.")

        elif status_code and 500 <= status_code < 600:

            print(f"Google Calendar API {status_code}: Temporary Google server error on update.")

        else:

            print(f"Google Calendar API error {status_code} on update.")

        return False

    except (TimeoutError, socket.timeout) as timeout_err:

        print(f"Google Calendar update network timeout (5s socket timeout exceeded): {type(timeout_err).__name__}")

        return False

    except Exception as e:

        print("Failed to update Google Calendar event:", type(e).__name__, str(e))

        return False





def delete_google_calendar_event(

    creds: Credentials,

    event_id: str

) -> bool:

    """

    Deletes an event from the user's primary Google Calendar with a 5-second socket timeout.

    Returns True if deleted or already gone (404/410), False on other error.

    Allows at most one retry for transient errors (429/5xx).

    """

    try:

        service = get_calendar_service(creds)

        # Allow at most 1 retry for transient server failures (429/5xx)

        service.events().delete(

            calendarId="primary",

            eventId=event_id

        ).execute(num_retries=1)

        return True

    except HttpError as http_err:

        status_code = http_err.resp.status if hasattr(http_err, 'resp') else None

        if status_code in (404, 410):

            # Already deleted on Google Calendar - treat as clean success

            return True

        elif status_code == 401:

            print("Google Calendar API 401: Authentication credentials invalid on delete.")

        elif status_code == 403:

            print("Google Calendar API 403: Permission denied on delete.")

        elif status_code == 429:

            print("Google Calendar API 429: Rate limit exceeded during delete.")

        elif status_code and 500 <= status_code < 600:

            print(f"Google Calendar API {status_code}: Temporary Google server error on delete.")

        else:

            print(f"Google Calendar API error {status_code} on delete.")

        return False

    except (TimeoutError, socket.timeout) as timeout_err:

        print(f"Google Calendar delete network timeout (5s socket timeout exceeded): {type(timeout_err).__name__}")

        return False

    except Exception as e:

        err_msg = str(e).lower()

        if "404" in err_msg or "410" in err_msg or "not found" in err_msg or "deleted" in err_msg:

            return True

        print("Failed to delete Google Calendar event:", type(e).__name__, str(e))

        return False





def serialize_session(session: models.StudySession) -> dict:

    creator_name = session.creator.name if session.creator else "Unknown Member"

    group_name = session.group.name if session.group else "Study Group"



    start_str = session.start_time.strftime("%a, %b %d · %I:%M %p") if hasattr(session.start_time, "strftime") else str(session.start_time)

    end_str = session.end_time.strftime("%I:%M %p") if hasattr(session.end_time, "strftime") else str(session.end_time)



    sync_status = getattr(session, "calendar_sync_status", None) or ("synced" if session.google_event_id else "not_connected")



    return {

        "id": session.id,

        "group_id": session.group_id,

        "group_name": group_name,

        "title": session.title,

        "description": session.description or "",

        "start_time": session.start_time.isoformat() if hasattr(session.start_time, "isoformat") else str(session.start_time),

        "end_time": session.end_time.isoformat() if hasattr(session.end_time, "isoformat") else str(session.end_time),

        "formatted_time": f"{start_str} – {end_str}",

        "time": f"{start_str} – {end_str}",

        "day": session.start_time.strftime("%a").upper() if hasattr(session.start_time, "strftime") else "UPC",

        "date": session.start_time.strftime("%d") if hasattr(session.start_time, "strftime") else "01",

        "month": session.start_time.strftime("%b") if hasattr(session.start_time, "strftime") else "JAN",

        "tag": "Past" if (session.end_time.replace(tzinfo=timezone.utc) if session.end_time.tzinfo is None else session.end_time) < datetime.now(timezone.utc) else "Upcoming",

        "created_by": session.created_by,

        "creator_name": creator_name,

        "calendar_owner_id": getattr(session, "calendar_owner_id", None),

        "google_event_id": session.google_event_id,

        "calendar_synced": bool(session.google_event_id),

        "calendar_sync_status": sync_status,

        "calendar_sync_error": getattr(session, "calendar_sync_error", None),

        "calendar_sync_started_at": session.calendar_sync_started_at.isoformat() if hasattr(session, "calendar_sync_started_at") and getattr(session, "calendar_sync_started_at", None) else None,

        "calendar_synced_at": session.calendar_synced_at.isoformat() if hasattr(session, "calendar_synced_at") and getattr(session, "calendar_synced_at", None) else None,

        "calendar_sync_attempt_id": getattr(session, "calendar_sync_attempt_id", None),

        "calendar_event_version": getattr(session, "calendar_event_version", 1),

        "created_at": session.created_at.isoformat() if hasattr(session.created_at, "isoformat") and session.created_at else None,

        "updated_at": session.updated_at.isoformat() if hasattr(session.updated_at, "isoformat") and session.updated_at else None,

    }





TEAMSYNC_ADVISORY_LOCK_NAMESPACE = 1414748494  # 0x5453594E ('TSYN' in ASCII)



@contextmanager

def session_calendar_mutex(session_id: int, timeout_seconds: float = 10.0):

    """

    Acquires a PostgreSQL session-level advisory lock using a dedicated engine connection.

    Serializes all Google Calendar mutations (create, update, delete, reconcile) for the given session_id.



    Guarantees:

    - Namespaced via (TEAMSYNC_ADVISORY_LOCK_NAMESPACE, session_id) avoiding collisions.

    - Uses a dedicated engine connection held for the entire critical section.

    - Does not hold any open database transaction during external Google network calls.

    - Yields True if acquired, False on timeout/failure.

    - Always releases the lock and returns the connection to the pool in a finally block.

    """

    conn = engine.connect()

    conn = conn.execution_options(isolation_level="AUTOCOMMIT")

    locked = False

    deadline = time.time() + max(1.0, float(timeout_seconds))

    sid = int(session_id)

    ns = int(TEAMSYNC_ADVISORY_LOCK_NAMESPACE)



    try:

        while time.time() < deadline:

            try:

                res = conn.execute(

                    text("SELECT pg_try_advisory_lock(:ns, :sid)"),

                    {"ns": ns, "sid": sid}

                ).scalar()

                if res:

                    locked = True

                    break

            except Exception as lock_err:

                print(f"Error checking advisory lock for session {session_id}: {type(lock_err).__name__}: {lock_err}")

                break

            time.sleep(0.02)



        yield locked

    finally:

        if locked:

            try:

                conn.execute(

                    text("SELECT pg_advisory_unlock(:ns, :sid)"),

                    {"ns": ns, "sid": sid}

                )

            except Exception as unlock_err:

                print(f"Note: Error releasing advisory lock for session {session_id}: {type(unlock_err).__name__}: {unlock_err}")

        try:

            conn.close()

        except Exception:

            pass





def reconcile_stale_external_operation(session_id: int, user_id: int) -> bool:

    """

    Safely reconciles Google Calendar when a worker's external operation succeeded

    on Google Calendar but its database write was fenced out (superseded).



    Guarantees:

    - Never uses stale worker payload; re-reads fresh committed state from PostgreSQL.

    - Atomically claims the session under a fresh UUID token; never overwrites an active 'syncing' claim.

    - Serialized per-session using PostgreSQL advisory locking.

    - If the session was deleted, respects deletion and does nothing.

    """

    rec_db = SessionLocal()

    rec_attempt_id = str(uuid.uuid4())

    try:

        now_utc = datetime.now(timezone.utc)



        # 1. Atomic claim: Only claim if NOT currently in 'syncing' (i.e. another active worker has not claimed it)

        claim_count = rec_db.query(models.StudySession).filter(

            models.StudySession.id == session_id,

            models.StudySession.calendar_sync_status.in_(["synced", "pending", "failed"])

        ).update({

            "calendar_sync_status": "syncing",

            "calendar_sync_started_at": now_utc,

            "calendar_sync_attempt_id": rec_attempt_id

        }, synchronize_session=False)

        rec_db.commit()



        if claim_count == 0:

            return False



        with session_calendar_mutex(session_id) as acquired:

            if not acquired:

                print(f"Reconcile worker {rec_attempt_id} could not acquire lock for session {session_id}. Aborting.")

                return False



            # Reload fresh committed state from PostgreSQL after acquiring advisory lock

            session = rec_db.query(models.StudySession).filter(models.StudySession.id == session_id).first()

            if not session:

                return False



            # Verify that worker still owns the current claim token

            if session.calendar_sync_attempt_id != rec_attempt_id:

                print(f"Reconcile worker {rec_attempt_id} lost claim while waiting for lock. Aborting.")

                return False



            target_owner_id = session.calendar_owner_id or session.created_by or user_id

            creds = get_valid_google_credentials(target_owner_id, rec_db)

            if not creds:

                rec_db.query(models.StudySession).filter(

                    models.StudySession.id == session_id,

                    models.StudySession.calendar_sync_attempt_id == rec_attempt_id

                ).update({

                    "calendar_sync_status": "failed",

                    "calendar_sync_error": "Google Calendar disconnected during reconciliation.",

                    "calendar_sync_attempt_id": None

                }, synchronize_session=False)

                rec_db.commit()

                return False



            title = session.title

            description = session.description

            start_time = session.start_time

            end_time = session.end_time

            group_name = session.group.name if session.group else None

            google_event_id = session.google_event_id



            if google_event_id:

                success = update_google_calendar_event(

                    creds=creds,

                    event_id=google_event_id,

                    title=title,

                    description=description,

                    start_time=start_time,

                    end_time=end_time,

                    group_name=group_name

                )

                if success:

                    fenced = rec_db.query(models.StudySession).filter(

                        models.StudySession.id == session_id,

                        models.StudySession.calendar_sync_attempt_id == rec_attempt_id

                    ).update({

                        "calendar_sync_status": "synced",

                        "calendar_sync_error": None,

                        "calendar_synced_at": datetime.now(timezone.utc),

                        "calendar_sync_attempt_id": None

                    }, synchronize_session=False)

                    if fenced > 0:

                        rec_db.commit()

                        return True

                    else:

                        rec_db.rollback()

                        return False

                else:

                    rec_db.query(models.StudySession).filter(

                        models.StudySession.id == session_id,

                        models.StudySession.calendar_sync_attempt_id == rec_attempt_id

                    ).update({

                        "calendar_sync_status": "failed",

                        "calendar_sync_error": "Reconciliation failed to update Google Calendar event.",

                        "calendar_sync_attempt_id": None

                    }, synchronize_session=False)

                    rec_db.commit()

                    return False

            else:

                event_version = session.calendar_event_version or 1

                deterministic_id = generate_deterministic_event_id(session.id, event_version)

                new_event_id = create_google_calendar_event(

                    creds=creds,

                    title=title,

                    description=description,

                    start_time=start_time,

                    end_time=end_time,

                    group_name=group_name,

                    event_id=deterministic_id,

                    session_id=session.id

                )

                if new_event_id:

                    fenced = rec_db.query(models.StudySession).filter(

                        models.StudySession.id == session_id,

                        models.StudySession.calendar_sync_attempt_id == rec_attempt_id

                    ).update({

                        "google_event_id": new_event_id,

                        "calendar_id": "primary",

                        "calendar_owner_id": target_owner_id,

                        "calendar_sync_status": "synced",

                        "calendar_sync_error": None,

                        "calendar_synced_at": datetime.now(timezone.utc),

                        "calendar_sync_attempt_id": None

                    }, synchronize_session=False)

                    if fenced > 0:

                        rec_db.commit()

                        return True

                    else:

                        rec_db.rollback()

                        return False

                else:

                    rec_db.query(models.StudySession).filter(

                        models.StudySession.id == session_id,

                        models.StudySession.calendar_sync_attempt_id == rec_attempt_id

                    ).update({

                        "calendar_sync_status": "failed",

                        "calendar_sync_error": "Reconciliation failed to create Google Calendar event.",

                        "calendar_sync_attempt_id": None

                    }, synchronize_session=False)

                    rec_db.commit()

                    return False

    except Exception as e:

        print(f"Reconciliation exception: {type(e).__name__}: {str(e)}")

        try:

            rec_db.rollback()

        except Exception:

            pass

        return False

    finally:

        rec_db.close()





def bg_sync_create_calendar_event(session_id: int, user_id: int):

    """

    Background worker to create a Google Calendar event for a newly scheduled study session.

    Features:

    - Atomic conditional claim from pending/failed -> syncing with worker fencing token (UUID).

    - Deterministic Google event ID reuse (prevents duplicates across retries).

    - HTTP 409 verification and cancelled tombstone recovery via version bumping.

    - Handles creation/cancellation race: cleans up orphan event if session was deleted in-flight.

    - Uses original calendar owner's credentials strictly.

    - All writes fenced by calendar_sync_attempt_id.

    - Serialized per-session using PostgreSQL advisory locking.

    """

    bg_db = SessionLocal()

    worker_attempt_id = str(uuid.uuid4())

    try:

        now_utc = datetime.now(timezone.utc)



        # 1. Atomic claim: transition from 'pending' or 'failed' to 'syncing' with unique worker fencing token

        claim_count = bg_db.query(models.StudySession).filter(

            models.StudySession.id == session_id,

            models.StudySession.calendar_sync_status.in_(["pending", "failed"]),

            models.StudySession.google_event_id.is_(None)

        ).update({

            "calendar_sync_status": "syncing",

            "calendar_sync_started_at": now_utc,

            "calendar_sync_attempt_id": worker_attempt_id

        }, synchronize_session=False)

        bg_db.commit()



        if claim_count == 0:

            return



        with session_calendar_mutex(session_id) as acquired:

            if not acquired:

                print(f"Worker {worker_attempt_id} could not acquire lock for session {session_id}. Aborting.")

                return



            # Reload fresh committed state from PostgreSQL after acquiring advisory lock

            session = bg_db.query(models.StudySession).filter(models.StudySession.id == session_id).first()

            if not session:

                return



            if session.calendar_sync_attempt_id != worker_attempt_id:

                print(f"Worker {worker_attempt_id} lost claim while waiting for lock on session {session_id}. Aborting.")

                return



            target_owner_id = session.calendar_owner_id or session.created_by or user_id

            creds = get_valid_google_credentials(target_owner_id, bg_db)

            if not creds:

                bg_db.query(models.StudySession).filter(

                    models.StudySession.id == session_id,

                    models.StudySession.calendar_sync_attempt_id == worker_attempt_id

                ).update({

                    "calendar_sync_status": "not_connected",

                    "calendar_sync_error": "Google Calendar not connected or credentials expired.",

                    "calendar_sync_attempt_id": None

                }, synchronize_session=False)

                bg_db.commit()

                return



            event_version = session.calendar_event_version or 1

            deterministic_id = generate_deterministic_event_id(session.id, event_version)

            title = session.title

            description = session.description

            start_time = session.start_time

            end_time = session.end_time

            group_name = session.group.name if session.group else None



            try:

                event_id = create_google_calendar_event(

                    creds=creds,

                    title=title,

                    description=description,

                    start_time=start_time,

                    end_time=end_time,

                    group_name=group_name,

                    event_id=deterministic_id,

                    session_id=session.id

                )

            except EventCancelledOnGoogleError as cancel_err:

                print(f"Session {session_id} event was cancelled on Google Calendar: {cancel_err}. Incrementing event version.")

                bg_db.query(models.StudySession).filter(

                    models.StudySession.id == session_id,

                    models.StudySession.calendar_sync_attempt_id == worker_attempt_id

                ).update({

                    "calendar_event_version": models.StudySession.calendar_event_version + 1,

                    "calendar_sync_status": "failed",

                    "calendar_sync_error": "Previous calendar event was deleted on Google Calendar. Retrying will create a fresh event.",

                    "calendar_sync_attempt_id": None

                }, synchronize_session=False)

                bg_db.commit()

                return



            if event_id:

                # Recheck if session was cancelled/deleted during in-flight creation

                recheck_session = bg_db.query(models.StudySession).filter(models.StudySession.id == session_id).first()

                if not recheck_session:

                    # Session was deleted during creation! Clean up orphaned event

                    print(f"Session {session_id} was deleted during event creation. Cleaning up orphan event {event_id}...")

                    del_success = delete_google_calendar_event(creds, event_id)

                    del_log = bg_db.query(models.CalendarSyncLog).filter_by(

                        session_id=session_id,

                        operation="delete"

                    ).order_by(models.CalendarSyncLog.id.desc()).first()



                    if del_log:

                        del_log.google_event_id = event_id

                        del_log.status = "success" if del_success else "failed"

                        if not del_success:

                            del_log.error = "Orphaned Google event cleanup failed after session deletion."

                    else:

                        del_log = models.CalendarSyncLog(

                            user_id=user_id,

                            session_id=session_id,

                            calendar_owner_id=target_owner_id,

                            google_event_id=event_id,

                            operation="delete",

                            status="success" if del_success else "failed",

                            error=None if del_success else "Orphaned Google event cleanup failed after session deletion."

                        )

                        bg_db.add(del_log)

                    bg_db.commit()

                    return



                # Conditional fenced update: only commit if our worker still holds the claim token

                fenced_count = bg_db.query(models.StudySession).filter(

                    models.StudySession.id == session_id,

                    models.StudySession.calendar_sync_attempt_id == worker_attempt_id

                ).update({

                    "google_event_id": event_id,

                    "calendar_id": "primary",

                    "calendar_owner_id": target_owner_id,

                    "calendar_sync_status": "synced",

                    "calendar_sync_error": None,

                    "calendar_synced_at": datetime.now(timezone.utc),

                    "calendar_sync_attempt_id": None

                }, synchronize_session=False)



                if fenced_count > 0:

                    log_entry = models.CalendarSyncLog(

                        user_id=user_id,

                        session_id=session.id,

                        calendar_owner_id=target_owner_id,

                        session_title=session.title,

                        google_event_id=event_id,

                        operation="create",

                        status="success"

                    )

                    bg_db.add(log_entry)

                    bg_db.commit()

                else:

                    print(f"Worker {worker_attempt_id} lost fencing on session {session_id}. Reconciling.")

                    bg_db.rollback()

                    reconcile_stale_external_operation(session_id, user_id)

                    return

            else:

                fenced_count = bg_db.query(models.StudySession).filter(

                    models.StudySession.id == session_id,

                    models.StudySession.calendar_sync_attempt_id == worker_attempt_id

                ).update({

                    "calendar_sync_status": "failed",

                    "calendar_sync_error": "Failed to sync event with Google Calendar.",

                    "calendar_sync_attempt_id": None

                }, synchronize_session=False)



                if fenced_count > 0:

                    log_entry = models.CalendarSyncLog(

                        user_id=user_id,

                        session_id=session.id,

                        calendar_owner_id=target_owner_id,

                        session_title=session.title,

                        google_event_id=None,

                        operation="create",

                        status="failed",

                        error="Failed to sync event with Google Calendar."

                    )

                    bg_db.add(log_entry)

                    bg_db.commit()

                else:

                    bg_db.rollback()

    except Exception as e:

        print(f"Background create sync exception: {type(e).__name__}: {str(e)}")

        try:

            bg_db.query(models.StudySession).filter(

                models.StudySession.id == session_id,

                models.StudySession.calendar_sync_attempt_id == worker_attempt_id

            ).update({

                "calendar_sync_status": "failed",

                "calendar_sync_error": f"Sync error: {type(e).__name__}",

                "calendar_sync_attempt_id": None

            }, synchronize_session=False)

            bg_db.commit()

        except Exception:

            pass

    finally:

        bg_db.close()





def bg_sync_update_calendar_event(session_id: int, user_id: int):

    """

    Background worker to update an existing Google Calendar event.

    Uses its own isolated SessionLocal database session.

    Features:

    - Atomic conditional claim from pending/failed -> syncing with worker fencing token (UUID).

    - Strictly uses original calendar_owner_id credentials; never falls back to another user's primary calendar.

    - All writes fenced by calendar_sync_attempt_id.

    - Serialized per-session using PostgreSQL advisory locking.

    """

    bg_db = SessionLocal()

    worker_attempt_id = str(uuid.uuid4())

    try:

        now_utc = datetime.now(timezone.utc)



        # 1. Atomic claim: transition from pending/failed to syncing with fencing token

        claim_count = bg_db.query(models.StudySession).filter(

            models.StudySession.id == session_id,

            models.StudySession.calendar_sync_status.in_(["pending", "failed"])

        ).update({

            "calendar_sync_status": "syncing",

            "calendar_sync_started_at": now_utc,

            "calendar_sync_attempt_id": worker_attempt_id

        }, synchronize_session=False)

        bg_db.commit()



        if claim_count == 0:

            return



        with session_calendar_mutex(session_id) as acquired:

            if not acquired:

                print(f"Update worker {worker_attempt_id} could not acquire lock for session {session_id}. Aborting.")

                return



            # Reload fresh committed state from PostgreSQL after acquiring advisory lock

            session = bg_db.query(models.StudySession).filter(models.StudySession.id == session_id).first()

            if not session:

                return



            if session.calendar_sync_attempt_id != worker_attempt_id:

                print(f"Update worker {worker_attempt_id} lost claim while waiting for lock on session {session_id}. Aborting.")

                return



            target_owner_id = session.calendar_owner_id or session.created_by

            creds = get_valid_google_credentials(target_owner_id, bg_db) if target_owner_id else None



            if not creds:

                bg_db.query(models.StudySession).filter(

                    models.StudySession.id == session_id,

                    models.StudySession.calendar_sync_attempt_id == worker_attempt_id

                ).update({

                    "calendar_sync_status": "failed",

                    "calendar_sync_error": "Session creator's Google Calendar is disconnected. Update cannot be performed.",

                    "calendar_sync_attempt_id": None

                }, synchronize_session=False)

                bg_db.commit()

                return



            title = session.title

            description = session.description

            start_time = session.start_time

            end_time = session.end_time

            group_name = session.group.name if session.group else None

            google_event_id = session.google_event_id



            if google_event_id:

                success = update_google_calendar_event(

                    creds=creds,

                    event_id=google_event_id,

                    title=title,

                    description=description,

                    start_time=start_time,

                    end_time=end_time,

                    group_name=group_name

                )

                if success:

                    fenced_count = bg_db.query(models.StudySession).filter(

                        models.StudySession.id == session_id,

                        models.StudySession.calendar_sync_attempt_id == worker_attempt_id

                    ).update({

                        "calendar_sync_status": "synced",

                        "calendar_sync_error": None,

                        "calendar_synced_at": datetime.now(timezone.utc),

                        "calendar_sync_attempt_id": None

                    }, synchronize_session=False)



                    if fenced_count > 0:

                        log_entry = models.CalendarSyncLog(

                            user_id=user_id,

                            session_id=session.id,

                            calendar_owner_id=target_owner_id,

                            session_title=session.title,

                            google_event_id=session.google_event_id,

                            operation="update",

                            status="success"

                        )

                        bg_db.add(log_entry)

                        bg_db.commit()

                    else:

                        print(f"Worker {worker_attempt_id} lost fencing after updating Google Calendar. Reconciling.")

                        bg_db.rollback()

                        reconcile_stale_external_operation(session_id, user_id)

                        return

                else:

                    fenced_count = bg_db.query(models.StudySession).filter(

                        models.StudySession.id == session_id,

                        models.StudySession.calendar_sync_attempt_id == worker_attempt_id

                    ).update({

                        "calendar_sync_status": "failed",

                        "calendar_sync_error": "Failed to update Google Calendar event.",

                        "calendar_sync_attempt_id": None

                    }, synchronize_session=False)



                    if fenced_count > 0:

                        log_entry = models.CalendarSyncLog(

                            user_id=user_id,

                            session_id=session.id,

                            calendar_owner_id=target_owner_id,

                            session_title=session.title,

                            google_event_id=session.google_event_id,

                            operation="update",

                            status="failed",

                            error="Failed to update Google Calendar event."

                        )

                        bg_db.add(log_entry)

                        bg_db.commit()

                    else:

                        bg_db.rollback()

            else:

                # Session had no event before; create one now with deterministic ID and version

                event_version = session.calendar_event_version or 1

                deterministic_id = generate_deterministic_event_id(session.id, event_version)

                try:

                    new_event_id = create_google_calendar_event(

                        creds=creds,

                        title=session.title,

                        description=session.description,

                        start_time=session.start_time,

                        end_time=session.end_time,

                        group_name=session.group.name if session.group else None,

                        event_id=deterministic_id,

                        session_id=session.id

                    )

                except EventCancelledOnGoogleError as cancel_err:

                    print(f"Session {session_id} event was cancelled on Google Calendar during update: {cancel_err}.")

                    bg_db.query(models.StudySession).filter(

                        models.StudySession.id == session_id,

                        models.StudySession.calendar_sync_attempt_id == worker_attempt_id

                    ).update({

                        "calendar_event_version": models.StudySession.calendar_event_version + 1,

                        "calendar_sync_status": "failed",

                        "calendar_sync_error": "Previous calendar event was deleted on Google Calendar. Retrying will create a fresh event.",

                        "calendar_sync_attempt_id": None

                    }, synchronize_session=False)

                    bg_db.commit()

                    return



                if new_event_id:

                    fenced_count = bg_db.query(models.StudySession).filter(

                        models.StudySession.id == session_id,

                        models.StudySession.calendar_sync_attempt_id == worker_attempt_id

                    ).update({

                        "google_event_id": new_event_id,

                        "calendar_id": "primary",

                        "calendar_owner_id": target_owner_id,

                        "calendar_sync_status": "synced",

                        "calendar_sync_error": None,

                        "calendar_synced_at": datetime.now(timezone.utc),

                        "calendar_sync_attempt_id": None

                    }, synchronize_session=False)



                    if fenced_count > 0:

                        log_entry = models.CalendarSyncLog(

                            user_id=user_id,

                            session_id=session.id,

                            calendar_owner_id=target_owner_id,

                            session_title=session.title,

                            google_event_id=new_event_id,

                            operation="create",

                            status="success"

                        )

                        bg_db.add(log_entry)

                        bg_db.commit()

                    else:

                        print(f"Worker {worker_attempt_id} lost fencing after creating Google Calendar event during update. Reconciling.")

                        bg_db.rollback()

                        reconcile_stale_external_operation(session_id, user_id)

                        return

                else:

                    fenced_count = bg_db.query(models.StudySession).filter(

                        models.StudySession.id == session_id,

                        models.StudySession.calendar_sync_attempt_id == worker_attempt_id

                    ).update({

                        "calendar_sync_status": "failed",

                        "calendar_sync_error": "Failed to create Google Calendar event during update.",

                        "calendar_sync_attempt_id": None

                    }, synchronize_session=False)

                    if fenced_count > 0:

                        bg_db.commit()

                    else:

                        bg_db.rollback()

    except Exception as e:

        print(f"Background update sync exception: {type(e).__name__}: {str(e)}")

        try:

            bg_db.query(models.StudySession).filter(

                models.StudySession.id == session_id,

                models.StudySession.calendar_sync_attempt_id == worker_attempt_id

            ).update({

                "calendar_sync_status": "failed",

                "calendar_sync_error": f"Update error: {type(e).__name__}",

                "calendar_sync_attempt_id": None

            }, synchronize_session=False)

            bg_db.commit()

        except Exception:

            pass

    finally:

        bg_db.close()





def bg_sync_delete_calendar_event(

    log_id: int,

    google_event_id: Optional[str],

    calendar_owner_id: Optional[int],

    session_title: Optional[str],

    session_id: Optional[int] = None

):

    """

    Background worker to delete an event from Google Calendar after session deletion.

    Tracks success or failure in calendar_sync_logs.

    Uses calendar_owner_id credentials; never falls back to another user's primary calendar.

    Serialized per session using PostgreSQL advisory locking.

    """

    bg_db = SessionLocal()

    try:

        log_entry = bg_db.query(models.CalendarSyncLog).filter(models.CalendarSyncLog.id == log_id).first()



        if not google_event_id:

            return



        target_sid = session_id or (log_entry.session_id if log_entry else None)



        def _execute_delete():

            creds = get_valid_google_credentials(calendar_owner_id, bg_db) if calendar_owner_id else None

            if not creds:

                if log_entry:

                    log_entry.status = "failed"

                    log_entry.error = "Calendar owner's Google Calendar is not connected. Event deletion could not be performed."

                    bg_db.commit()

                return



            success = delete_google_calendar_event(creds, google_event_id)

            if log_entry:

                if success:

                    log_entry.status = "success"

                    log_entry.error = None

                else:

                    log_entry.status = "failed"

                    log_entry.error = "Failed to delete Google Calendar event."

                bg_db.commit()



        if target_sid:

            with session_calendar_mutex(target_sid) as acquired:

                _execute_delete()

        else:

            _execute_delete()

    except Exception as e:

        print(f"Background delete sync exception: {type(e).__name__}: {str(e)}")

        try:

            log_entry = bg_db.query(models.CalendarSyncLog).filter(models.CalendarSyncLog.id == log_id).first()

            if log_entry:

                log_entry.status = "failed"

                log_entry.error = f"Delete error: {type(e).__name__}"

                bg_db.commit()

        except Exception:

            pass

    finally:

        bg_db.close()





@app.post("/api/groups")

def create_group(

    group: GroupCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    new_group = models.Group(    

        name=group.name,    

        subject=group.subject,

        description=group.description

    )

    db.add(new_group)

    db.commit()

    db.refresh(new_group)



    # Record the authenticated creator as owner in group_members

    owner_member = models.GroupMember(

        group_id=new_group.id,

        user_id=current_user.id,

        role="owner"

    )

    db.add(owner_member)

    db.commit()



    return {

        "message": "Study group created successfully!",

        "group": {

            "id": new_group.id,

            "name": new_group.name,

            "subject": new_group.subject,

            "description": new_group.description,

            "member_count": 1,

            "members_count": 1,

            "task_count": 0,

            "tasks_count": 0,

            "session_count": 0,

            "sessions_count": 0

        }

    }





@app.get("/api/groups")

def get_groups(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    # Only return groups that the logged-in user belongs to

    memberships = db.query(models.GroupMember).filter(

        models.GroupMember.user_id == current_user.id

    ).all()



    user_group_ids = [m.group_id for m in memberships]



    if not user_group_ids:

        return {

            "message": "Groups fetched successfully!",

            "count": 0,

            "groups": []

        }



    groups = db.query(models.Group).filter(models.Group.id.in_(user_group_ids)).all()



    group_list = []

    now = datetime.now(timezone.utc)

    for group in groups:

        m_count = db.query(models.GroupMember).filter(models.GroupMember.group_id == group.id).count()

        t_count = db.query(models.Task).filter(models.Task.group_id == group.id).count()

        s_count = db.query(models.StudySession).filter(

            models.StudySession.group_id == group.id,

            models.StudySession.end_time >= now

        ).count()

        p_task_count = db.query(models.Task).filter(models.Task.group_id == group.id, models.Task.status.in_(["pending", "in_progress"])).count()



        member_previews = []

        if group.members:

            for m in group.members:

                if m.user:

                    member_previews.append({

                        "id": m.user.id,

                        "name": m.user.name,

                        "role": m.role or "member"

                    })



        group_data = {

            "id": group.id,

            "name": group.name,

            "subject": group.subject or "",

            "description": group.description,

            "member_count": m_count,

            "members_count": m_count,

            "task_count": t_count,

            "tasks_count": t_count,

            "pending_task_count": p_task_count,

            "session_count": s_count,

            "sessions_count": s_count,

            "members": member_previews

        }

        group_list.append(group_data)



    return {

        "message": "Groups fetched successfully!",

        "count": len(group_list),

        "groups": group_list

    }





@app.get("/api/groups/{group_id}")

def get_group(

    group_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    group = db.query(models.Group).filter(models.Group.id == group_id).first()



    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    # Membership authorization: only members of this group may access its details

    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()



    if not membership:

        raise HTTPException(

            status_code=403,

            detail="Access denied. You are not a member of this study group."

        )



    now = datetime.now(timezone.utc)



    m_count = db.query(models.GroupMember).filter(models.GroupMember.group_id == group.id).count()

    t_count = db.query(models.Task).filter(models.Task.group_id == group.id).count()



    # Query upcoming sessions ordered chronologically (ongoing and future: end_time >= now)

    upcoming_sessions = db.query(models.StudySession).filter(

        models.StudySession.group_id == group.id,

        models.StudySession.end_time >= now

    ).order_by(models.StudySession.start_time.asc()).all()

    sessions_data = [serialize_session(s) for s in upcoming_sessions]

    s_count = len(sessions_data)



    members_data = []

    if group.members:

        for m in group.members:

            if m.user:

                members_data.append({

                    "id": m.user.id,

                    "name": m.user.name,

                    "role": m.role or "member",

                    "joined_at": m.joined_at.strftime("%b %d, %Y") if hasattr(m.joined_at, "strftime") else str(m.joined_at)

                })



    # Fetch and serialize group tasks

    tasks = db.query(models.Task).filter(

        models.Task.group_id == group.id

    ).order_by(models.Task.id.desc()).all()

    tasks_data = [serialize_task(t) for t in tasks]

    task_stats = get_group_task_stats(db, group.id)



    return {

        "message": "Group fetched successfully!",

        "group": {

            "id": group.id,

            "name": group.name,

            "subject": group.subject or "",

            "description": group.description,

            "member_count": m_count,

            "members_count": m_count,

            "task_count": t_count,

            "tasks_count": t_count,

            "session_count": s_count,

            "sessions_count": s_count,

            "members": members_data,

            "sessions": sessions_data,

            "tasks": tasks_data,

            "task_stats": task_stats

        }

    }





@app.put("/api/groups/{group_id}")

def update_group(

    group_id: int,

    group: GroupCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    existing_group = db.query(models.Group).filter(

        models.Group.id == group_id

    ).first()



    if not existing_group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()



    if not membership or membership.role != "owner":

        raise HTTPException(status_code=403, detail="Only the group owner can update this study group.")



    existing_group.name = group.name

    existing_group.subject = group.subject

    existing_group.description = group.description



    db.commit()

    db.refresh(existing_group)



    return {

        "message": "Group updated successfully!",

        "group": {

            "id": existing_group.id,

            "name": existing_group.name,

            "subject": existing_group.subject or "",

            "description": existing_group.description

        }

    }





@app.delete("/api/groups/{group_id}")

def delete_group(

    group_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    existing_group = db.query(models.Group).filter(

        models.Group.id == group_id

    ).first()



    if not existing_group:

        raise HTTPException(status_code=404, detail="Group not found")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()



    has_any_members = db.query(models.GroupMember).filter(models.GroupMember.group_id == group_id).count() > 0



    if has_any_members and (not membership or membership.role != "owner"):

        raise HTTPException(status_code=403, detail="Only the group owner can delete this study group.")



    # Delete related records first to respect foreign key constraints

    db.query(models.Invitation).filter(models.Invitation.group_id == group_id).delete()

    db.query(models.GroupMember).filter(models.GroupMember.group_id == group_id).delete()

    db.query(models.Task).filter(models.Task.group_id == group_id).delete()

    db.query(models.StudySession).filter(models.StudySession.group_id == group_id).delete()



    db.delete(existing_group)

    db.commit()



    return {

        "message": "Group deleted successfully!"

    }





# ── Group Membership & Invitations Endpoints ──



@app.post("/api/groups/{group_id}/invitations")

def create_invitation(

    group_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()



    if not membership:

        raise HTTPException(

            status_code=403,

            detail="Access denied. You must be a member of this study group to generate an invitation code."

        )



    now = datetime.now(timezone.utc)



    # Check if an active invitation already exists

    active_inv = db.query(models.Invitation).filter(

        models.Invitation.group_id == group_id,

        models.Invitation.expires_at > now

    ).first()



    if active_inv:

        return {

            "success": True,

            "message": "Active invitation retrieved successfully!",

            "invite_code": active_inv.invite_code,

            "expires_at": active_inv.expires_at.isoformat()

        }



    # Generate unique code

    code = generate_invite_code()

    for _ in range(5):

        exists = db.query(models.Invitation).filter(models.Invitation.invite_code == code).first()

        if not exists:

            break

        code = generate_invite_code()



    expires_at = now + timedelta(days=7)

    invitation = models.Invitation(

        group_id=group_id,

        created_by=current_user.id if hasattr(current_user, "id") else None,

        invite_code=code,

        expires_at=expires_at

    )

    db.add(invitation)

    db.commit()

    db.refresh(invitation)



    return {

        "success": True,

        "message": "Invitation code generated successfully!",

        "invite_code": invitation.invite_code,

        "expires_at": invitation.expires_at.isoformat()

    }





@app.post("/api/groups/join")

def join_group(

    data: JoinGroupRequest,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    code = data.invite_code.strip().upper()

    if not code:

        raise HTTPException(status_code=400, detail="Invitation code is required.")



    invitation = db.query(models.Invitation).filter(

        models.Invitation.invite_code == code

    ).first()



    if not invitation:

        raise HTTPException(status_code=404, detail="Invalid invitation code. Please check and try again.")



    now = datetime.now(timezone.utc)

    if invitation.expires_at and invitation.expires_at < now:

        raise HTTPException(status_code=400, detail="This invitation code has expired. Please request a new one.")



    group = db.query(models.Group).filter(models.Group.id == invitation.group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="The study group associated with this code no longer exists.")



    # Check if user is already a member

    existing_member = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group.id,

        models.GroupMember.user_id == current_user.id

    ).first()



    if existing_member:

        return {

            "success": False,

            "already_member": True,

            "message": f"You are already a member of {group.name}!",

            "group": {

                "id": group.id,

                "name": group.name

            }

        }



    # Add user to group_members with role "member"

    new_member = models.GroupMember(

        group_id=group.id,

        user_id=current_user.id,

        role="member"

    )

    db.add(new_member)

    db.commit()



    return {

        "success": True,

        "message": f"Welcome to {group.name}! You have joined successfully.",

        "group": {

            "id": group.id,

            "name": group.name,

            "subject": group.subject or ""

        }

    }





@app.get("/api/groups/{group_id}/members")

def get_group_members(

    group_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()



    if not membership:

        raise HTTPException(

            status_code=403,

            detail="Access denied. You must be a member of this study group to view its members."

        )



    members = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id

    ).order_by(models.GroupMember.joined_at.asc()).all()



    members_list = []

    for m in members:

        user = m.user

        if not user:

            continue

        members_list.append({

            "id": user.id,

            "name": user.name,

            "role": m.role or "member",

            "joined_at": m.joined_at.strftime("%b %d, %Y") if hasattr(m.joined_at, "strftime") else str(m.joined_at)

        })



    return {

        "message": "Group members fetched successfully!",

        "count": len(members_list),

        "members": members_list

    }





# ── Group Tasks Endpoints ──



@app.get("/api/groups/{group_id}/tasks")

def get_group_tasks(

    group_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()



    if not membership:

        raise HTTPException(status_code=403, detail="Access denied. You must be a member of this study group to view tasks.")



    tasks = db.query(models.Task).filter(

        models.Task.group_id == group_id

    ).order_by(models.Task.id.desc()).all()



    stats = get_group_task_stats(db, group_id)



    return {

        "success": True,

        "tasks": [serialize_task(t) for t in tasks],

        "stats": stats

    }





@app.post("/api/groups/{group_id}/tasks")

def create_task(

    group_id: int,

    task_data: TaskCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()



    if not membership:

        raise HTTPException(status_code=403, detail="Access denied. You must be a member of this study group to create tasks.")



    title = task_data.title.strip()

    if not title:

        raise HTTPException(status_code=400, detail="Task title is required.")



    # Validate assigned_to belongs to this group

    assigned_to = task_data.assigned_to

    if assigned_to:

        assignee_membership = db.query(models.GroupMember).filter(

            models.GroupMember.group_id == group_id,

            models.GroupMember.user_id == assigned_to

        ).first()

        if not assignee_membership:

            raise HTTPException(status_code=400, detail="The assigned user is not a member of this study group.")



    valid_statuses = {"pending", "in_progress", "completed"}

    status = (task_data.status or "pending").lower().strip()

    if status not in valid_statuses:

        status = "pending"



    due_dt = parse_due_date(task_data.due_date)



    new_task = models.Task(

        group_id=group_id,

        assigned_to=assigned_to,

        title=title,

        description=(task_data.description or "").strip(),

        due_date=due_dt,

        status=status

    )

    db.add(new_task)

    db.commit()

    db.refresh(new_task)



    stats = get_group_task_stats(db, group_id)



    return {

        "success": True,

        "message": "Task created successfully!",

        "task": serialize_task(new_task),

        "stats": stats

    }





@app.put("/api/groups/{group_id}/tasks/{task_id}")

def update_task(

    group_id: int,

    task_id: int,

    task_data: TaskCreate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()



    if not membership:

        raise HTTPException(status_code=403, detail="Access denied. You must be a member of this study group to edit tasks.")



    task = db.query(models.Task).filter(

        models.Task.id == task_id,

        models.Task.group_id == group_id

    ).first()



    if not task:

        raise HTTPException(status_code=404, detail="Task not found in this study group.")



    title = task_data.title.strip()

    if not title:

        raise HTTPException(status_code=400, detail="Task title is required.")



    assigned_to = task_data.assigned_to

    if assigned_to:

        assignee_membership = db.query(models.GroupMember).filter(

            models.GroupMember.group_id == group_id,

            models.GroupMember.user_id == assigned_to

        ).first()

        if not assignee_membership:

            raise HTTPException(status_code=400, detail="The assigned user is not a member of this study group.")



    valid_statuses = {"pending", "in_progress", "completed"}

    status = (task_data.status or "pending").lower().strip()

    if status not in valid_statuses:

        status = "pending"



    due_dt = parse_due_date(task_data.due_date)



    task.title = title

    task.description = (task_data.description or "").strip()

    task.assigned_to = assigned_to

    task.due_date = due_dt

    task.status = status



    db.commit()

    db.refresh(task)



    stats = get_group_task_stats(db, group_id)



    return {

        "success": True,

        "message": "Task updated successfully!",

        "task": serialize_task(task),

        "stats": stats

    }





@app.patch("/api/groups/{group_id}/tasks/{task_id}/status")

def update_task_status(

    group_id: int,

    task_id: int,

    status_data: TaskStatusUpdate,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()



    if not membership:

        raise HTTPException(status_code=403, detail="Access denied. You must be a member of this study group to update tasks.")



    task = db.query(models.Task).filter(

        models.Task.id == task_id,

        models.Task.group_id == group_id

    ).first()



    if not task:

        raise HTTPException(status_code=404, detail="Task not found in this study group.")



    new_status = status_data.status.lower().strip()

    valid_statuses = {"pending", "in_progress", "completed"}

    if new_status not in valid_statuses:

        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")



    task.status = new_status

    db.commit()

    db.refresh(task)



    stats = get_group_task_stats(db, group_id)



    return {

        "success": True,

        "message": f"Task status updated to {new_status.replace('_', ' ').title()}.",

        "task": serialize_task(task),

        "stats": stats

    }





@app.delete("/api/groups/{group_id}/tasks/{task_id}")

def delete_task(

    group_id: int,

    task_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()



    if not membership:

        raise HTTPException(status_code=403, detail="Access denied. You must be a member of this study group to delete tasks.")



    task = db.query(models.Task).filter(

        models.Task.id == task_id,

        models.Task.group_id == group_id

    ).first()



    if not task:

        raise HTTPException(status_code=404, detail="Task not found in this study group.")



    db.delete(task)

    db.commit()



    stats = get_group_task_stats(db, group_id)



    return {

        "success": True,

        "message": "Task deleted successfully!",

        "stats": stats

    }





# ── Study Sessions Endpoints ──



@app.post("/api/groups/{group_id}/sessions")

def create_session(

    group_id: int,

    session_data: SessionCreate,

    background_tasks: BackgroundTasks,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    # 1. Verify user membership in this group

    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()

    if not membership:

        raise HTTPException(status_code=403, detail="Access denied. You are not a member of this study group.")



    # 2. Validate input fields

    title = session_data.title.strip()

    if not title:

        raise HTTPException(status_code=400, detail="Session title is required.")

    if len(title) > 150:

        raise HTTPException(status_code=400, detail="Session title must not exceed 150 characters.")



    # 3. Validate start and end times

    if session_data.end_time <= session_data.start_time:

        raise HTTPException(status_code=400, detail="End time must be later than start time.")



    # 4. Check Google Calendar connection

    has_creds = bool(get_valid_google_credentials(current_user.id, db))

    initial_sync_status = "pending" if has_creds else "not_connected"

    now_utc = datetime.now(timezone.utc)



    # 5. Persist the session in PostgreSQL immediately with calendar_owner_id

    new_session = models.StudySession(

        group_id=group_id,

        created_by=current_user.id,

        calendar_owner_id=current_user.id if has_creds else None,

        title=title,

        description=session_data.description.strip() if session_data.description else None,

        start_time=session_data.start_time,

        end_time=session_data.end_time,

        google_event_id=None,

        calendar_id="primary" if initial_sync_status == "pending" else None,

        calendar_sync_status=initial_sync_status,

        calendar_sync_started_at=now_utc if initial_sync_status == "pending" else None,

        calendar_sync_attempt_id=None,

        calendar_event_version=1,

        calendar_sync_error=None

    )



    db.add(new_session)

    db.commit()

    db.refresh(new_session)



    # 6. Schedule background creation if connected

    if initial_sync_status == "pending":

        background_tasks.add_task(bg_sync_create_calendar_event, new_session.id, current_user.id)



    msg = "Study session scheduled successfully!"

    if initial_sync_status == "pending":

        msg += " Synced with Google Calendar 📅 (queued)"



    return {

        "success": True,

        "message": msg,

        "session": serialize_session(new_session)

    }





@app.get("/api/groups/{group_id}/sessions")

def get_group_sessions(

    group_id: int,

    upcoming_only: bool = False,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()

    if not membership:

        raise HTTPException(status_code=403, detail="Access denied. You are not a member of this study group.")



    query = db.query(models.StudySession).filter(

        models.StudySession.group_id == group_id

    )

    if upcoming_only:

        now = datetime.now(timezone.utc)

        query = query.filter(models.StudySession.end_time >= now)



    sessions = query.order_by(models.StudySession.start_time.asc()).all()



    return {

        "success": True,

        "group_id": group_id,

        "count": len(sessions),

        "sessions": [serialize_session(s) for s in sessions]

    }





@app.get("/api/sessions")
def get_user_upcoming_sessions(
    filter: Optional[str] = "upcoming",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns study sessions for the authenticated user across their groups.
    Supports filtering by 'upcoming' (default), 'past', or 'all'.
    """
    memberships = db.query(models.GroupMember).filter(
        models.GroupMember.user_id == current_user.id
    ).all()

    user_group_ids = [m.group_id for m in memberships]
    if not user_group_ids:
        return {
            "success": True,
            "count": 0,
            "sessions": []
        }

    now = datetime.now(timezone.utc)
    query = db.query(models.StudySession).filter(
        models.StudySession.group_id.in_(user_group_ids)
    )

    filter_mode = (filter or "upcoming").lower()
    if filter_mode == "past":
        query = query.filter(models.StudySession.end_time < now).order_by(models.StudySession.start_time.desc())
    elif filter_mode == "all":
        query = query.order_by(models.StudySession.start_time.desc())
    else:  # upcoming
        query = query.filter(models.StudySession.end_time >= now).order_by(models.StudySession.start_time.asc())

    sessions = query.all()

    return {
        "success": True,
        "count": len(sessions),
        "sessions": [serialize_session(s) for s in sessions]
    }


@app.get("/api/tasks")
def get_user_tasks(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns tasks accessible to the authenticated user across all groups they belong to.
    Supports optional status filtering: 'pending', 'in_progress', 'completed', or 'all'.
    """
    memberships = db.query(models.GroupMember).filter(
        models.GroupMember.user_id == current_user.id
    ).all()

    user_group_ids = [m.group_id for m in memberships]
    if not user_group_ids:
        return {
            "success": True,
            "count": 0,
            "tasks": []
        }

    query = db.query(models.Task).filter(models.Task.group_id.in_(user_group_ids))
    if status and status.lower() != "all":
        query = query.filter(models.Task.status == status.lower())

    tasks = query.order_by(models.Task.due_date.asc().nulls_last(), models.Task.id.desc()).all()

    groups = {g.id: g.name for g in db.query(models.Group).filter(models.Group.id.in_(user_group_ids)).all()}

    task_list = []
    for t in tasks:
        item = serialize_task(t)
        item["group_name"] = groups.get(t.group_id, "Study Group")
        task_list.append(item)

    return {
        "success": True,
        "count": len(task_list),
        "tasks": task_list
    }


@app.get("/api/users/me")
def get_user_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns profile information for the authenticated user and account metadata for the Settings view.
    """
    memberships_count = db.query(models.GroupMember).filter(
        models.GroupMember.user_id == current_user.id
    ).count()

    google_credential = db.query(models.GoogleCredential).filter(
        models.GoogleCredential.user_id == current_user.id
    ).first()

    return {
        "success": True,
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "groups_count": memberships_count,
        "calendar_connected": bool(google_credential and google_credential.access_token)
    }

class UserProfileUpdate(BaseModel):
    name: str


@app.put("/api/users/me")
@app.patch("/api/users/me")
def update_user_profile(
    update_data: UserProfileUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the authenticated user's profile information (name).
    """
    new_name = update_data.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")
    if len(new_name) > 100:
        raise HTTPException(status_code=400, detail="Name must be 100 characters or fewer.")

    current_user.name = new_name
    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "message": "Name updated successfully!",
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email
        }
    }


@app.put("/api/groups/{group_id}/sessions/{session_id}")

def update_session(

    group_id: int,

    session_id: int,

    update_data: SessionUpdate,

    background_tasks: BackgroundTasks,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    # 1. Group verification

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    # 2. Session verification and group match

    session = db.query(models.StudySession).filter(

        models.StudySession.id == session_id,

        models.StudySession.group_id == group_id

    ).first()

    if not session:

        raise HTTPException(status_code=404, detail="Study session not found in this group.")



    # 3. Authorization check: creator OR group owner

    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()

    if not membership:

        raise HTTPException(status_code=403, detail="Access denied. You are not a member of this study group.")



    is_creator = (session.created_by == current_user.id)

    is_owner = (membership.role == "owner")

    if not (is_creator or is_owner):

        raise HTTPException(status_code=403, detail="Permission denied. Only the session creator or group owner can edit this session.")



    # 4. Input validation

    title = update_data.title.strip()

    if not title:

        raise HTTPException(status_code=400, detail="Session title is required.")

    if len(title) > 150:

        raise HTTPException(status_code=400, detail="Session title must not exceed 150 characters.")



    if update_data.end_time <= update_data.start_time:

        raise HTTPException(status_code=400, detail="End time must be later than start time.")



    # 5. Check original calendar owner connection (F-03: never fall back to updater on primary calendar)

    target_owner_id = session.calendar_owner_id or session.created_by

    has_creds = bool(get_valid_google_credentials(target_owner_id, db)) if target_owner_id else False



    if has_creds:

        session.calendar_sync_status = "pending"

        session.calendar_sync_started_at = datetime.now(timezone.utc)

        session.calendar_sync_attempt_id = None

        session.calendar_sync_error = None

        background_tasks.add_task(bg_sync_update_calendar_event, session.id, current_user.id)

    else:

        session.calendar_sync_attempt_id = None

        if session.google_event_id:

            # Event exists on Google Calendar but owner's credentials are unavailable

            session.calendar_sync_status = "failed"

            session.calendar_sync_error = "Session creator's Google Calendar is disconnected. Cannot update Google Calendar event."

        else:

            session.calendar_sync_status = "not_connected"



    # 6. Database update

    session.title = title

    session.description = update_data.description.strip() if update_data.description else None

    session.start_time = update_data.start_time

    session.end_time = update_data.end_time

    session.updated_at = datetime.now(timezone.utc)



    db.commit()

    db.refresh(session)



    msg = "Study session updated successfully!"

    if session.calendar_sync_status == "pending":

        msg += " Google Calendar event updated 📅 (sync queued)"



    return {

        "success": True,

        "message": msg,

        "calendar_sync_status": session.calendar_sync_status,

        "session": serialize_session(session)

    }





@app.delete("/api/groups/{group_id}/sessions/{session_id}")

def delete_session(

    group_id: int,

    session_id: int,

    background_tasks: BackgroundTasks,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    # 1. Group verification

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    # 2. Session verification and group match

    session = db.query(models.StudySession).filter(

        models.StudySession.id == session_id,

        models.StudySession.group_id == group_id

    ).first()

    if not session:

        raise HTTPException(status_code=404, detail="Study session not found in this group.")



    # 3. Authorization check: creator OR group owner

    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()

    if not membership:

        raise HTTPException(status_code=403, detail="Access denied. You are not a member of this study group.")



    is_creator = (session.created_by == current_user.id)

    is_owner = (membership.role == "owner")

    if not (is_creator or is_owner):

        raise HTTPException(status_code=403, detail="Permission denied. Only the session creator or group owner can cancel this session.")



    session_title = session.title

    had_google_event = bool(session.google_event_id)

    google_event_id = session.google_event_id

    calendar_owner_id = session.calendar_owner_id or session.created_by

    is_sync_pending = session.calendar_sync_status in ("pending", "syncing")



    # F-04: Queue deletion if event exists OR if creation is currently in-flight

    should_queue_delete = had_google_event or is_sync_pending



    if should_queue_delete:

        log_entry = models.CalendarSyncLog(

            user_id=current_user.id,

            session_id=session.id,

            calendar_owner_id=calendar_owner_id,

            session_title=session_title,

            google_event_id=google_event_id,

            operation="delete",

            status="pending"

        )

        db.add(log_entry)

        db.commit()

        db.refresh(log_entry)



        if had_google_event:

            background_tasks.add_task(

                bg_sync_delete_calendar_event,

                log_entry.id,

                google_event_id,

                calendar_owner_id,

                session_title,

                session.id

            )



    # 5. Remove session from PostgreSQL immediately

    db.delete(session)

    db.commit()



    # Calculate remaining upcoming sessions count for this group

    now = datetime.now(timezone.utc)

    remaining_count = db.query(models.StudySession).filter(

        models.StudySession.group_id == group_id,

        models.StudySession.end_time >= now

    ).count()



    msg = f"Study session '{session_title}' canceled successfully!"

    if should_queue_delete:

        msg += " Google Calendar event removed 🗑️ (deletion scheduled)"



    return {

        "success": True,

        "message": msg,

        "session_id": session_id,

        "group_id": group_id,

        "calendar_deleted": False,

        "calendar_delete_queued": should_queue_delete,

        "calendar_sync_status": "delete_pending" if should_queue_delete else "not_synced",

        "remaining_sessions_count": remaining_count

    }





# ── Step 5C: Manual Retry & Status Endpoints ──



@app.post("/api/groups/{group_id}/sessions/{session_id}/sync")

def retry_session_sync(

    group_id: int,

    session_id: int,

    background_tasks: BackgroundTasks,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    """

    Manually retries synchronization of a study session with Google Calendar.

    Enforces F-01 (atomic claim), F-02 (stale operation recovery), and F-03 (ownership enforcement).

    """

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    session = db.query(models.StudySession).filter(

        models.StudySession.id == session_id,

        models.StudySession.group_id == group_id

    ).first()

    if not session:

        raise HTTPException(status_code=404, detail="Study session not found in this group.")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()

    if not membership:

        raise HTTPException(status_code=403, detail="Access denied. You are not a member of this study group.")



    is_creator = (session.created_by == current_user.id)

    is_owner = (membership.role == "owner")

    if not (is_creator or is_owner):

        raise HTTPException(status_code=403, detail="Permission denied. Only the session creator or group owner can synchronize this session.")



    # F-03: Verify Google Calendar connection for original calendar owner

    target_owner_id = session.calendar_owner_id or session.created_by or current_user.id

    creds = get_valid_google_credentials(target_owner_id, db)

    if not creds:

        owner_text = "Your" if target_owner_id == current_user.id else "The original session creator's"

        raise HTTPException(

            status_code=400,

            detail=f"{owner_text} Google Calendar is not connected. Reconnection is required."

        )



    # If already synced, return success without re-creating

    if session.calendar_sync_status == "synced" and session.google_event_id:

        return {

            "success": True,

            "message": "Study session is already synchronized with Google Calendar.",

            "session": serialize_session(session)

        }



    # F-02: Check for active operation vs stale operation (> 5 minutes)

    now = datetime.now(timezone.utc)

    sync_started = session.calendar_sync_started_at or session.updated_at

    is_stale = (

        sync_started is not None and

        (now - (sync_started.replace(tzinfo=timezone.utc) if sync_started.tzinfo is None else sync_started)) > timedelta(minutes=5)

    )



    if session.calendar_sync_status in ("pending", "syncing") and not is_stale:

        raise HTTPException(

            status_code=409,

            detail="Synchronization is currently in progress for this session."

        )



    # Set status to pending and schedule background task

    session.calendar_sync_status = "pending"

    session.calendar_sync_started_at = now

    session.calendar_sync_attempt_id = None

    session.calendar_sync_error = None

    if not session.calendar_owner_id:

        session.calendar_owner_id = target_owner_id



    db.commit()

    db.refresh(session)



    if session.google_event_id:

        background_tasks.add_task(bg_sync_update_calendar_event, session.id, current_user.id)

    else:

        background_tasks.add_task(bg_sync_create_calendar_event, session.id, current_user.id)



    return {

        "success": True,

        "message": "Synchronization queued ⏳",

        "session": serialize_session(session)

    }





@app.get("/api/groups/{group_id}/sessions/{session_id}/sync-status")

def get_session_sync_status(

    group_id: int,

    session_id: int,

    db: Session = Depends(get_db),

    current_user: models.User = Depends(get_current_user)

):

    """

    Returns explicit synchronization status and error details for a study session.

    """

    group = db.query(models.Group).filter(models.Group.id == group_id).first()

    if not group:

        raise HTTPException(status_code=404, detail="Study group not found.")



    session = db.query(models.StudySession).filter(

        models.StudySession.id == session_id,

        models.StudySession.group_id == group_id

    ).first()

    if not session:

        raise HTTPException(status_code=404, detail="Study session not found in this group.")



    membership = db.query(models.GroupMember).filter(

        models.GroupMember.group_id == group_id,

        models.GroupMember.user_id == current_user.id

    ).first()

    if not membership:

        raise HTTPException(status_code=403, detail="Access denied. You are not a member of this study group.")



    return {

        "success": True,

        "session_id": session.id,

        "calendar_sync_status": session.calendar_sync_status or ("synced" if session.google_event_id else "not_connected"),

        "calendar_sync_error": session.calendar_sync_error,

        "calendar_sync_started_at": session.calendar_sync_started_at.isoformat() if session.calendar_sync_started_at else None,

        "calendar_synced_at": session.calendar_synced_at.isoformat() if session.calendar_synced_at else None,

        "calendar_owner_id": session.calendar_owner_id,

        "calendar_synced": bool(session.google_event_id),

        "google_event_id": session.google_event_id

    }





# ── Authentication Endpoints ──



@app.post("/api/signup")

def signup(user_data: UserSignup, db: Session = Depends(get_db)):

    name = user_data.name.strip()

    email = user_data.email.strip().lower()

    password = user_data.password.strip()



    if not name or not email or not password:

        return {"success": False, "message": "All fields are required."}



    existing_user = db.query(models.User).filter(models.User.email == email).first()

    if existing_user:

        return {"success": False, "message": "An account with this email already exists."}



    hashed = hash_password(password)

    new_user = models.User(

        name=name,

        email=email,

        password_hash=hashed

    )



    db.add(new_user)

    db.commit()

    db.refresh(new_user)



    token = create_access_token(new_user.id)



    return {

        "success": True,

        "message": "Account created successfully!",

        "access_token": token,

        "user": {

            "id": new_user.id,

            "name": new_user.name,

            "email": new_user.email

        }

    }





@app.post("/api/login")

def login(credentials: UserLogin, db: Session = Depends(get_db)):

    email = credentials.email.strip().lower()

    password = credentials.password.strip()



    if not email or not password:

        return {"success": False, "message": "Email and password are required."}



    user = db.query(models.User).filter(models.User.email == email).first()

    if not user or not verify_password(password, user.password_hash):

        return {"success": False, "message": "Invalid email or password."}



    token = create_access_token(user.id)



    return {

        "success": True,

        "message": "Login successful!",

        "access_token": token,

        "user": {

            "id": user.id,

            "name": user.name,

            "email": user.email

        }

    }







@app.get("/auth/google/callback")

def google_callback(

    request: Request,

    code: Optional[str] = None,

    state: Optional[str] = None,

    db: Session = Depends(get_db)

):

    target_return_url = DEFAULT_FRONTEND_URL



    # Check whether the user cancelled authorization on Google's consent screen

    if request.query_params.get("error"):

        if state:

            remove_pkce_verifier(state)

        error_param = request.query_params.get("error", "cancelled")

        return RedirectResponse(

            url=build_frontend_redirect(

                target_return_url,

                {"calendar_status": "error", "calendar_error": f"Google authorization was not granted ({error_param})."}

            )

        )



    if not code or not state:

        if state:

            remove_pkce_verifier(state)

        return RedirectResponse(

            url=build_frontend_redirect(

                target_return_url,

                {"calendar_status": "error", "calendar_error": "Authorization code or state parameter was missing."}

            )

        )



    # Step 1: Validate OAuth state securely (distinguish SignatureExpired vs BadSignature)

    try:

        state_data = state_serializer.loads(

            state,

            salt="google-oauth-state",

            max_age=900  # 15 minutes validity

        )

        user_id = int(state_data.get("user_id"))

        if state_data.get("return_url"):

            target_return_url = state_data["return_url"]



    except SignatureExpired:

        remove_pkce_verifier(state)

        return RedirectResponse(

            url=build_frontend_redirect(

                target_return_url,

                {"calendar_status": "error", "calendar_error": "OAuth session expired. Please click Connect Google Calendar again."}

            )

        )

    except BadSignature:

        remove_pkce_verifier(state)

        return RedirectResponse(

            url=build_frontend_redirect(

                target_return_url,

                {"calendar_status": "error", "calendar_error": "Invalid OAuth state signature. Connection rejected for security."}

            )

        )

    except (KeyError, ValueError, TypeError):

        remove_pkce_verifier(state)

        return RedirectResponse(

            url=build_frontend_redirect(

                target_return_url,

                {"calendar_status": "error", "calendar_error": "Malformed OAuth state data."}

            )

        )



    # Step 2: Retrieve and validate the original PKCE code_verifier

    code_verifier = retrieve_and_remove_pkce_verifier(state, user_id)



    # Fallback to securely decrypting verifier from verified state payload if server restarted

    if not code_verifier and state_data.get("enc_verifier"):

        try:

            code_verifier = decrypt_google_token(state_data["enc_verifier"])

        except Exception:

            code_verifier = None



    if not code_verifier:

        remove_pkce_verifier(state)

        return RedirectResponse(

            url=build_frontend_redirect(

                target_return_url,

                {"calendar_status": "error", "calendar_error": "PKCE code verifier is missing or invalid. Please connect again."}

            )

        )



    # Step 3: Find the TeamSync user

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:

        remove_pkce_verifier(state)

        return RedirectResponse(

            url=build_frontend_redirect(

                target_return_url,

                {"calendar_status": "error", "calendar_error": "TeamSync user not found."}

            )

        )



    # Step 4: Exchange authorization code with Google using the restored PKCE code_verifier

    try:

        flow = Flow.from_client_config(

            {

                "web": {

                    "client_id": GOOGLE_CLIENT_ID,

                    "client_secret": GOOGLE_CLIENT_SECRET,

                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",

                    "token_uri": "https://oauth2.googleapis.com/token",

                    "redirect_uris": [GOOGLE_REDIRECT_URI]

                }

            },

            scopes=GOOGLE_SCOPES,

            state=state

        )



        flow.redirect_uri = GOOGLE_REDIRECT_URI

        flow.code_verifier = code_verifier

        flow.fetch_token(code=code)

        credentials = flow.credentials



    except Exception as error:

        remove_pkce_verifier(state)

        err_msg = str(error)

        print("Google OAuth token exchange error:", type(error).__name__, err_msg)

        if "invalid_grant" in err_msg.lower():

            friendly_err = "Authorization code was already used or expired. Please click Connect again."

        else:

            friendly_err = "Failed to exchange authorization code with Google. Please try again."



        return RedirectResponse(

            url=build_frontend_redirect(

                target_return_url,

                {"calendar_status": "error", "calendar_error": friendly_err}

            )

        )



    # Step 5: Encrypt tokens before storing in database

    try:

        encrypted_access_token = encrypt_google_token(credentials.token)

        encrypted_refresh_token = (

            encrypt_google_token(credentials.refresh_token)

            if credentials.refresh_token

            else None

        )



        google_credential = db.query(models.GoogleCredential).filter(

            models.GoogleCredential.user_id == user_id

        ).first()



        if google_credential:

            google_credential.access_token = encrypted_access_token

            if encrypted_refresh_token:

                google_credential.refresh_token = encrypted_refresh_token

            google_credential.token_expiry = credentials.expiry

            google_credential.scopes = " ".join(credentials.scopes or GOOGLE_SCOPES)

        else:

            google_credential = models.GoogleCredential(

                user_id=user_id,

                access_token=encrypted_access_token,

                refresh_token=encrypted_refresh_token,

                token_expiry=credentials.expiry,

                scopes=" ".join(credentials.scopes or GOOGLE_SCOPES)

            )

            db.add(google_credential)



        db.commit()



    except Exception as db_err:

        db.rollback()

        remove_pkce_verifier(state)

        print("Database error saving Google credentials:", type(db_err).__name__)

        return RedirectResponse(

            url=build_frontend_redirect(

                target_return_url,

                {"calendar_status": "error", "calendar_error": "Database error occurred while saving credentials."}

            )

        )



    # Step 6: Successful connection -> ensure verifier is purged & redirect to frontend

    remove_pkce_verifier(state)

    return RedirectResponse(

        url=build_frontend_redirect(

            target_return_url,

            {"calendar_status": "connected"}

        )

    )

