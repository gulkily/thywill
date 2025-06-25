# ThyWill v2: Database Design

## Database Architecture Principles

### 1. Simplicity and Consistency
- Single ORM approach (SQLAlchemy Core)
- Explicit relationships and constraints
- No hybrid text-file/database systems
- Standard relational patterns

### 2. Data Integrity
- Proper foreign key constraints
- NOT NULL constraints where appropriate
- Check constraints for data validation
- Consistent data types and naming

### 3. Performance Considerations
- Appropriate indexes for common queries
- Efficient query patterns
- Minimal N+1 query problems
- Reasonable denormalization where needed

## Schema Design

### Core Tables

#### Users Table
```sql
CREATE TABLE users (
    id VARCHAR(32) PRIMARY KEY,
    display_name VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    religious_preference VARCHAR(50) NOT NULL DEFAULT 'unspecified',
    prayer_style VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    text_archive_path VARCHAR(500),  -- Path to user's text archive file
    
    -- Constraints
    CONSTRAINT users_display_name_length CHECK (LENGTH(display_name) >= 2),
    CONSTRAINT users_religious_preference_valid CHECK (
        religious_preference IN ('christian', 'unspecified', 'other')
    )
);

-- Indexes
CREATE INDEX idx_users_display_name ON users(display_name);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;
```

#### Prayers Table
```sql
CREATE TABLE prayers (
    id VARCHAR(32) PRIMARY KEY,
    author_id VARCHAR(32) NOT NULL,
    text TEXT NOT NULL,
    generated_prayer TEXT,
    target_audience VARCHAR(50) NOT NULL DEFAULT 'all',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    is_answered BOOLEAN NOT NULL DEFAULT FALSE,
    answered_at TIMESTAMP,
    testimony TEXT,
    text_archive_path VARCHAR(500),  -- Path to prayer's text archive file
    
    -- Foreign Keys
    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT prayers_text_length CHECK (LENGTH(text) >= 10 AND LENGTH(text) <= 5000),
    CONSTRAINT prayers_target_audience_valid CHECK (
        target_audience IN ('all', 'christians_only')
    ),
    CONSTRAINT prayers_answered_consistency CHECK (
        (is_answered = FALSE AND answered_at IS NULL AND testimony IS NULL) OR
        (is_answered = TRUE AND answered_at IS NOT NULL)
    )
);

-- Indexes
CREATE INDEX idx_prayers_author_id ON prayers(author_id);
CREATE INDEX idx_prayers_created_at ON prayers(created_at DESC);
CREATE INDEX idx_prayers_active ON prayers(is_archived, created_at DESC) WHERE is_archived = FALSE;
CREATE INDEX idx_prayers_answered ON prayers(is_answered, answered_at DESC) WHERE is_answered = TRUE;
```

#### Prayer Marks Table
```sql
CREATE TABLE prayer_marks (
    id VARCHAR(32) PRIMARY KEY,
    prayer_id VARCHAR(32) NOT NULL,
    user_id VARCHAR(32) NOT NULL,
    marked_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Foreign Keys
    FOREIGN KEY (prayer_id) REFERENCES prayers(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Constraints
    UNIQUE(prayer_id, user_id)  -- User can only mark each prayer once
);

-- Indexes
CREATE INDEX idx_prayer_marks_prayer_id ON prayer_marks(prayer_id);
CREATE INDEX idx_prayer_marks_user_id ON prayer_marks(user_id, marked_at DESC);
CREATE INDEX idx_prayer_marks_recent ON prayer_marks(marked_at DESC);
```

#### Sessions Table
```sql
CREATE TABLE sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL DEFAULT NOW(),
    user_agent TEXT,
    ip_address INET,
    
    -- Foreign Keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT sessions_expires_after_created CHECK (expires_at > created_at)
);

-- Indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_sessions_active ON sessions(user_id, expires_at) WHERE expires_at > NOW();
```

#### Invites Table
```sql
CREATE TABLE invites (
    id VARCHAR(32) PRIMARY KEY,
    token VARCHAR(64) NOT NULL UNIQUE,
    created_by_user_id VARCHAR(32),  -- NULL for system-generated tokens
    invited_display_name VARCHAR(100),  -- Optional pre-filled name
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    used_by_user_id VARCHAR(32),
    is_admin_token BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Foreign Keys
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (used_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    
    -- Constraints
    CONSTRAINT invites_expires_after_created CHECK (expires_at > created_at),
    CONSTRAINT invites_used_consistency CHECK (
        (used_at IS NULL AND used_by_user_id IS NULL) OR
        (used_at IS NOT NULL AND used_by_user_id IS NOT NULL)
    )
);

-- Indexes
CREATE INDEX idx_invites_token ON invites(token);
CREATE INDEX idx_invites_created_by ON invites(created_by_user_id);
CREATE INDEX idx_invites_expires_at ON invites(expires_at);
CREATE INDEX idx_invites_unused ON invites(expires_at) WHERE used_at IS NULL;
```

