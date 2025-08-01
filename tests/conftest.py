import pytest
import tempfile
import os
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta
import uuid
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from models import User, Prayer, Session as SessionModel, InviteToken, PrayerMark, AuthenticationRequest, AuthApproval, AuthAuditLog, SecurityLog, PrayerAttribute, PrayerActivityLog, Role, UserRole, NotificationState, PrayerSkip, ChangelogEntry
from tests.factories import UserFactory, SessionFactory

# Additional safety layer: Verify we're using safe database path
def pytest_configure(config):
    """Pytest configuration hook to verify database safety"""
    from models import DATABASE_PATH
    if DATABASE_PATH != ':memory:':
        raise RuntimeError(f"SAFETY ERROR: Tests must use in-memory database, got: {DATABASE_PATH}")
    print(f"Database safety verified: {DATABASE_PATH}")


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine using in-memory SQLite"""
    # Tests use in-memory database by default (safe by design)
    # No need to set any environment variables
    
    # Use in-memory SQLite for faster tests with threading support
    engine = create_engine(
        "sqlite:///:memory:", 
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a test database session with automatic cleanup"""
    with Session(test_engine) as session:
        yield session
        # Cleanup happens automatically when session closes


@pytest.fixture(scope="function")
def client(test_session):
    """Test client for API testing with test database session injection"""
    from app import app
    
    # Create a dependency override to inject the test session
    def get_test_session():
        return test_session
    
    # Create a custom dependency for database operations  
    from sqlmodel import Session
    from models import engine
    
    # Override the Session creation in the app to use test_session
    original_session = Session
    
    def mock_session(engine_arg):
        # Return the test session instead of creating a new one
        return test_session
    
    # Create all patches in a single context manager
    patches = [
        patch('app_helpers.services.text_archive_service.TEXT_ARCHIVE_ENABLED', False),
        patch('app.TEXT_ARCHIVE_ENABLED', False),
        patch('app_helpers.services.archive_first_service.text_archive_service.enabled', False),
        patch('app.Session', mock_session),
        patch('models.engine', test_session.bind),
        patch('app_helpers.services.text_importer_service.engine', test_session.bind),
        patch('app_helpers.services.archive_first_service.engine', test_session.bind),
        patch('app_helpers.services.archive_download_service.engine', test_session.bind),
        patch('app_helpers.services.auth_helpers.Session', mock_session),
        patch('app_helpers.services.auth.session_helpers.Session', mock_session),
        patch('app_helpers.services.auth.token_helpers.Session', mock_session),
        patch('app_helpers.services.auth.validation_helpers.Session', mock_session),
        patch('app_helpers.services.prayer_helpers.Session', mock_session),
        patch('app_helpers.services.invite_helpers.Session', mock_session),
        patch('app_helpers.services.archive_first_service.Session', mock_session),
        patch('app_helpers.routes.prayer_routes.Session', mock_session),
        patch('app_helpers.routes.prayer.feed_operations.Session', mock_session),
        patch('app_helpers.routes.prayer.prayer_operations.Session', mock_session),
        patch('app_helpers.routes.prayer.prayer_status.Session', mock_session),
        patch('app_helpers.routes.prayer.prayer_moderation.Session', mock_session),
        patch('app_helpers.routes.auth_routes.Session', mock_session),
        patch('app_helpers.routes.admin_routes.Session', mock_session),
        patch('app_helpers.routes.admin.dashboard.Session', mock_session),
        patch('app_helpers.routes.admin.auth_management.Session', mock_session),
        patch('app_helpers.routes.admin.analytics.Session', mock_session),
        patch('app_helpers.routes.admin.user_management.Session', mock_session),
        patch('app_helpers.routes.admin.moderation.Session', mock_session),
        patch('app_helpers.routes.user_routes.Session', mock_session),
        patch('app_helpers.routes.invite_routes.Session', mock_session),
    ]
    
    # Apply all patches
    for p in patches:
        p.start()
    
    try:
        yield TestClient(app)
    finally:
        # Clean up all patches
        for p in patches:
            p.stop()


@pytest.fixture(scope="function")
def mock_authenticated_user(test_session):
    """Mock the current_user function using FastAPI dependency override"""
    from app import app, current_user
    from unittest.mock import Mock
    
    # Create simple mock objects to avoid any database interaction
    user = Mock()
    user.display_name = "testuser"
    user.created_at = datetime.utcnow()
    user.religious_preference = "unspecified"
    user.prayer_style = None
    user.invited_by_username = None
    user.invite_token_used = None
    # Mock has_role method to return False (not admin)
    user.has_role.return_value = False
    
    session = Mock()
    session.id = "test_session_id"
    session.username = "testuser"
    session.created_at = datetime.utcnow()
    session.expires_at = datetime.utcnow() + timedelta(days=14)
    session.auth_request_id = None
    session.device_info = None
    session.ip_address = None
    session.is_fully_authenticated = True
    
    # Create real objects in test database for operations that need them
    real_user = UserFactory.create(display_name="testuser")
    real_session = SessionFactory.create(id="test_session_id", username="testuser", is_fully_authenticated=True)
    test_session.add_all([real_user, real_session])
    test_session.commit()
    
    # Override the dependency with mock objects (no database session binding)
    def override_current_user():
        return user, session
    
    app.dependency_overrides[current_user] = override_current_user
    
    yield user, session
    
    # Clean up the override
    if current_user in app.dependency_overrides:
        del app.dependency_overrides[current_user]


