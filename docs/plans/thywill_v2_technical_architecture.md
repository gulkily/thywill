# ThyWill v2: Technical Architecture

## Core Architectural Principles

### 1. Simplicity Over Cleverness
- Choose boring, well-understood technologies
- Avoid abstractions that hide important details
- Prefer explicit over implicit behavior
- Use standard patterns from the ecosystem

### 2. Data Integrity First
- Database is the single source of truth
- All writes go through validated transactions
- Consistent query patterns with explicit error handling
- No mixed ORM/raw SQL approaches

### 3. Testable Components
- Clear dependency injection
- Mockable external services
- Isolated business logic
- Comprehensive test coverage

## Technology Stack

### Core Technologies

**Database**: PostgreSQL 15+
- **Why**: Superior data integrity, JSON support, full-text search
- **Not SQLite**: Avoids file-based corruption issues
- **Migration path**: Easy to start with SQLite locally, deploy to PostgreSQL

**ORM**: SQLAlchemy 2.x Core (no ORM)
- **Why**: Explicit control, no hidden behaviors, excellent performance
- **Not SQLModel**: Removes hybrid complexity that caused our issues
- **Pattern**: Repository pattern with explicit SQL

**Web Framework**: FastAPI 0.100+
- **Why**: Excellent type hints, good performance, familiar
- **Keep**: Current choice is solid
- **Improve**: Better structure and dependency injection

**Authentication**: Custom with secure cookies
- **Why**: Simple, stateless, no external dependencies
- **Not**: Complex multi-device flows
- **Security**: HTTPOnly, Secure, SameSite cookies

### Supporting Technologies

**Migrations**: Alembic
**Testing**: pytest + pytest-asyncio
**Validation**: Pydantic v2
**CLI**: Click (separate from web app)
**AI Integration**: Anthropic SDK (existing)
**Frontend**: HTMX + Alpine.js (keep existing approach)

## Project Structure

```
thywill_v2/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app setup
│   ├── config.py              # Configuration management
│   ├── dependencies.py        # FastAPI dependencies
│   │
│   ├── core/                  # Core business logic
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication logic
│   │   ├── prayers.py        # Prayer business logic
│   │   ├── users.py          # User management logic
│   │   └── archives.py       # Text archive business logic
│   │
│   ├── models/               # Data models
│   │   ├── __init__.py
│   │   ├── base.py          # Base model classes
│   │   ├── user.py          # User-related models
│   │   ├── prayer.py        # Prayer-related models
│   │   ├── auth.py          # Auth-related models
│   │   └── archive.py       # Archive-related models
│   │
│   ├── repositories/         # Database access layer
│   │   ├── __init__.py
│   │   ├── base.py          # Base repository
│   │   ├── user.py          # User repository
│   │   ├── prayer.py        # Prayer repository
│   │   └── auth.py          # Auth repository
│   │
│   ├── routes/              # HTTP route handlers
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── prayers.py       # Prayer routes
│   │   ├── admin.py         # Admin routes
│   │   ├── archives.py      # Archive download routes
│   │   └── api.py           # API routes
│   │
│   └── services/            # External service integrations
│       ├── __init__.py
│       ├── ai.py           # AI prayer generation
│       ├── archives.py     # Text archive service
│       └── email.py        # Email notifications (future)
│
├── database/
│   ├── __init__.py
│   ├── engine.py           # Database connection
│   ├── session.py          # Session management
│   └── migrations/         # Alembic migrations
│       └── versions/
│
├── cli/
│   ├── __init__.py
│   ├── main.py            # CLI entry point
│   ├── admin.py           # Admin commands
│   └── data.py            # Data management commands
│
├── tests/
│   ├── conftest.py        # Test configuration
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test data
│
├── static/                # Static files
├── templates/             # Jinja2 templates
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Database Layer Architecture

### Connection Management

```python
# database/engine.py
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

def create_db_engine(database_url: str, echo: bool = False):
    """Create database engine with proper configuration."""
    return create_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,  # Auto-reconnect
        pool_recycle=3600,   # Recycle connections
    )

# database/session.py
from contextlib import contextmanager
from sqlalchemy.orm import sessionmaker

@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    session = sessionmaker(bind=engine)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

### Repository Pattern

