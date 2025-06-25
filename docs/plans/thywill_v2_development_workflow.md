# ThyWill v2: Development Workflow & Best Practices

## Development Environment Setup

### Prerequisites
```bash
# Required software
python 3.11+
postgresql 15+
git
docker (optional, for containerized development)
```

### Initial Setup
```bash
# Clone repository
git clone https://github.com/your-org/thywill-v2.git
cd thywill-v2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Set up database
createdb thywill_v2_dev
alembic upgrade head

# Set up text archives directory
mkdir -p text_archives_dev/{users,prayers,activity,community,downloads}

# Seed development data
python scripts/seed_dev_data.py

# Run tests to verify setup
pytest

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure & Organization

### Directory Layout
```
thywill_v2/
├── app/                    # Main application code
│   ├── core/              # Business logic
│   ├── models/            # Data models
│   ├── repositories/      # Database access
│   ├── routes/            # HTTP routes
│   ├── services/          # External services
│   └── dependencies.py   # FastAPI dependencies
├── database/              # Database management
│   ├── migrations/        # Alembic migrations
│   └── seeds/            # Development data
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── fixtures/         # Test data
│   └── conftest.py       # Test configuration
├── scripts/               # Utility scripts
├── docs/                  # Documentation
├── requirements-dev.txt   # Development dependencies
└── pyproject.toml        # Project configuration
```

### Import Organization
```python
# Standard imports
import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Connection, text
from pydantic import BaseModel

# Local imports
from app.core.users import UserService
from app.repositories.user import UserRepository
from app.models.user import User, CreateUserRequest
```

## Coding Standards

### Python Style Guide
- **PEP 8** compliance enforced by `black` and `flake8`
- **Type hints** required for all function signatures
- **Docstrings** required for all public functions and classes
- **Maximum line length**: 88 characters (black default)

### Code Quality Tools
```bash
# Format code
black app/ tests/ scripts/

# Check style
flake8 app/ tests/ scripts/

# Type checking
mypy app/

# Security scanning
bandit -r app/

# Import sorting
isort app/ tests/ scripts/
```

### Function Documentation
```python
def create_user(self, request: CreateUserRequest) -> str:
    """Create a new user account.
    
    Args:
        request: User creation request with validation
        
    Returns:
        User ID of the created user
        
    Raises:
        ValidationError: If request data is invalid
        ConflictError: If display name already exists
    """
```

### Error Handling
```python
# Use specific exception types
from app.core.exceptions import ValidationError, ConflictError

# Always log errors with context
import logging
logger = logging.getLogger(__name__)

def create_user(self, request: CreateUserRequest) -> str:
    try:
        # Validate input
        if not request.display_name.strip():
            raise ValidationError("Display name cannot be empty")
        
        # Business logic
        return self.user_repo.create_user(request)
        
    except Exception as e:
        logger.error(f"Failed to create user {request.display_name}: {e}")
        raise
```

## Database Development

### Migration Workflow
```bash
# Create new migration
alembic revision --autogenerate -m "Add user roles table"

# Review generated migration file
# Edit migrations/versions/xxx_add_user_roles_table.py

# Test migration up
alembic upgrade head

# Test migration down
alembic downgrade -1

