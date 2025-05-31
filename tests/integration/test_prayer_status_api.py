"""Integration tests for prayer status management API endpoints"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import app
from models import Prayer, PrayerAttribute, PrayerActivityLog
from tests.factories import UserFactory, PrayerFactory, SessionFactory


@pytest.fixture
def client():
    """Test client for API testing"""
    return TestClient(app)


@pytest.fixture
def authenticated_user_session(test_session):
    """Create authenticated user with valid session cookie"""
    user = UserFactory.create()
    session = SessionFactory.create(user_id=user.id, is_fully_authenticated=True)
    test_session.add_all([user, session])
    test_session.commit()
    return user, session


@pytest.mark.integration
class TestArchiveEndpoints:
    """Test prayer archive and restore API endpoints"""
    
    def test_archive_prayer_success(self, client, test_session, authenticated_user_session):
        """Test successful prayer archiving"""
        user, session = authenticated_user_session
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add(prayer)
        test_session.commit()
        
        # Set session cookie
        client.cookies.set("session_id", session.id)
        
        # Archive prayer
        response = client.post(f"/prayer/{prayer.id}/archive")
        
        assert response.status_code == 303  # Redirect
        
        # Verify prayer is archived
        test_session.refresh(prayer)
        assert prayer.is_archived(test_session) == True
    
    def test_archive_prayer_htmx_response(self, client, test_session, authenticated_user_session):
        """Test HTMX response for prayer archiving"""
        user, session = authenticated_user_session
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add(prayer)
        test_session.commit()
        
        # Set session cookie and HTMX header
        client.cookies.set("session_id", session.id)
        
        response = client.post(
            f"/prayer/{prayer.id}/archive",
            headers={"HX-Request": "true"}
        )
        
        assert response.status_code == 200
        assert "Prayer archived successfully" in response.text
        assert "bg-amber-50" in response.text  # Styling check
    
    def test_archive_prayer_unauthorized(self, client, test_session):
        """Test archiving prayer without authentication"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # No session cookie
        response = client.post(f"/prayer/{prayer.id}/archive")
        
        assert response.status_code == 401  # Unauthorized
    
    def test_archive_prayer_not_author(self, client, test_session):
        """Test archiving prayer by non-author"""
        author = UserFactory.create(display_name="Author")
        other_user = UserFactory.create(display_name="Other User")
        prayer = PrayerFactory.create(author_id=author.id)
        session = SessionFactory.create(user_id=other_user.id, is_fully_authenticated=True)
        
        test_session.add_all([author, other_user, prayer, session])
        test_session.commit()
        
        # Set session cookie for non-author
        client.cookies.set("session_id", session.id)
        
        response = client.post(f"/prayer/{prayer.id}/archive")
        
        assert response.status_code == 403  # Forbidden
    
    def test_restore_prayer_success(self, client, test_session, authenticated_user_session):
        """Test successful prayer restoration"""
        user, session = authenticated_user_session
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add(prayer)
        test_session.commit()
        
        # Archive prayer first
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        
        # Set session cookie
        client.cookies.set("session_id", session.id)
        
        # Restore prayer
        response = client.post(f"/prayer/{prayer.id}/restore")
        
        assert response.status_code == 303  # Redirect
        
        # Verify prayer is no longer archived
        test_session.refresh(prayer)
        assert prayer.is_archived(test_session) == False
    
    def test_restore_prayer_htmx_response(self, client, test_session, authenticated_user_session):
        """Test HTMX response for prayer restoration"""
        user, session = authenticated_user_session
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add(prayer)
        test_session.commit()
        
        # Archive prayer first
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        
        # Set session cookie and HTMX header
        client.cookies.set("session_id", session.id)
        
        response = client.post(
            f"/prayer/{prayer.id}/restore",
            headers={"HX-Request": "true"}
        )
        
        assert response.status_code == 200
        assert "Prayer restored successfully" in response.text
        assert "bg-green-50" in response.text  # Styling check
    
    def test_archive_nonexistent_prayer(self, client, test_session, authenticated_user_session):
        """Test archiving non-existent prayer"""
        user, session = authenticated_user_session
        
        # Set session cookie
        client.cookies.set("session_id", session.id)
        
        response = client.post("/prayer/nonexistent_id/archive")
        
        assert response.status_code == 404