```python
# repositories/base.py
from abc import ABC, abstractmethod
from sqlalchemy import Connection

class BaseRepository(ABC):
    def __init__(self, connection: Connection):
        self.conn = connection
    
    def execute(self, query, params=None):
        """Execute query with proper error handling."""
        try:
            return self.conn.execute(query, params or {})
        except Exception as e:
            # Log error with context
            raise DatabaseError(f"Query failed: {e}")

# repositories/user.py
class UserRepository(BaseRepository):
    def create_user(self, user_data: dict) -> str:
        """Create new user, return user ID."""
        query = text("""
            INSERT INTO users (id, display_name, email, created_at)
            VALUES (:id, :display_name, :email, :created_at)
            RETURNING id
        """)
        result = self.execute(query, user_data)
        return result.scalar()
    
    def get_user_by_id(self, user_id: str) -> dict | None:
        """Get user by ID."""
        query = text("SELECT * FROM users WHERE id = :user_id")
        result = self.execute(query, {"user_id": user_id})
        row = result.fetchone()
        return dict(row) if row else None
```

## Service Layer Architecture

### Business Logic Separation

```python
# core/users.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateUserRequest:
    display_name: str
    email: Optional[str] = None
    religious_preference: str = "unspecified"

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    def create_user(self, request: CreateUserRequest) -> str:
        """Create a new user with validation."""
        # Validate display name
        if len(request.display_name) < 2:
            raise ValidationError("Display name too short")
        
        # Check for duplicates
        existing = self.user_repo.get_user_by_display_name(request.display_name)
        if existing:
            raise ConflictError("Display name already exists")
        
        # Create user
        user_data = {
            "id": generate_user_id(),
            "display_name": request.display_name,
            "email": request.email,
            "religious_preference": request.religious_preference,
            "created_at": utcnow(),
        }
        
        return self.user_repo.create_user(user_data)
```

## Authentication Architecture

### Simplified Auth Flow

```python
# core/auth.py
from datetime import datetime, timedelta
import secrets
import hashlib

class AuthService:
    def __init__(self, user_repo: UserRepository, session_repo: SessionRepository):
        self.user_repo = user_repo
        self.session_repo = session_repo
    
    def create_session(self, user_id: str) -> str:
        """Create authenticated session."""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=14)
        
        self.session_repo.create_session({
            "id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
        })
        
        return session_id
    
    def validate_session(self, session_id: str) -> dict | None:
        """Validate session and return user data."""
        session = self.session_repo.get_session(session_id)
        if not session or session["expires_at"] < datetime.utcnow():
            return None
        
        user = self.user_repo.get_user_by_id(session["user_id"])
        return user

# Admin token system (simplified)
class AdminTokenService:
    def create_admin_token(self) -> str:
        """Create one-time admin setup token."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        self.session_repo.create_admin_token({
            "token": token,
            "expires_at": expires_at,
            "used": False,
        })
        
        return token
    
    def use_admin_token(self, token: str, user_data: dict) -> str:
        """Use admin token to create admin user."""
        token_record = self.session_repo.get_admin_token(token)
        if not token_record or token_record["used"] or token_record["expires_at"] < datetime.utcnow():
            raise AuthError("Invalid or expired admin token")
        
        # Create admin user
        user_id = self.user_service.create_user(user_data)
        
        # Grant admin role
        self.user_repo.add_user_role(user_id, "admin")
        
        # Mark token as used
        self.session_repo.mark_admin_token_used(token)
        
        return user_id
```

## Route Layer Architecture

### Clean HTTP Handlers

```python
# routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

router = APIRouter(prefix="/auth")

class LoginRequest(BaseModel):
    display_name: str

@router.post("/login")
async def login(
    request: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Simple login endpoint."""
    try:
        user = auth_service.get_user_by_display_name(request.display_name)
        if not user:
            raise HTTPException(404, "User not found")
        
        session_id = auth_service.create_session(user["id"])
        
        # Set secure cookie
        response.set_cookie(
            "session_id",
            session_id,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=14 * 24 * 60 * 60  # 14 days
        )
        
        return {"success": True}
        
    except Exception as e:
        raise HTTPException(500, "Login failed")

@router.post("/admin-setup")
async def admin_setup(
    token: str,
    user_data: CreateUserRequest,
    admin_service: AdminTokenService = Depends(get_admin_service)
):
    """Set up admin user with token."""
    try:
        user_id = admin_service.use_admin_token(token, user_data)
        return {"user_id": user_id, "success": True}
    except AuthError as e:
        raise HTTPException(400, str(e))
```

## Error Handling Strategy

### Consistent Error Patterns