#### Content Flags Table
```sql
CREATE TABLE content_flags (
    id VARCHAR(32) PRIMARY KEY,
    prayer_id VARCHAR(32) NOT NULL,
    flagged_by_user_id VARCHAR(32) NOT NULL,
    reason VARCHAR(255),
    flagged_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolved_by_user_id VARCHAR(32),
    resolution_action VARCHAR(50),  -- 'dismissed', 'content_removed', 'user_warned'
    
    -- Foreign Keys
    FOREIGN KEY (prayer_id) REFERENCES prayers(id) ON DELETE CASCADE,
    FOREIGN KEY (flagged_by_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (resolved_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    
    -- Constraints
    UNIQUE(prayer_id, flagged_by_user_id),  -- User can only flag each prayer once
    CONSTRAINT flags_resolution_consistency CHECK (
        (resolved_at IS NULL AND resolved_by_user_id IS NULL AND resolution_action IS NULL) OR
        (resolved_at IS NOT NULL AND resolved_by_user_id IS NOT NULL AND resolution_action IS NOT NULL)
    )
);

-- Indexes
CREATE INDEX idx_content_flags_prayer_id ON content_flags(prayer_id);
CREATE INDEX idx_content_flags_flagged_by ON content_flags(flagged_by_user_id);
CREATE INDEX idx_content_flags_unresolved ON content_flags(flagged_at) WHERE resolved_at IS NULL;
```

#### User Roles Table (Simplified)
```sql
CREATE TABLE user_roles (
    user_id VARCHAR(32) NOT NULL,
    role VARCHAR(50) NOT NULL,
    granted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    granted_by_user_id VARCHAR(32),
    
    -- Foreign Keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    
    -- Constraints
    PRIMARY KEY (user_id, role),
    CONSTRAINT user_roles_role_valid CHECK (role IN ('admin', 'moderator'))
);

-- Indexes
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role);
```

## Repository Implementation Examples

### Base Repository Pattern

```python
# repositories/base.py
from abc import ABC, abstractmethod
from sqlalchemy import Connection, text
from typing import Any, Dict, List, Optional

class BaseRepository(ABC):
    def __init__(self, connection: Connection):
        self.conn = connection
    
    def execute(self, query: str, params: Dict[str, Any] = None) -> Any:
        """Execute a query with parameters."""
        return self.conn.execute(text(query), params or {})
    
    def fetch_one(self, query: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Execute query and return one row as dict."""
        result = self.execute(query, params)
        row = result.fetchone()
        return dict(row) if row else None
    
    def fetch_all(self, query: str, params: Dict[str, Any] = None) -> List[Dict]:
        """Execute query and return all rows as dicts."""
        result = self.execute(query, params)
        return [dict(row) for row in result.fetchall()]
```

### User Repository

```python
# repositories/user.py
from .base import BaseRepository
from typing import Optional, List
import uuid
from datetime import datetime

class UserRepository(BaseRepository):
    
    def create_user(self, display_name: str, email: Optional[str] = None, 
                   religious_preference: str = "unspecified") -> str:
        """Create a new user and return user ID."""
        user_id = uuid.uuid4().hex
        query = """
            INSERT INTO users (id, display_name, email, religious_preference, created_at, updated_at)
            VALUES (:id, :display_name, :email, :religious_preference, :created_at, :updated_at)
            RETURNING id
        """
        params = {
            "id": user_id,
            "display_name": display_name,
            "email": email,
            "religious_preference": religious_preference,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.execute(query, params)
        return result.scalar()
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        query = "SELECT * FROM users WHERE id = :user_id AND is_active = TRUE"
        return self.fetch_one(query, {"user_id": user_id})
    
    def get_user_by_display_name(self, display_name: str) -> Optional[Dict]:
        """Get user by display name."""
        query = "SELECT * FROM users WHERE display_name = :display_name AND is_active = TRUE"
        return self.fetch_one(query, {"display_name": display_name})
    
    def display_name_exists(self, display_name: str) -> bool:
        """Check if display name is already taken."""
        query = "SELECT 1 FROM users WHERE display_name = :display_name AND is_active = TRUE"
        result = self.fetch_one(query, {"display_name": display_name})
        return result is not None
    
    def add_user_role(self, user_id: str, role: str, granted_by_user_id: Optional[str] = None):
        """Add role to user."""
        query = """
            INSERT INTO user_roles (user_id, role, granted_at, granted_by_user_id)
            VALUES (:user_id, :role, :granted_at, :granted_by_user_id)
            ON CONFLICT (user_id, role) DO NOTHING
        """
        params = {
            "user_id": user_id,
            "role": role,
            "granted_at": datetime.utcnow(),
            "granted_by_user_id": granted_by_user_id
        }
        self.execute(query, params)
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """Get all roles for a user."""
        query = "SELECT role FROM user_roles WHERE user_id = :user_id"
        results = self.fetch_all(query, {"user_id": user_id})
        return [row["role"] for row in results]
```