@pytest.fixture(scope="function")
def mock_half_authenticated_user(test_session):
    """Mock a user with pending authentication for testing permission restrictions"""
    from app import app, current_user
    from unittest.mock import Mock
    
    # Create simple mock objects to avoid any database interaction
    user = Mock()
    user.display_name = "pending_auth_user"
    user.created_at = datetime.utcnow()
    user.religious_preference = "unspecified"
    user.prayer_style = None
    user.invited_by_username = None
    user.invite_token_used = None
    # Mock has_role method to return False (not admin)
    user.has_role.return_value = False
    
    session = Mock()
    session.id = "test_half_auth_session_id"
    session.username = "pending_auth_user"
    session.created_at = datetime.utcnow()
    session.expires_at = datetime.utcnow() + timedelta(days=14)
    session.auth_request_id = None
    session.device_info = None
    session.ip_address = None
    session.is_fully_authenticated = False  # Half-authenticated
    
    # Create real objects in test database for operations that need them
    real_user = UserFactory.create(display_name="pending_auth_user")
    real_session = SessionFactory.create(id="test_half_auth_session_id", username="pending_auth_user", is_fully_authenticated=False)
    test_session.add_all([real_user, real_session])
    test_session.commit()
    
    # Override the dependency with mock objects (no database session binding)
    def override_current_user():
        return user, session
    
    app.dependency_overrides[current_user] = override_current_user
    
    yield user, session
    
    # Clean up the override
    if current_user in app.dependency_overrides:
        del app.dependency_overrides[current_user]


@pytest.fixture(scope="function")
def mock_admin_user(test_session):
    """Mock an admin user for testing admin permissions"""
    from app import app, current_user
    from unittest.mock import Mock
    
    # Create simple mock objects to avoid any database interaction
    user = Mock()
    user.display_name = "admin"  # Admin users have display_name="admin"
    user.created_at = datetime.utcnow()
    user.religious_preference = "unspecified"
    user.prayer_style = None
    user.invited_by_username = None
    user.invite_token_used = None
    
    session = Mock()
    session.id = "test_admin_session_id"
    session.username = "admin"
    session.created_at = datetime.utcnow()
    session.expires_at = datetime.utcnow() + timedelta(days=14)
    session.auth_request_id = None
    session.device_info = None
    session.ip_address = None
    session.is_fully_authenticated = True
    
    # Create real objects in test database for operations that need them
    real_user = UserFactory.create_admin()  # Creates user with display_name="admin"
    real_session = SessionFactory.create(id="test_admin_session_id", username="admin", is_fully_authenticated=True)
    test_session.add_all([real_user, real_session])
    test_session.commit()
    
    # Override the dependency with mock objects (no database session binding)
    def override_current_user():
        return user, session
    
    app.dependency_overrides[current_user] = override_current_user
    
    yield user, session
    
    # Clean up the override
    if current_user in app.dependency_overrides:
        del app.dependency_overrides[current_user]


@pytest.fixture(scope="function")  
def clean_db(test_session):
    """Ensure clean database state for each test"""
    # Delete all data from tables in correct order (respecting foreign keys)
    from sqlmodel import delete
    test_session.exec(delete(AuthAuditLog))
    test_session.exec(delete(SecurityLog))
    test_session.exec(delete(AuthApproval))
    test_session.exec(delete(AuthenticationRequest))
    test_session.exec(delete(PrayerActivityLog))
    test_session.exec(delete(PrayerAttribute))
    test_session.exec(delete(PrayerMark))
    test_session.exec(delete(SessionModel))
    test_session.exec(delete(Prayer))
    test_session.exec(delete(InviteToken))
    test_session.exec(delete(User))
    test_session.commit()
    return test_session


# Freeze time for consistent testing
@pytest.fixture
def frozen_time():
    """Provide a consistent datetime for testing"""
    return datetime(2024, 1, 15, 12, 0, 0)


# Mock external dependencies
@pytest.fixture
def mock_anthropic_client(monkeypatch):
    """Mock the Anthropic API client"""
    class MockResponse:
        def __init__(self, text):
            self.content = [type('obj', (object,), {'text': text})]
    
    class MockClient:
        def messages_create(self, **kwargs):
            return MockResponse("Divine Creator, we lift up our friend in prayer. Amen.")
    
    mock_client = MockClient()
    monkeypatch.setattr("app.anthropic_client", mock_client)
    return mock_client