```python
# core/exceptions.py
class ThyWillError(Exception):
    """Base exception for all application errors."""
    pass

class ValidationError(ThyWillError):
    """Data validation errors."""
    pass

class ConflictError(ThyWillError):
    """Resource conflicts (duplicates, etc)."""
    pass

class AuthError(ThyWillError):
    """Authentication/authorization errors."""
    pass

class DatabaseError(ThyWillError):
    """Database operation errors."""
    pass

# Global error handler
@app.exception_handler(ThyWillError)
async def thywill_error_handler(request: Request, exc: ThyWillError):
    """Convert application errors to HTTP responses."""
    error_map = {
        ValidationError: 400,
        ConflictError: 409,
        AuthError: 401,
        DatabaseError: 500,
    }
    
    status_code = error_map.get(type(exc), 500)
    return JSONResponse(
        status_code=status_code,
        content={"error": str(exc), "type": type(exc).__name__}
    )
```

## Configuration Management

### Environment-Based Config

```python
# config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///thywill.db"
    database_echo: bool = False
    
    # Security
    secret_key: str
    cookie_secure: bool = True
    
    # AI Integration
    anthropic_api_key: str | None = None
    
    # Application
    debug: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Testing Strategy

### Test Structure

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from app.database.engine import create_db_engine

@pytest.fixture
def db_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:")
    # Run migrations
    return engine

@pytest.fixture
def user_repo(db_engine):
    """Create user repository for testing."""
    with db_engine.connect() as conn:
        yield UserRepository(conn)

# tests/unit/test_user_service.py
def test_create_user(user_repo):
    """Test user creation."""
    service = UserService(user_repo)
    request = CreateUserRequest(display_name="testuser")
    
    user_id = service.create_user(request)
    
    assert user_id is not None
    user = user_repo.get_user_by_id(user_id)
    assert user["display_name"] == "testuser"
```

## Text Archive Architecture

### Archive System Design Principles

The text archive system is **essential** for ThyWill's transparency and data durability. The v2 implementation improves reliability while maintaining the core benefits:

1. **Community Transparency**: Users can download complete site archives
2. **Data Durability**: Human-readable backups survive any database issues
3. **Audit Trail**: Complete history of all community activity
4. **Disaster Recovery**: Ability to rebuild from text files if needed

### Archive Service Architecture

