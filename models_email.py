"""
Email Database Models - Separate database for email data isolation
"""
import os
import sys
from datetime import datetime
from sqlmodel import Field, SQLModel, create_engine, Session, MetaData
import uuid

# Create separate metadata for email tables to avoid importing all main DB tables
email_metadata = MetaData()

class UserEmail(SQLModel, table=True, metadata=email_metadata):
    """User email associations stored in separate database for security isolation"""
    __tablename__ = "user_email"
    
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    user_id: str = Field(index=True)  # Links to User.display_name in main db (no FK for isolation)
    email_encrypted: str = Field(index=True)  # AES encrypted email address
    email_verified: bool = Field(default=False)
    verification_token: str | None = Field(default=None, index=True)
    added_at: datetime = Field(default_factory=datetime.utcnow)
    verified_at: datetime | None = Field(default=None)
    
    def __repr__(self):
        return f"<UserEmail(user_id={self.user_id}, verified={self.email_verified})>"

# Database path configuration for email database
def get_email_database_path():
    """
    Email database path selection with test environment safety
    """
    # Safety: Detect test environment 
    if ('pytest' in sys.modules or 
        'PYTEST_CURRENT_TEST' in os.environ or
        any('pytest' in arg for arg in sys.argv)):
        return ':memory:'
    
    # Explicit configuration
    if 'EMAIL_DATABASE_PATH' in os.environ and os.environ['EMAIL_DATABASE_PATH'].strip():
        return os.environ['EMAIL_DATABASE_PATH']
    
    # Default: separate email database
    return 'email.db'

# Get email database path and create engine
EMAIL_DATABASE_PATH = get_email_database_path()
print(f"Email database path: {EMAIL_DATABASE_PATH}")

email_engine = create_engine(
    f"sqlite:///{EMAIL_DATABASE_PATH}" if EMAIL_DATABASE_PATH != ':memory:' else "sqlite:///:memory:",
    echo=False,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True if EMAIL_DATABASE_PATH != ':memory:' else False
)

# Create only email tables in the email database
UserEmail.__table__.create(email_engine, checkfirst=True)