@pytest.mark.integration
class TestAnsweredEndpoints:
    """Test answered prayer API endpoints"""
    
    def test_mark_prayer_answered_basic(self, client, test_session, authenticated_user_session):
        """Test marking prayer as answered without testimony"""
        user, session = authenticated_user_session
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add(prayer)
        test_session.commit()
        
        # Set session cookie
        client.cookies.set("session_id", session.id)
        
        # Mark prayer as answered
        response = client.post(f"/prayer/{prayer.id}/answered")
        
        assert response.status_code == 303  # Redirect
        
        # Verify prayer is answered
        test_session.refresh(prayer)
        assert prayer.is_answered(test_session) == True
        assert prayer.answer_date(test_session) is not None
    
    def test_mark_prayer_answered_with_testimony(self, client, test_session, authenticated_user_session):
        """Test marking prayer as answered with testimony"""
        user, session = authenticated_user_session
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add(prayer)
        test_session.commit()
        
        # Set session cookie
        client.cookies.set("session_id", session.id)
        
        # Mark prayer as answered with testimony
        testimony = "God provided exactly what I needed!"
        response = client.post(
            f"/prayer/{prayer.id}/answered",
            data={"testimony": testimony}
        )
        
        assert response.status_code == 303  # Redirect
        
        # Verify prayer is answered with testimony
        test_session.refresh(prayer)
        assert prayer.is_answered(test_session) == True
        assert prayer.answer_testimony(test_session) == testimony
    
    def test_mark_prayer_answered_htmx_response(self, client, test_session, authenticated_user_session):
        """Test HTMX response for marking prayer as answered"""
        user, session = authenticated_user_session
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add(prayer)
        test_session.commit()
        
        # Set session cookie and HTMX header
        client.cookies.set("session_id", session.id)
        
        response = client.post(
            f"/prayer/{prayer.id}/answered",
            headers={"HX-Request": "true"},
            data={"testimony": "Praise the Lord!"}
        )
        
        assert response.status_code == 200
        assert "Prayer Answered!" in response.text
        assert "celebration feed" in response.text
        assert "bg-green-100" in response.text  # Celebration styling
    
    def test_mark_prayer_answered_not_author(self, client, test_session):
        """Test marking prayer as answered by non-author"""
        author = UserFactory.create(display_name="Author")
        other_user = UserFactory.create(display_name="Other User")
        prayer = PrayerFactory.create(author_id=author.id)
        session = SessionFactory.create(user_id=other_user.id, is_fully_authenticated=True)
        
        test_session.add_all([author, other_user, prayer, session])
        test_session.commit()
        
        # Set session cookie for non-author
        client.cookies.set("session_id", session.id)
        
        response = client.post(f"/prayer/{prayer.id}/answered")
        
        assert response.status_code == 403  # Forbidden
    
    def test_answered_celebration_page(self, client, test_session, authenticated_user_session):
        """Test answered prayers celebration page"""
        user, session = authenticated_user_session
        
        # Create answered prayer
        prayer = PrayerFactory.create(author_id=user.id, text="Test prayer")
        test_session.add(prayer)
        test_session.commit()
        
        prayer.set_attribute('answered', 'true', user.id, test_session)
        prayer.set_attribute('answer_testimony', 'God is faithful!', user.id, test_session)
        test_session.commit()
        
        # Set session cookie
        client.cookies.set("session_id", session.id)
        
        # Access celebration page
        response = client.get("/answered")
        
        assert response.status_code == 200
        assert "Answered Prayers" in response.text
        assert "Celebrating how God has moved" in response.text
        assert "Test prayer" in response.text
        assert "God is faithful!" in response.text