```python
# services/archives.py
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json
import zipfile

class TextArchiveService:
    """Improved text archive service with reliability focus."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.users_dir = self.base_dir / "users"
        self.prayers_dir = self.base_dir / "prayers"
        self.activity_dir = self.base_dir / "activity"
        self.community_dir = self.base_dir / "community"
        
        # Ensure directories exist
        for dir_path in [self.users_dir, self.prayers_dir, self.activity_dir, self.community_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def archive_user_registration(self, user_data: Dict) -> Path:
        """Archive user registration with atomic write."""
        user_file = self.users_dir / f"{user_data['id']}.txt"
        
        content = f"""User Registration
Date: {user_data['created_at'].isoformat()}
User ID: {user_data['id']}
Display Name: {user_data['display_name']}
Religious Preference: {user_data.get('religious_preference', 'unspecified')}
Email: {user_data.get('email', 'not provided')}
Invited By: {user_data.get('invited_by_display_name', 'direct signup')}

Registration completed successfully.
"""
        
        # Atomic write: write to temp file, then rename
        temp_file = user_file.with_suffix('.tmp')
        temp_file.write_text(content, encoding='utf-8')
        temp_file.rename(user_file)
        
        # Also append to community timeline
        self._append_to_community_timeline(
            f"User '{user_data['display_name']}' joined the community"
        )
        
        return user_file
    
    def archive_prayer_request(self, prayer_data: Dict) -> Path:
        """Archive prayer request with atomic write."""
        prayer_file = self.prayers_dir / f"{prayer_data['id']}.txt"
        
        content = f"""Prayer Request
Date: {prayer_data['created_at'].isoformat()}
Prayer ID: {prayer_data['id']}
Author: {prayer_data['author_display_name']}
Target Audience: {prayer_data.get('target_audience', 'all')}

Request:
{prayer_data['text']}

"""
        
        if prayer_data.get('generated_prayer'):
            content += f"""Generated Community Prayer:
{prayer_data['generated_prayer']}

"""
        
        content += "Prayer request submitted successfully.\n"
        
        # Atomic write
        temp_file = prayer_file.with_suffix('.tmp')
        temp_file.write_text(content, encoding='utf-8')
        temp_file.rename(prayer_file)
        
        # Append to community timeline
        self._append_to_community_timeline(
            f"Prayer request submitted by {prayer_data['author_display_name']}"
        )
        
        return prayer_file
    
    def archive_prayer_mark(self, mark_data: Dict) -> None:
        """Archive prayer mark activity."""
        activity_content = f"""Prayer Mark
Date: {mark_data['marked_at'].isoformat()}
Prayer ID: {mark_data['prayer_id']}
Marked By: {mark_data['user_display_name']}

User marked this prayer as prayed.
"""
        
        # Append to monthly activity log
        month_file = self.activity_dir / f"{mark_data['marked_at'].strftime('%Y-%m')}.txt"
        self._append_to_file(month_file, activity_content)
        
        # Update prayer file with mark
        prayer_file = self.prayers_dir / f"{mark_data['prayer_id']}.txt"
        if prayer_file.exists():
            mark_entry = f"\nPrayer Mark - {mark_data['marked_at'].isoformat()}: Prayed by {mark_data['user_display_name']}\n"
            self._append_to_file(prayer_file, mark_entry)
    
    def archive_prayer_answered(self, prayer_id: str, answered_data: Dict) -> None:
        """Archive answered prayer testimony."""
        prayer_file = self.prayers_dir / f"{prayer_id}.txt"
        
        answered_content = f"""
PRAYER ANSWERED - {answered_data['answered_at'].isoformat()}
"""
        
        if answered_data.get('testimony'):
            answered_content += f"Testimony: {answered_data['testimony']}\n"
        
        answered_content += "Praise God for answered prayer!\n"
        
        self._append_to_file(prayer_file, answered_content)
        
        # Add to community timeline
        self._append_to_community_timeline(
            f"Prayer answered - testimony by {answered_data['author_display_name']}"
        )
    
    def create_user_archive_download(self, user_id: str) -> Path:
        """Create downloadable ZIP archive for a specific user."""
        user_archive_dir = self.base_dir / "downloads" / "users"
        user_archive_dir.mkdir(parents=True, exist_ok=True)
        
        zip_file = user_archive_dir / f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add user registration file
            user_file = self.users_dir / f"{user_id}.txt"
            if user_file.exists():
                zf.write(user_file, f"registration/{user_file.name}")
            
            # Add user's prayer files
            for prayer_file in self.prayers_dir.glob("*.txt"):
                content = prayer_file.read_text(encoding='utf-8')
                if f"Author: {user_id}" in content or f"User ID: {user_id}" in content:
                    zf.write(prayer_file, f"prayers/{prayer_file.name}")
            
            # Add activity files mentioning this user
            for activity_file in self.activity_dir.glob("*.txt"):
                content = activity_file.read_text(encoding='utf-8')
                if user_id in content:
                    zf.write(activity_file, f"activity/{activity_file.name}")
        
        return zip_file
    
    def create_community_archive_download(self) -> Path:
        """Create downloadable ZIP archive of entire community."""
        community_archive_dir = self.base_dir / "downloads" / "community"
        community_archive_dir.mkdir(parents=True, exist_ok=True)
        
        zip_file = community_archive_dir / f"community_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add all archive directories
            for dir_name in ["users", "prayers", "activity", "community"]:
                dir_path = self.base_dir / dir_name
                if dir_path.exists():
                    for file_path in dir_path.rglob("*.txt"):
                        relative_path = file_path.relative_to(self.base_dir)
                        zf.write(file_path, str(relative_path))
            
            # Add metadata
            metadata = {
                "archive_created": datetime.now().isoformat(),
                "archive_type": "complete_community",
                "total_files": len(list(self.base_dir.rglob("*.txt"))),
                "description": "Complete ThyWill community archive including all users, prayers, and activity"
            }
            
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))
        
        return zip_file
    
    def _append_to_file(self, file_path: Path, content: str) -> None:
        """Safely append content to file."""
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Append content atomically
        with file_path.open('a', encoding='utf-8') as f:
            f.write(content)
    
    def _append_to_community_timeline(self, event_description: str) -> None:
        """Append event to community timeline."""
        timeline_file = self.community_dir / f"{datetime.now().strftime('%Y-%m')}.txt"
        event_entry = f"{datetime.now().isoformat()}: {event_description}\n"
        self._append_to_file(timeline_file, event_entry)
```

### Integration with Core Services