# Test migration on fresh database
dropdb thywill_v2_test && createdb thywill_v2_test
DATABASE_URL=postgresql://localhost/thywill_v2_test alembic upgrade head
```

### Migration Best Practices
```python
# migrations/versions/xxx_example.py
"""Add user email column

Revision ID: abc123
Revises: def456
Create Date: 2024-01-15 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123'
down_revision = 'def456'
branch_labels = None
depends_on = None

def upgrade():
    # Add column with default value for existing rows
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))
    
    # Add constraint after column exists
    op.create_index('idx_users_email', 'users', ['email'])

def downgrade():
    # Remove in reverse order
    op.drop_index('idx_users_email', 'users')
    op.drop_column('users', 'email')
```

### Repository Pattern
```python
# repositories/base.py
from abc import ABC, abstractmethod
from sqlalchemy import Connection

class BaseRepository(ABC):
    def __init__(self, connection: Connection):
        self.conn = connection
    
    def execute(self, query: str, params: dict = None):
        """Execute query with error handling and logging."""
        try:
            return self.conn.execute(text(query), params or {})
        except Exception as e:
            logger.error(f"Database query failed: {query[:100]}... Error: {e}")
            raise

# repositories/user.py
class UserRepository(BaseRepository):
    def create_user(self, user_data: dict) -> str:
        """Create user with transaction safety."""
        query = """
            INSERT INTO users (id, display_name, email, created_at, updated_at)
            VALUES (:id, :display_name, :email, :created_at, :updated_at)
            RETURNING id
        """
        result = self.execute(query, user_data)
        return result.scalar()
```

## Testing Strategy

### Test Categories
```bash
# Unit tests - fast, isolated
pytest tests/unit/ -v

# Integration tests - database required
pytest tests/integration/ -v

# End-to-end tests - full application
pytest tests/e2e/ -v

# All tests with coverage
pytest --cov=app --cov-report=html tests/
```

### Test Structure
```python
# tests/unit/test_user_service.py
import pytest
from unittest.mock import Mock

from app.core.users import UserService
from app.core.exceptions import ValidationError

class TestUserService:
    @pytest.fixture
    def mock_user_repo(self):
        return Mock()
    
    @pytest.fixture
    def user_service(self, mock_user_repo):
        return UserService(mock_user_repo)
    
    def test_create_user_success(self, user_service, mock_user_repo):
        # Arrange
        request = CreateUserRequest(display_name="testuser")
        mock_user_repo.create_user.return_value = "user123"
        mock_user_repo.display_name_exists.return_value = False
        
        # Act
        result = user_service.create_user(request)
        
        # Assert
        assert result == "user123"
        mock_user_repo.create_user.assert_called_once()
    
    def test_create_user_duplicate_name(self, user_service, mock_user_repo):
        # Arrange
        request = CreateUserRequest(display_name="existing")
        mock_user_repo.display_name_exists.return_value = True
        
        # Act & Assert
        with pytest.raises(ConflictError, match="Display name already exists"):
            user_service.create_user(request)
```

### Integration Testing
```python
# tests/integration/test_user_repository.py
import pytest
from sqlalchemy import create_engine

from app.repositories.user import UserRepository

class TestUserRepositoryIntegration:
    @pytest.fixture
    def db_connection(self):
        engine = create_engine("sqlite:///:memory:")
        # Run migrations
        with engine.connect() as conn:
            yield conn
    
    def test_create_and_retrieve_user(self, db_connection):
        repo = UserRepository(db_connection)
        
        # Create user
        user_data = {
            "id": "test123",
            "display_name": "testuser",
            "email": "test@example.com",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        user_id = repo.create_user(user_data)
        assert user_id == "test123"
        
        # Retrieve user
        user = repo.get_user_by_id("test123")
        assert user["display_name"] == "testuser"
        assert user["email"] == "test@example.com"
```

## Development Workflow

### Git Workflow
```bash
# Feature development
git checkout main
git pull origin main
git checkout -b feature/user-authentication

# Make changes, commit frequently
git add .
git commit -m "Add user authentication service"

# Push and create PR
git push origin feature/user-authentication
# Create pull request in GitHub

# After review and approval
git checkout main
git pull origin main
git branch -d feature/user-authentication
```

### Commit Message Format
```
type(scope): brief description

Longer description if needed explaining what and why.

- Bullet points for multiple changes
- Use present tense ("add" not "added")
- Reference issues: "Fixes #123"

Types: feat, fix, docs, style, refactor, test, chore
Scopes: auth, users, prayers, db, api, etc.
```

### Code Review Checklist

**Functionality**
- [ ] Code works as intended
- [ ] Edge cases handled appropriately
- [ ] Error handling is comprehensive
- [ ] Performance considerations addressed

**Code Quality**
- [ ] Follows project coding standards
- [ ] Type hints are complete and accurate
- [ ] Documentation is clear and sufficient
- [ ] No code duplication

**Testing**
- [ ] Unit tests cover new functionality
- [ ] Integration tests for database changes
- [ ] Tests are readable and maintainable
- [ ] Edge cases are tested

**Security**
- [ ] No hardcoded secrets or credentials
- [ ] Input validation is proper
- [ ] SQL injection prevention
- [ ] Authentication/authorization correct

## Local Development

### Development Database
```bash
# Reset development database
dropdb thywill_v2_dev
createdb thywill_v2_dev
alembic upgrade head
python scripts/seed_dev_data.py

# Development with live reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run background tasks (if any)
python scripts/run_background_tasks.py
```

### Development Data
```python
# scripts/seed_dev_data.py
def seed_development_data():
    """Create realistic development data."""
    
    with get_db_connection() as conn:
        user_repo = UserRepository(conn)
        prayer_repo = PrayerRepository(conn)
        
        # Create test users
        users = [
            {"display_name": "Alice", "religious_preference": "christian"},
            {"display_name": "Bob", "religious_preference": "unspecified"},
            {"display_name": "Charlie", "religious_preference": "christian"}
        ]
        
        user_ids = []
        for user_data in users:
            user_id = user_repo.create_user({
                "id": uuid.uuid4().hex,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                **user_data
            })
            user_ids.append(user_id)
        
        # Create test prayers
        prayers = [
            "Please pray for my job interview tomorrow",
            "Prayers needed for my family's health",
            "Grateful for answered prayers about housing"
        ]
        
        for i, prayer_text in enumerate(prayers):
            prayer_id = prayer_repo.create_prayer(
                author_id=user_ids[i % len(user_ids)],
                text=prayer_text,
                target_audience="all"
            )
            
            # Create text archive for development prayer
            archive_service = TextArchiveService(Path("./text_archives_dev"))
            prayer_data = {
                "id": prayer_id,
                "author_id": user_ids[i % len(user_ids)],
                "author_display_name": users[i % len(users)]["display_name"],
                "text": prayer_text,
                "target_audience": "all",
                "created_at": datetime.utcnow()
            }
            archive_service.archive_prayer_request(prayer_data)
```

### Configuration Management
```python
# app/config.py
from pydantic import BaseSettings

class DevelopmentSettings(BaseSettings):
    database_url: str = "postgresql://localhost/thywill_v2_dev"
    database_echo: bool = True  # SQL logging
    debug: bool = True
    reload: bool = True
    
    anthropic_api_key: str | None = None  # Optional for development
    
    class Config:
        env_file = ".env.dev"

class ProductionSettings(BaseSettings):
    database_url: str
    database_echo: bool = False
    debug: bool = False
    reload: bool = False
    
    anthropic_api_key: str  # Required
    secret_key: str  # Required
    
    class Config:
        env_file = ".env.prod"

# app/main.py
import os
from app.config import DevelopmentSettings, ProductionSettings

if os.getenv("ENVIRONMENT") == "production":
    settings = ProductionSettings()
else:
    settings = DevelopmentSettings()
```

## Deployment

### Staging Deployment
```bash
# Build and deploy to staging
docker build -t thywill-v2:staging .
docker push registry.example.com/thywill-v2:staging

# Deploy with docker-compose
docker-compose -f docker-compose.staging.yml up -d

# Run migrations
docker exec thywill-v2-web alembic upgrade head

# Smoke tests
python scripts/smoke_tests.py --env staging
```

### Production Deployment
```bash
# Tag release
git tag v2.0.0
git push origin v2.0.0

# Build production image
docker build -t thywill-v2:v2.0.0 .
docker push registry.example.com/thywill-v2:v2.0.0

# Deploy with zero downtime
kubectl set image deployment/thywill-v2 web=registry.example.com/thywill-v2:v2.0.0

# Verify deployment
kubectl rollout status deployment/thywill-v2
python scripts/health_check.py --env production
```

## Monitoring & Debugging

### Logging Configuration
```python
# app/logging_config.py
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "app.log",
            "level": "DEBUG",
            "formatter": "detailed",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
```

### Performance Monitoring
```python
# app/middleware/performance.py
import time
from fastapi import Request

async def performance_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 1.0:
        logger.warning(f"Slow request: {request.url} took {process_time:.2f}s")
    
    return response
```

This development workflow emphasizes:
- **Code quality** through automated tools and review processes
- **Testing** with comprehensive coverage and multiple test types
- **Database safety** through proper migration and repository patterns
- **Developer experience** with clear setup and debugging tools
- **Production readiness** through proper deployment and monitoring practices