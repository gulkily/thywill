import pytest
import tempfile
import os
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta
import uuid
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from models import User, Prayer, Session as SessionModel, InviteToken, PrayerMark, AuthenticationRequest, AuthApproval, AuthAuditLog, SecurityLog, PrayerAttribute, PrayerActivityLog
from tests.factories import UserFactory, SessionFactory


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine using in-memory SQLite"""
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
    
    # Patch Session creation throughout the app and helper modules
    with patch('app.Session', mock_session), \
         patch('app_helpers.services.auth_helpers.Session', mock_session), \
         patch('app_helpers.services.prayer_helpers.Session', mock_session), \
         patch('app_helpers.services.invite_helpers.Session', mock_session), \
         patch('app_helpers.routes.prayer_routes.Session', mock_session), \
         patch('app_helpers.routes.auth_routes.Session', mock_session), \
         patch('app_helpers.routes.admin_routes.Session', mock_session), \
         patch('app_helpers.routes.user_routes.Session', mock_session), \
         patch('app_helpers.routes.invite_routes.Session', mock_session):
        yield TestClient(app)


@pytest.fixture(scope="function")
def mock_authenticated_user(test_session):
    """Mock the current_user function using FastAPI dependency override"""
    from app import app, current_user
    from unittest.mock import Mock
    
    # Create simple mock objects to avoid any database interaction
    user = Mock()
    user.id = "test_user_id"
    user.display_name = "Test User"
    user.created_at = datetime.utcnow()
    user.religious_preference = "unspecified"
    user.prayer_style = None
    user.invited_by_user_id = None
    user.invite_token_used = None
    
    session = Mock()
    session.id = "test_session_id"
    session.user_id = "test_user_id"
    session.created_at = datetime.utcnow()
    session.expires_at = datetime.utcnow() + timedelta(days=14)
    session.auth_request_id = None
    session.device_info = None
    session.ip_address = None
    session.is_fully_authenticated = True
    
    # Create real objects in test database for operations that need them
    real_user = UserFactory.create(id="test_user_id", display_name="Test User")
    real_session = SessionFactory.create(id="test_session_id", user_id="test_user_id", is_fully_authenticated=True)
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
    """Mock a half-authenticated user for testing permission restrictions"""
    from app import app, current_user
    from unittest.mock import Mock
    
    # Create simple mock objects to avoid any database interaction
    user = Mock()
    user.id = "test_half_auth_user_id"
    user.display_name = "Half Auth User"
    user.created_at = datetime.utcnow()
    user.religious_preference = "unspecified"
    user.prayer_style = None
    user.invited_by_user_id = None
    user.invite_token_used = None
    
    session = Mock()
    session.id = "test_half_auth_session_id"
    session.user_id = "test_half_auth_user_id"
    session.created_at = datetime.utcnow()
    session.expires_at = datetime.utcnow() + timedelta(days=14)
    session.auth_request_id = None
    session.device_info = None
    session.ip_address = None
    session.is_fully_authenticated = False  # Half-authenticated
    
    # Create real objects in test database for operations that need them
    real_user = UserFactory.create(id="test_half_auth_user_id", display_name="Half Auth User")
    real_session = SessionFactory.create(id="test_half_auth_session_id", user_id="test_half_auth_user_id", is_fully_authenticated=False)
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
    user.id = "admin"  # Admin users have id="admin"
    user.display_name = "Admin User"
    user.created_at = datetime.utcnow()
    user.religious_preference = "unspecified"
    user.prayer_style = None
    user.invited_by_user_id = None
    user.invite_token_used = None
    
    session = Mock()
    session.id = "test_admin_session_id"
    session.user_id = "admin"
    session.created_at = datetime.utcnow()
    session.expires_at = datetime.utcnow() + timedelta(days=14)
    session.auth_request_id = None
    session.device_info = None
    session.ip_address = None
    session.is_fully_authenticated = True
    
    # Create real objects in test database for operations that need them
    real_user = UserFactory.create_admin()  # Creates user with id="admin"
    real_session = SessionFactory.create(id="test_admin_session_id", user_id="admin", is_fully_authenticated=True)
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