```python
# core/prayers.py - Prayer service with archive integration
class PrayerService:
    def __init__(self, prayer_repo: PrayerRepository, archive_service: TextArchiveService):
        self.prayer_repo = prayer_repo
        self.archive_service = archive_service
    
    def create_prayer(self, request: CreatePrayerRequest, author: User) -> str:
        """Create prayer with database-first, archive-second approach."""
        
        # Step 1: Create in database first (for data integrity)
        prayer_data = {
            "id": uuid.uuid4().hex,
            "author_id": author["id"],
            "text": request.text,
            "target_audience": request.target_audience,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Generate AI prayer if requested
        if request.generate_prayer:
            prayer_data["generated_prayer"] = self.ai_service.generate_prayer(request.text)
        
        prayer_id = self.prayer_repo.create_prayer(prayer_data)
        
        # Step 2: Archive after successful database creation
        try:
            archive_data = {
                **prayer_data,
                "author_display_name": author["display_name"]
            }
            self.archive_service.archive_prayer_request(archive_data)
        except Exception as e:
            # Log archive failure but don't fail the request
            logger.error(f"Failed to archive prayer {prayer_id}: {e}")
        
        return prayer_id
    
    def mark_prayer(self, prayer_id: str, user: User) -> bool:
        """Mark prayer as prayed with archive integration."""
        
        # Database operation first
        was_marked = self.prayer_repo.mark_prayer(prayer_id, user["id"])
        
        if was_marked:
            # Archive the activity
            try:
                mark_data = {
                    "prayer_id": prayer_id,
                    "user_id": user["id"],
                    "user_display_name": user["display_name"],
                    "marked_at": datetime.utcnow()
                }
                self.archive_service.archive_prayer_mark(mark_data)
            except Exception as e:
                logger.error(f"Failed to archive prayer mark: {e}")
        
        return was_marked
```

### Archive Routes

```python
# routes/archives.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/archives")

@router.get("/user/{user_id}/download")
async def download_user_archive(
    user_id: str,
    current_user: User = Depends(require_auth),
    archive_service: TextArchiveService = Depends(get_archive_service)
):
    """Download user's personal archive (own data only unless admin)."""
    
    # Security check: users can only download their own data unless admin
    if user_id != current_user["id"] and not current_user.get("is_admin"):
        raise HTTPException(403, "Access denied")
    
    try:
        zip_file = archive_service.create_user_archive_download(user_id)
        
        return FileResponse(
            zip_file,
            media_type="application/zip",
            filename=f"thywill_personal_archive_{user_id}.zip"
        )
    
    except Exception as e:
        logger.error(f"Failed to create user archive: {e}")
        raise HTTPException(500, "Archive creation failed")

@router.get("/community/download")
async def download_community_archive(
    archive_service: TextArchiveService = Depends(get_archive_service)
):
    """Download complete community archive (available to all users for transparency)."""
    
    try:
        zip_file = archive_service.create_community_archive_download()
        
        return FileResponse(
            zip_file,
            media_type="application/zip",
            filename=f"thywill_community_archive_{datetime.now().strftime('%Y%m%d')}.zip"
        )
    
    except Exception as e:
        logger.error(f"Failed to create community archive: {e}")
        raise HTTPException(500, "Archive creation failed")

@router.get("/prayer/{prayer_id}/file")
async def download_prayer_file(
    prayer_id: str,
    archive_service: TextArchiveService = Depends(get_archive_service)
):
    """Download individual prayer text file."""
    
    prayer_file = archive_service.prayers_dir / f"{prayer_id}.txt"
    
    if not prayer_file.exists():
        raise HTTPException(404, "Prayer archive not found")
    
    return FileResponse(
        prayer_file,
        media_type="text/plain",
        filename=f"prayer_{prayer_id}.txt"
    )
```

### Configuration

```python
# config.py
class Settings(BaseSettings):
    # ... other settings ...
    
    # Text Archive Settings
    text_archive_enabled: bool = True
    text_archive_base_dir: Path = Path("./text_archives")
    archive_downloads_enabled: bool = True
    archive_cleanup_days: int = 30  # Clean up old download files
    
    class Config:
        env_file = ".env"
```

## Migration Strategy

### Database Migrations

```python
# database/migrations/versions/001_initial.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('display_name', sa.String(100), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('religious_preference', sa.String(50), default='unspecified'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('is_admin', sa.Boolean, default=False),
        sa.Column('text_archive_path', sa.String(500), nullable=True),  # Path to user's archive file
    )
    
    op.create_table(
        'prayers',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('author_id', sa.String(32), sa.ForeignKey('users.id')),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('generated_prayer', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('is_flagged', sa.Boolean, default=False),
        sa.Column('text_archive_path', sa.String(500), nullable=True),  # Path to prayer's archive file
    )
```

This architecture prioritizes:
- **Simplicity**: Clear layers, explicit patterns
- **Reliability**: Proper error handling, transaction management
- **Testability**: Dependency injection, isolated components
- **Maintainability**: Standard patterns, good documentation

The key insight is to avoid the complexity that led to our current issues while maintaining the core spiritual community features that make ThyWill valuable.