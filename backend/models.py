
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


# 1. USERS TABLE
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    memberships = relationship("GroupMember", back_populates="user")
    assigned_tasks = relationship("Task", back_populates="assignee")
    created_sessions = relationship("StudySession", back_populates="creator", foreign_keys="[StudySession.created_by]")

    google_credential = relationship(
    "GoogleCredential",
    back_populates="user",
    uselist=False,
    cascade="all, delete-orphan"
)


# 2. GROUPS TABLE
class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    subject = Column(String(100), nullable=True)

    members = relationship("GroupMember", back_populates="group")
    tasks = relationship("Task", back_populates="group")
    sessions = relationship("StudySession", back_populates="group")
    invitations = relationship("Invitation", back_populates="group")


# 3. GROUP MEMBERS TABLE
class GroupMember(Base):
    __tablename__ = "group_members"

    __table_args__ = (
        UniqueConstraint("group_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="memberships")


# 4. TASKS TABLE
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), default="pending")

    group = relationship("Group", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks")


# 5. SESSIONS TABLE
class StudySession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    google_event_id = Column(String(255), nullable=True)
    calendar_id = Column(String(255), nullable=True)
    calendar_sync_status = Column(String(30), default="not_connected", nullable=False)
    calendar_sync_error = Column(Text, nullable=True)
    calendar_synced_at = Column(DateTime(timezone=True), nullable=True)
    calendar_sync_started_at = Column(DateTime(timezone=True), nullable=True)
    calendar_sync_attempt_id = Column(String(64), nullable=True)
    calendar_event_version = Column(Integer, default=1, nullable=False)
    calendar_owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    group = relationship("Group", back_populates="sessions")
    creator = relationship("User", back_populates="created_sessions", foreign_keys=[created_by])
    calendar_owner = relationship("User", foreign_keys=[calendar_owner_id])


# 6. INVITATIONS TABLE
class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    invite_code = Column(String(100), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    group = relationship("Group", back_populates="invitations")



# 7. GOOGLE CREDENTIALS TABLE
class GoogleCredential(Base):
    __tablename__ = "google_credentials"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)

    token_expiry = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    user = relationship("User", back_populates="google_credential")

# 8. CALENDAR SYNC LOGS TABLE (For tracking background sync and deletion outcomes)
class CalendarSyncLog(Base):
    __tablename__ = "calendar_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_id = Column(Integer, nullable=True)
    calendar_owner_id = Column(Integer, nullable=True)
    session_title = Column(String(150), nullable=True)
    google_event_id = Column(String(255), nullable=True)
    operation = Column(String(30), nullable=False)  # "create", "update", "delete"
    status = Column(String(30), nullable=False, default="pending")  # "pending", "success", "failed"
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
