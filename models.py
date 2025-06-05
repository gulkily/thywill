from sqlmodel import Field, SQLModel, create_engine, Session, select
from datetime import datetime
import uuid
import secrets

class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    display_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Religious preference fields
    religious_preference: str | None = Field(default="unspecified", max_length=50)  # "christian", "unspecified"
    prayer_style: str | None = Field(default=None, max_length=100)  # e.g., "in_jesus_name", "interfaith"
    # Invite tree fields
    invited_by_user_id: str | None = Field(default=None)  # ID of the user who invited this user
    invite_token_used: str | None = Field(default=None)   # Token that was used to create this account

class Prayer(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    author_id: str
    text: str
    generated_prayer: str | None = None  # LLM-generated prayer
    project_tag: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    flagged: bool = False  # Will be deprecated after migration
    # Religious targeting fields
    target_audience: str | None = Field(default="all", max_length=50)  # "christians_only", "all"
    
    def has_attribute(self, name: str, session: Session) -> bool:
        """Check if prayer has a specific attribute"""
        stmt = select(PrayerAttribute).where(
            PrayerAttribute.prayer_id == self.id,
            PrayerAttribute.attribute_name == name
        )
        return session.exec(stmt).first() is not None
    
    def get_attribute(self, name: str, session: Session) -> str | None:
        """Get the value of a specific attribute"""
        stmt = select(PrayerAttribute).where(
            PrayerAttribute.prayer_id == self.id,
            PrayerAttribute.attribute_name == name
        )
        attr = session.exec(stmt).first()
        return attr.attribute_value if attr else None
    
    def set_attribute(self, name: str, value: str = "true", user_id: str | None = None, session: Session = None) -> None:
        """Set or update an attribute for this prayer"""
        if session is None:
            raise ValueError("Session is required for attribute operations")
            
        stmt = select(PrayerAttribute).where(
            PrayerAttribute.prayer_id == self.id,
            PrayerAttribute.attribute_name == name
        )
        existing_attr = session.exec(stmt).first()
        
        old_value = existing_attr.attribute_value if existing_attr else None
        
        if existing_attr:
            existing_attr.attribute_value = value
        else:
            new_attr = PrayerAttribute(
                prayer_id=self.id,
                attribute_name=name,
                attribute_value=value,
                created_by=user_id
            )
            session.add(new_attr)
        
        # Log the activity
        if user_id:
            activity_log = PrayerActivityLog(
                prayer_id=self.id,
                user_id=user_id,
                action=f"set_{name}",
                old_value=old_value,
                new_value=value
            )
            session.add(activity_log)
    
    def remove_attribute(self, name: str, session: Session, user_id: str | None = None) -> None:
        """Remove an attribute from this prayer"""
        stmt = select(PrayerAttribute).where(
            PrayerAttribute.prayer_id == self.id,
            PrayerAttribute.attribute_name == name
        )
        attr = session.exec(stmt).first()
        if attr:
            old_value = attr.attribute_value
            session.delete(attr)
            
            # Log the activity
            if user_id:
                activity_log = PrayerActivityLog(
                    prayer_id=self.id,
                    user_id=user_id,
                    action=f"remove_{name}",
                    old_value=old_value,
                    new_value=None
                )
                session.add(activity_log)
    
    # Convenience properties
    def is_archived(self, session: Session) -> bool:
        return self.has_attribute('archived', session)
    
    def is_answered(self, session: Session) -> bool:
        return self.has_attribute('answered', session)
    
    def is_flagged_attr(self, session: Session) -> bool:
        return self.has_attribute('flagged', session)
    
    def answer_date(self, session: Session) -> str | None:
        return self.get_attribute('answer_date', session)
    
    def answer_testimony(self, session: Session) -> str | None:
        return self.get_attribute('answer_testimony', session)

class PrayerAttribute(SQLModel, table=True):
    __tablename__ = 'prayer_attributes'
    
    id: str = Field(default_factory=lambda: secrets.token_hex(16), primary_key=True)
    prayer_id: str = Field(foreign_key="prayer.id")
    attribute_name: str = Field(max_length=50)
    attribute_value: str | None = Field(default="true", max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = Field(default=None, foreign_key="user.id")

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
    verification_code: str | None = None  # 6-digit verification code for user verification
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

class PrayerActivityLog(SQLModel, table=True):
    __tablename__ = 'prayer_activity_log'
    
    id: str = Field(default_factory=lambda: secrets.token_hex(16), primary_key=True)
    prayer_id: str = Field(foreign_key="prayer.id")
    user_id: str = Field(foreign_key="user.id")
    action: str = Field(max_length=50)  # 'archived', 'restored', 'answered', 'flagged', 'unflagged'
    old_value: str | None = Field(default=None, max_length=255)
    new_value: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class InviteToken(SQLModel, table=True):
    token: str = Field(primary_key=True)
    created_by_user: str
    used: bool = Field(default=False)
    expires_at: datetime
    used_by_user_id: str | None = Field(default=None)     # ID of user who claimed this invite

# Performance optimization: Enable WAL mode for better concurrency
engine = create_engine(
    "sqlite:///thywill.db", 
    echo=False,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

# Create all tables
SQLModel.metadata.create_all(engine)

# Enable performance optimizations
with engine.connect() as conn:
    from sqlalchemy import text
    conn.execute(text("PRAGMA journal_mode=WAL"))
    conn.execute(text("PRAGMA synchronous=NORMAL")) 
    conn.execute(text("PRAGMA cache_size=10000"))
    conn.execute(text("PRAGMA temp_store=memory"))
    conn.commit()