@pytest.mark.integration
class TestPermissionChecks:
    """Test authorization for prayer status changes"""
    
    def test_half_authenticated_user_cannot_manage_prayers(self, client, test_session):
        """Test that half-authenticated users cannot manage prayer status"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        session = SessionFactory.create(user_id=user.id, is_fully_authenticated=False)
        
        test_session.add_all([user, prayer, session])
        test_session.commit()
        
        # Set session cookie for half-authenticated user
        client.cookies.set("session_id", session.id)
        
        # Try to archive prayer
        response = client.post(f"/prayer/{prayer.id}/archive")
        assert response.status_code == 403  # Forbidden
        
        # Try to mark as answered
        response = client.post(f"/prayer/{prayer.id}/answered")
        assert response.status_code == 403  # Forbidden
    
    def test_admin_can_manage_any_prayer(self, client, test_session):
        """Test that admin users can manage any prayer"""
        admin = UserFactory.create_admin()  # Creates user with id="admin"
        author = UserFactory.create(display_name="Regular User")
        prayer = PrayerFactory.create(author_id=author.id)
        session = SessionFactory.create(user_id=admin.id, is_fully_authenticated=True)
        
        test_session.add_all([admin, author, prayer, session])
        test_session.commit()
        
        # Set session cookie for admin
        client.cookies.set("session_id", session.id)
        
        # Admin should be able to archive prayer
        response = client.post(f"/prayer/{prayer.id}/archive")
        assert response.status_code == 303  # Success (redirect)
        
        # Verify prayer was archived
        test_session.refresh(prayer)
        assert prayer.is_archived(test_session) == True
    
    def test_session_expiry_blocks_access(self, client, test_session):
        """Test that expired sessions cannot manage prayers"""
        from datetime import timedelta
        
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        
        # Create expired session
        expired_time = datetime.utcnow() - timedelta(days=1)
        session = SessionFactory.create(
            user_id=user.id, 
            expires_at=expired_time,
            is_fully_authenticated=True
        )
        
        test_session.add_all([user, prayer, session])
        test_session.commit()
        
        # Set expired session cookie
        client.cookies.set("session_id", session.id)
        
        # Should be unauthorized
        response = client.post(f"/prayer/{prayer.id}/archive")
        assert response.status_code == 401  # Unauthorized


@pytest.mark.integration
class TestHTMXResponses:
    """Test HTMX-specific response formats"""
    
    def test_htmx_headers_detected(self, client, test_session, authenticated_user_session):
        """Test that HTMX headers are properly detected"""
        user, session = authenticated_user_session
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add(prayer)
        test_session.commit()
        
        # Set session cookie
        client.cookies.set("session_id", session.id)
        
        # Test with HTMX header
        response_htmx = client.post(
            f"/prayer/{prayer.id}/archive",
            headers={"HX-Request": "true"}
        )
        
        # Test without HTMX header
        prayer.remove_attribute('archived', test_session, user.id)
        test_session.commit()
        
        response_normal = client.post(f"/prayer/{prayer.id}/archive")
        
        # HTMX should return HTML content
        assert response_htmx.status_code == 200
        assert "text/html" in response_htmx.headers.get("content-type", "")
        
        # Normal should redirect
        assert response_normal.status_code == 303
    
    def test_htmx_response_content_format(self, client, test_session, authenticated_user_session):
        """Test HTMX response content formatting"""
        user, session = authenticated_user_session
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add(prayer)
        test_session.commit()
        
        # Set session cookie
        client.cookies.set("session_id", session.id)
        
        # Test archive HTMX response
        response = client.post(
            f"/prayer/{prayer.id}/archive",
            headers={"HX-Request": "true"}
        )
        
        assert response.status_code == 200
        
        # Should contain proper CSS classes and structure
        content = response.text
        assert 'class="prayer-archived' in content
        assert 'bg-amber-50' in content
        assert 'Prayer archived successfully' in content
        
        # Test answered HTMX response
        prayer.remove_attribute('archived', test_session, user.id)
        test_session.commit()
        
        response = client.post(
            f"/prayer/{prayer.id}/answered",
            headers={"HX-Request": "true"},
            data={"testimony": "Hallelujah!"}
        )
        
        assert response.status_code == 200
        content = response.text
        assert 'class="prayer-answered' in content
        assert 'bg-green-100' in content
        assert 'Prayer Answered!' in content
        assert 'celebration feed' in content


@pytest.mark.integration
class TestActivityLogging:
    """Test that API endpoints create proper activity logs"""
    
    def test_archive_creates_activity_log(self, client, test_session, authenticated_user_session):
        """Test that archiving creates activity log"""
        user, session = authenticated_user_session
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add(prayer)
        test_session.commit()
        
        # Count initial logs
        initial_count = len(test_session.exec(select(PrayerActivityLog)).all())
        
        # Set session cookie
        client.cookies.set("session_id", session.id)
        
        # Archive prayer
        response = client.post(f"/prayer/{prayer.id}/archive")
        assert response.status_code == 303
        
        # Should have created activity log
        logs = test_session.exec(select(PrayerActivityLog)).all()
        assert len(logs) == initial_count + 1
        
        # Verify log content
        log = logs[-1]
        assert log.prayer_id == prayer.id
        assert log.user_id == user.id
        assert log.action == 'set_archived'
        assert log.new_value == 'true'
    
    def test_answered_creates_multiple_logs(self, client, test_session, authenticated_user_session):
        """Test that marking as answered creates multiple activity logs"""
        user, session = authenticated_user_session
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add(prayer)
        test_session.commit()
        
        # Count initial logs
        initial_count = len(test_session.exec(select(PrayerActivityLog)).all())
        
        # Set session cookie
        client.cookies.set("session_id", session.id)
        
        # Mark as answered with testimony
        response = client.post(
            f"/prayer/{prayer.id}/answered",
            data={"testimony": "Praise God!"}
        )
        assert response.status_code == 303
        
        # Should have created multiple activity logs
        logs = test_session.exec(select(PrayerActivityLog)).all()
        
        # Should create logs for: answered, answer_date, answer_testimony
        assert len(logs) >= initial_count + 3
        
        # Verify log actions
        recent_logs = logs[-3:]
        actions = [log.action for log in recent_logs]
        assert 'set_answered' in actions
        assert 'set_answer_date' in actions
        assert 'set_answer_testimony' in actions