import pytest
import tempfile
import os
from sqlmodel import Session, SQLModel, create_engine
from datetime import datetime, timedelta
import uuid

from models import User, Prayer, Session as SessionModel, InviteToken, PrayerMark, AuthenticationRequest, AuthApproval, AuthAuditLog, SecurityLog


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine using in-memory SQLite"""
    # Use in-memory SQLite for faster tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a test database session with automatic cleanup"""
    with Session(test_engine) as session:
        yield session
        # Cleanup happens automatically when session closes


@pytest.fixture(scope="function")  
def clean_db(test_session):
    """Ensure clean database state for each test"""
    # Delete all data from tables in correct order (respecting foreign keys)
    from sqlmodel import delete
    test_session.exec(delete(AuthAuditLog))
    test_session.exec(delete(SecurityLog))
    test_session.exec(delete(AuthApproval))
    test_session.exec(delete(AuthenticationRequest))
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