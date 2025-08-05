from sqlmodel import Field, SQLModel, create_engine, Session, select
from datetime import datetime
import uuid
import secrets
import sys
import os

class User(SQLModel, table=True):
    display_name: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Invite tree fields
    invited_by_username: str | None = Field(default=None)  # Username of the user who invited this user
    invite_token_used: str | None = Field(default=None)   # Token that was used to create this account
    # Welcome message tracking
    welcome_message_dismissed: bool = Field(default=False)  # Whether user has dismissed the welcome message
    # Text archive tracking
    text_file_path: str | None = Field(default=None)  # Path to the text archive file containing this user's registration
    # Supporter status tracking
    is_supporter: bool = Field(default=False)  # Manual supporter flag
    supporter_since: datetime | None = Field(default=None)  # When they became a supporter
    supporter_type: str | None = Field(default=None)  # Type of supporter: 'financial', 'prayer_warrior', 'advisor', 'community_leader' (comma-separated for multiple types)
    
    def has_role(self, role_name: str, session: Session) -> bool:
        """Check if user has a specific role"""
        from sqlmodel import select
        stmt = select(UserRole).join(Role, UserRole.role_id == Role.id).where(
            UserRole.user_id == self.display_name,
            Role.name == role_name,
            (UserRole.expires_at.is_(None)) | (UserRole.expires_at > datetime.utcnow())
        )
        return session.exec(stmt).first() is not None
    
    def has_permission(self, permission: str, session: Session) -> bool:
        """Check if user has a specific permission"""
        import json
        from sqlmodel import select
        stmt = select(Role).join(UserRole, Role.id == UserRole.role_id).where(
            UserRole.user_id == self.display_name,
            (UserRole.expires_at.is_(None)) | (UserRole.expires_at > datetime.utcnow())
        )
        roles = session.exec(stmt).all()
        
        for role in roles:
            try:
                permissions = json.loads(role.permissions)
                if permission in permissions or "*" in permissions:
                    return True
            except json.JSONDecodeError:
                continue
        return False
    
    def get_roles(self, session: Session) -> list:
        """Get all active roles for this user"""
        from sqlmodel import select
        stmt = select(Role).join(UserRole, Role.id == UserRole.role_id).where(
            UserRole.user_id == self.display_name,
            (UserRole.expires_at.is_(None)) | (UserRole.expires_at > datetime.utcnow())
        )
        return list(session.exec(stmt).all())
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges - template-friendly property"""
        # For backward compatibility during migration, check both systems
        if self.display_name == "admin":
            return True
        
        # Check role-based system
        try:
            # Use the global engine variable from this module
            with Session(engine) as session:
                return self.has_role("admin", session)
        except Exception:
            # Fallback: return False for non-admin usernames
            # This property is mainly for templates, actual auth should use is_admin() function
            return False

class Role(SQLModel, table=True):
    """Roles define different permission levels in the system"""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    name: str = Field(unique=True, max_length=50)  # "admin", "moderator", "user"
    description: str | None = Field(default=None, max_length=255)
    permissions: str = Field(default="[]")  # JSON string of permissions list
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = Field(default=None, foreign_key="user.display_name")
    is_system_role: bool = Field(default=False)  # System roles cannot be deleted

class UserRole(SQLModel, table=True):
    """Many-to-many relationship between users and roles"""
    __tablename__ = "user_roles"
    
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    user_id: str = Field(foreign_key="user.display_name")
    role_id: str = Field(foreign_key="role.id")
    granted_by: str | None = Field(default=None, foreign_key="user.display_name")  # Who granted this role
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = Field(default=None)  # Optional expiration

class Prayer(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    author_username: str
    text: str
    generated_prayer: str | None = None  # LLM-generated prayer
    project_tag: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    flagged: bool = False  # Will be deprecated after migration
    # Text archive tracking
    text_file_path: str | None = Field(default=None)  # Path to the text archive file containing this prayer
    
    # Categorization fields (cache layer - populated from text archives)
    safety_score: float = Field(default=1.0)  # 0.0 (concerning) to 1.0 (safe)
    safety_flags: str = Field(default='[]')  # JSON array of safety concerns
    categorization_method: str = Field(default='default')  # 'ai_full', 'keyword_fallback', 'default_fallback'
    specificity_type: str = Field(default='unknown')  # 'specific', 'general', 'mixed', 'unknown'
    specificity_confidence: float = Field(default=0.0)  # Confidence score 0.0-1.0
    subject_category: str = Field(default='general')  # Primary subject category
    
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
    created_by: str | None = Field(default=None, foreign_key="user.display_name")
    # Text archive tracking
    text_file_path: str | None = Field(default=None)  # Path to the text archive file where this attribute change is logged

class PrayerMark(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    username: str = Field(foreign_key="user.display_name")
    prayer_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Text archive tracking
    text_file_path: str | None = Field(default=None)  # Path to the text archive file where this prayer mark is logged

class PrayerSkip(SQLModel, table=True):
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
    username: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    # New fields for multi-device auth
    auth_request_id: str | None = None  # Link to authentication request
    device_info: str | None = None
    ip_address: str | None = None
    is_fully_authenticated: bool = Field(default=True)  # For existing sessions

class NotificationState(SQLModel, table=True):
    __tablename__ = 'notification_state'
    
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    user_id: str = Field(foreign_key="user.display_name")  # User who should receive the notification
    auth_request_id: str = Field(foreign_key="authenticationrequest.id")  # Associated auth request
    notification_type: str = Field(default="auth_request", max_length=50)  # Type of notification
    is_read: bool = Field(default=False)  # Whether notification has been read
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: datetime | None = Field(default=None)  # When notification was marked as read

class PrayerActivityLog(SQLModel, table=True):
    __tablename__ = 'prayer_activity_log'
    
    id: str = Field(default_factory=lambda: secrets.token_hex(16), primary_key=True)
    prayer_id: str = Field(foreign_key="prayer.id")
    user_id: str = Field(foreign_key="user.display_name")
    action: str = Field(max_length=50)  # 'archived', 'restored', 'answered', 'flagged', 'unflagged'
    old_value: str | None = Field(default=None, max_length=255)
    new_value: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Text archive tracking
    text_file_path: str | None = Field(default=None)  # Path to the text archive file where this activity is logged

class InviteToken(SQLModel, table=True):
    token: str = Field(primary_key=True)
    created_by_user: str
    usage_count: int = Field(default=0)  # Number of times this token has been used
    max_uses: int | None = Field(default=None)  # Maximum uses allowed (null = unlimited)
    expires_at: datetime
    used_by_user_id: str | None = Field(default=None)     # ID of user who most recently claimed this invite
    token_type: str = Field(default="new_user", max_length=20)  # 'new_user' or 'multi_device'
    
    # Backward compatibility property
    @property
    def used(self) -> bool:
        """Backward compatibility: token is 'used' if it has reached max_uses"""
        if self.max_uses is None:
            return False  # Unlimited use tokens are never "used"
        return self.usage_count >= self.max_uses

class InviteTokenUsage(SQLModel, table=True):
    __tablename__ = 'invite_token_usage'
    
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    invite_token_id: str = Field(foreign_key="invitetoken.token")
    user_id: str = Field(foreign_key="user.display_name")
    claimed_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: str | None = None  # Security tracking

class ChangelogEntry(SQLModel, table=True):
    commit_id: str = Field(primary_key=True, max_length=40)
    original_message: str
    friendly_description: str | None = None
    change_type: str | None = Field(default=None, max_length=20)  # 'new', 'enhanced', 'fixed'
    commit_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Database engine configuration with intelligent path detection
def get_database_path():
    """
    Multi-layer safety approach for database path selection:
    1. Test environment detection (highest priority)
    2. Explicit DATABASE_PATH configuration
    3. Default production database path
    """
    # Safety: Detect test environment - this overrides everything else
    if ('pytest' in sys.modules or 
        'PYTEST_CURRENT_TEST' in os.environ or
        any('pytest' in arg for arg in sys.argv)):
        return ':memory:'
    
    # Explicit configuration (ignore empty strings)
    if 'DATABASE_PATH' in os.environ and os.environ['DATABASE_PATH'].strip():
        return os.environ['DATABASE_PATH']
    
    # Default production
    return 'thywill.db'

# Get database path and create engine
DATABASE_PATH = get_database_path()
print(f"Database path: {DATABASE_PATH}")

engine = create_engine(
    f"sqlite:///{DATABASE_PATH}" if DATABASE_PATH != ':memory:' else "sqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True if DATABASE_PATH != ':memory:' else False
)

# Database initialization is now handled by standalone script only
# No automatic table creation on import to prevent accidental data loss

# Enable performance optimizations and create invite tree integrity constraints
# Only run optimizations for file-based databases (not in-memory)
if DATABASE_PATH != ':memory:':
    with engine.connect() as conn:
        # Import text here to avoid top-level SQLAlchemy imports
        from sqlalchemy import text
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL")) 
        conn.execute(text("PRAGMA cache_size=10000"))
        conn.execute(text("PRAGMA temp_store=memory"))
        
        # Create indexes for invite tree integrity (only if tables exist)
        try:
            # Check if tables exist before creating indexes
            tables_exist = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('user', 'invitetoken')")).fetchall()
            table_names = [row[0] for row in tables_exist]
            
            if 'user' in table_names:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_invited_by ON user(invited_by_username)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_user_invite_token ON user(invite_token_used)"))
            
            if 'invitetoken' in table_names:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_invitetoken_used_by ON invitetoken(used_by_user_id)"))
                
        except Exception as e:
            # Silently ignore index creation errors (tables may not exist yet)
            pass
        
        conn.commit()