### Prayer Repository

```python
# repositories/prayer.py
from .base import BaseRepository
from typing import Optional, List, Dict
import uuid
from datetime import datetime

class PrayerRepository(BaseRepository):
    
    def create_prayer(self, author_id: str, text: str, generated_prayer: Optional[str] = None,
                     target_audience: str = "all") -> str:
        """Create a new prayer and return prayer ID."""
        prayer_id = uuid.uuid4().hex
        query = """
            INSERT INTO prayers (id, author_id, text, generated_prayer, target_audience, created_at, updated_at)
            VALUES (:id, :author_id, :text, :generated_prayer, :target_audience, :created_at, :updated_at)
            RETURNING id
        """
        params = {
            "id": prayer_id,
            "author_id": author_id,
            "text": text,
            "generated_prayer": generated_prayer,
            "target_audience": target_audience,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = self.execute(query, params)
        return result.scalar()
    
    def get_prayer_by_id(self, prayer_id: str) -> Optional[Dict]:
        """Get prayer by ID with author information."""
        query = """
            SELECT p.*, u.display_name as author_name
            FROM prayers p
            JOIN users u ON p.author_id = u.id
            WHERE p.id = :prayer_id
        """
        return self.fetch_one(query, {"prayer_id": prayer_id})
    
    def get_prayers_feed(self, target_audience: str = "all", limit: int = 50, 
                        offset: int = 0, include_archived: bool = False) -> List[Dict]:
        """Get prayers for main feed with prayer counts."""
        where_conditions = ["p.target_audience IN ('all', :target_audience)"]
        if not include_archived:
            where_conditions.append("p.is_archived = FALSE")
        
        query = f"""
            SELECT 
                p.*,
                u.display_name as author_name,
                COUNT(pm.id) as prayer_count
            FROM prayers p
            JOIN users u ON p.author_id = u.id
            LEFT JOIN prayer_marks pm ON p.id = pm.prayer_id
            WHERE {' AND '.join(where_conditions)}
            GROUP BY p.id, u.display_name
            ORDER BY p.created_at DESC
            LIMIT :limit OFFSET :offset
        """
        params = {
            "target_audience": target_audience,
            "limit": limit,
            "offset": offset
        }
        return self.fetch_all(query, params)
    
    def mark_prayer(self, prayer_id: str, user_id: str) -> bool:
        """Mark a prayer as prayed by user. Returns True if newly marked."""
        # Check if already marked
        check_query = """
            SELECT 1 FROM prayer_marks 
            WHERE prayer_id = :prayer_id AND user_id = :user_id
        """
        existing = self.fetch_one(check_query, {"prayer_id": prayer_id, "user_id": user_id})
        
        if existing:
            return False  # Already marked
        
        # Insert new mark
        mark_id = uuid.uuid4().hex
        insert_query = """
            INSERT INTO prayer_marks (id, prayer_id, user_id, marked_at)
            VALUES (:id, :prayer_id, :user_id, :marked_at)
        """
        params = {
            "id": mark_id,
            "prayer_id": prayer_id,
            "user_id": user_id,
            "marked_at": datetime.utcnow()
        }
        self.execute(insert_query, params)
        return True  # Newly marked
    
    def archive_prayer(self, prayer_id: str, author_id: str) -> bool:
        """Archive a prayer (only by author)."""
        query = """
            UPDATE prayers 
            SET is_archived = TRUE, updated_at = :updated_at
            WHERE id = :prayer_id AND author_id = :author_id AND is_archived = FALSE
        """
        params = {
            "prayer_id": prayer_id,
            "author_id": author_id,
            "updated_at": datetime.utcnow()
        }
        result = self.execute(query, params)
        return result.rowcount > 0
    
    def mark_answered(self, prayer_id: str, author_id: str, testimony: Optional[str] = None) -> bool:
        """Mark prayer as answered (only by author)."""
        query = """
            UPDATE prayers 
            SET is_answered = TRUE, answered_at = :answered_at, testimony = :testimony, updated_at = :updated_at
            WHERE id = :prayer_id AND author_id = :author_id AND is_answered = FALSE
        """
        params = {
            "prayer_id": prayer_id,
            "author_id": author_id,
            "answered_at": datetime.utcnow(),
            "testimony": testimony,
            "updated_at": datetime.utcnow()
        }
        result = self.execute(query, params)
        return result.rowcount > 0
```

## Data Migration Strategy

### Migration from ThyWill v1

