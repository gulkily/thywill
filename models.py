from sqlmodel import Field, SQLModel, create_engine, Session
from datetime import datetime
import uuid

class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    display_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Prayer(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    author_id: str
    text: str
    generated_prayer: str | None = None  # LLM-generated prayer
    project_tag: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    flagged: bool = False

class PrayerMark(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    user_id: str
    prayer_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AuthenticationRequest(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    user_id: str  # User requesting authentication
    device_info: str | None = None  # Browser/device identifier
    ip_address: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime  # 7 days from creation
    status: str = "pending"  # "pending", "approved", "rejected", "expired"
    approved_by_user_id: str | None = None
    approved_at: datetime | None = None

class AuthApproval(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    auth_request_id: str
    approver_user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AuthAuditLog(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    auth_request_id: str
    action: str  # "approved", "rejected", "created", "expired"
    actor_user_id: str | None = None  # Who performed the action
    actor_type: str | None = None  # "admin", "self", "peer", "system"
    details: str | None = None  # Additional context
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SecurityLog(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    event_type: str  # "failed_login", "rate_limit", "suspicious_activity"
    user_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    details: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Session(SQLModel, table=True):
    id: str = Field(primary_key=True)          # random hex
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    # New fields for multi-device auth
    auth_request_id: str | None = None  # Link to authentication request
    device_info: str | None = None
    ip_address: str | None = None
    is_fully_authenticated: bool = Field(default=True)  # For existing sessions

class InviteToken(SQLModel, table=True):
    token: str = Field(primary_key=True)
    created_by_user: str
    used: bool = Field(default=False)
    expires_at: datetime

engine = create_engine("sqlite:///thywill.db", echo=False)
SQLModel.metadata.create_all(engine)