```python
# cli/migrate_from_v1.py
def migrate_from_v1_database(v1_db_path: str, v2_connection: Connection):
    """Migrate data from v1 SQLite database to v2 schema."""
    
    # Connect to v1 database
    v1_engine = create_engine(f"sqlite:///{v1_db_path}")
    
    with v1_engine.connect() as v1_conn:
        # Migrate users
        v1_users = v1_conn.execute("SELECT * FROM user").fetchall()
        for user in v1_users:
            # Skip corrupted users (implement detection logic)
            if is_user_corrupted(user):
                print(f"Skipping corrupted user: {user.display_name}")
                continue
            
            # Insert into v2
            v2_connection.execute(text("""
                INSERT INTO users (id, display_name, religious_preference, created_at, updated_at)
                VALUES (:id, :display_name, :religious_preference, :created_at, :updated_at)
            """), {
                "id": user.id,
                "display_name": user.display_name,
                "religious_preference": user.religious_preference or "unspecified",
                "created_at": user.created_at,
                "updated_at": user.created_at  # Use created_at as updated_at
            })
        
        # Migrate prayers
        v1_prayers = v1_conn.execute("SELECT * FROM prayer").fetchall()
        for prayer in v1_prayers:
            # Check if author exists in v2
            author_exists = v2_connection.execute(text(
                "SELECT 1 FROM users WHERE id = :author_id"
            ), {"author_id": prayer.author_id}).fetchone()
            
            if not author_exists:
                print(f"Skipping prayer {prayer.id} - author not found")
                continue
            
            v2_connection.execute(text("""
                INSERT INTO prayers (id, author_id, text, generated_prayer, target_audience, created_at, updated_at)
                VALUES (:id, :author_id, :text, :generated_prayer, :target_audience, :created_at, :updated_at)
            """), {
                "id": prayer.id,
                "author_id": prayer.author_id,
                "text": prayer.text,
                "generated_prayer": prayer.generated_prayer,
                "target_audience": prayer.target_audience or "all",
                "created_at": prayer.created_at,
                "updated_at": prayer.created_at
            })
        
        # Migrate prayer marks
        v1_marks = v1_conn.execute("SELECT * FROM prayermark").fetchall()
        for mark in v1_marks:
            # Verify both prayer and user exist
            prayer_exists = v2_connection.execute(text(
                "SELECT 1 FROM prayers WHERE id = :prayer_id"
            ), {"prayer_id": mark.prayer_id}).fetchone()
            
            user_exists = v2_connection.execute(text(
                "SELECT 1 FROM users WHERE id = :user_id"
            ), {"user_id": mark.user_id}).fetchone()
            
            if prayer_exists and user_exists:
                v2_connection.execute(text("""
                    INSERT INTO prayer_marks (id, prayer_id, user_id, marked_at)
                    VALUES (:id, :prayer_id, :user_id, :marked_at)
                    ON CONFLICT (prayer_id, user_id) DO NOTHING
                """), {
                    "id": uuid.uuid4().hex,
                    "prayer_id": mark.prayer_id,
                    "user_id": mark.user_id,
                    "marked_at": mark.created_at
                })

def is_user_corrupted(user_row) -> bool:
    """Detect if a user record is corrupted based on v1 patterns."""
    # Implement corruption detection logic based on our experience
    # For example, users that can't be retrieved by ID in v1
    return False  # Placeholder
```

## Performance Considerations

### Query Optimization

```sql
-- Efficient prayer feed query with pagination
EXPLAIN ANALYZE
SELECT 
    p.id,
    p.text,
    p.generated_prayer,
    p.created_at,
    u.display_name as author_name,
    COUNT(pm.id) as prayer_count
FROM prayers p
JOIN users u ON p.author_id = u.id
LEFT JOIN prayer_marks pm ON p.id = pm.prayer_id
WHERE p.is_archived = FALSE 
    AND p.target_audience IN ('all', 'christians_only')
GROUP BY p.id, u.display_name
ORDER BY p.created_at DESC
LIMIT 20 OFFSET 0;

-- Index usage verification
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('prayers', 'users', 'prayer_marks');
```

### Connection Pooling

```python
# database/engine.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

def create_production_engine(database_url: str):
    """Create production database engine with connection pooling."""
    return create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=10,          # Number of connections to maintain
        max_overflow=20,       # Additional connections when needed
        pool_recycle=3600,     # Recycle connections every hour
        pool_pre_ping=True,    # Verify connections before use
        echo=False             # Disable query logging in production
    )
```

This database design prioritizes:
- **Data integrity** through proper constraints and foreign keys
- **Performance** through strategic indexing and efficient queries
- **Simplicity** through standard relational patterns
- **Maintainability** through clear repository patterns and migration strategies

The key improvement over v1 is the elimination of complex ORM abstractions and hybrid approaches that led to corruption issues.