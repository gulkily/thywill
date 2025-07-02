"""Integration tests for prayer status management API endpoints"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import app
from models import Prayer, PrayerAttribute, PrayerActivityLog
from tests.factories import UserFactory, PrayerFactory, SessionFactory



@pytest.mark.integration
class TestArchiveEndpoints:
    """Test prayer archive and restore API endpoints"""
    
    def test_archive_prayer_success(self, client, test_session, mock_authenticated_user):
        """Test successful prayer archiving"""
        user, session = mock_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # Archive prayer - no need to set cookies since current_user is mocked
        response = client.post(f"/prayer/{prayer_id}/archive", follow_redirects=False)
        
        assert response.status_code == 303  # Redirect
        
        # Verify prayer is archived by re-fetching from test database
        updated_prayer = test_session.get(Prayer, prayer_id)
        assert updated_prayer is not None
        assert updated_prayer.is_archived(test_session) == True
    
    def test_archive_prayer_htmx_response(self, client, test_session, mock_authenticated_user):
        """Test HTMX response for prayer archiving"""
        user, session = mock_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        response = client.post(
            f"/prayer/{prayer_id}/archive",
            headers={"HX-Request": "true"}
        )
        
        assert response.status_code == 200
        assert "Prayer archived successfully" in response.text
        assert "bg-amber-50" in response.text  # Styling check
    
    def test_archive_prayer_unauthorized(self, client, test_session):
        """Test archiving prayer without authentication"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # No session cookie
        response = client.post(f"/prayer/{prayer.id}/archive")
        
        assert response.status_code == 401  # Unauthorized
    
    def test_archive_prayer_not_author(self, client, test_session, mock_authenticated_user):
        """Test archiving prayer by non-author"""
        user, session = mock_authenticated_user
        author = UserFactory.create(display_name="Author")
        prayer = PrayerFactory.create(author_username=author.id)
        test_session.add_all([author, prayer])
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # User tries to archive someone else's prayer
        response = client.post(f"/prayer/{prayer_id}/archive", follow_redirects=False)
        
        assert response.status_code == 403  # Forbidden
    
    def test_restore_prayer_success(self, client, test_session, mock_authenticated_user):
        """Test successful prayer restoration"""
        user, session = mock_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Archive prayer first
        prayer.set_attribute('archived', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # Restore prayer
        response = client.post(f"/prayer/{prayer_id}/restore", follow_redirects=False)
        
        assert response.status_code == 303  # Redirect
        
        # Verify prayer is no longer archived by re-fetching from test database
        updated_prayer = test_session.get(Prayer, prayer_id)
        assert updated_prayer is not None
        assert updated_prayer.is_archived(test_session) == False
    
    def test_restore_prayer_htmx_response(self, client, test_session, mock_authenticated_user):
        """Test HTMX response for prayer restoration"""
        user, session = mock_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Archive prayer first
        prayer.set_attribute('archived', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        response = client.post(
            f"/prayer/{prayer_id}/restore",
            headers={"HX-Request": "true"}
        )
        
        assert response.status_code == 200
        assert "Prayer restored successfully" in response.text
        assert "bg-green-50" in response.text  # Styling check
    
    def test_archive_nonexistent_prayer(self, client, test_session, mock_authenticated_user):
        """Test archiving non-existent prayer"""
        user, session = mock_authenticated_user
        
        response = client.post("/prayer/nonexistent_id/archive", follow_redirects=False)
        
        assert response.status_code == 404


@pytest.mark.integration
class TestAnsweredEndpoints:
    """Test answered prayer API endpoints"""
    
    def test_mark_prayer_answered_basic(self, client, test_session, mock_authenticated_user):
        """Test marking prayer as answered without testimony"""
        user, session = mock_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # Mark prayer as answered
        response = client.post(f"/prayer/{prayer_id}/answered", follow_redirects=False)
        
        assert response.status_code == 303  # Redirect
        
        # Verify prayer is answered by re-fetching from test database
        updated_prayer = test_session.get(Prayer, prayer_id)
        assert updated_prayer is not None
        assert updated_prayer.is_answered(test_session) == True
        assert updated_prayer.answer_date(test_session) is not None
    
    def test_mark_prayer_answered_with_testimony(self, client, test_session, mock_authenticated_user):
        """Test marking prayer as answered with testimony"""
        user, session = mock_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # Mark prayer as answered with testimony
        testimony = "God provided exactly what I needed!"
        response = client.post(
            f"/prayer/{prayer_id}/answered",
            data={"testimony": testimony},
            follow_redirects=False
        )
        
        assert response.status_code == 303  # Redirect
        
        # Verify prayer is answered with testimony by re-fetching from test database
        updated_prayer = test_session.get(Prayer, prayer_id)
        assert updated_prayer is not None
        assert updated_prayer.is_answered(test_session) == True
        assert updated_prayer.answer_testimony(test_session) == testimony
    
    def test_mark_prayer_answered_htmx_response(self, client, test_session, mock_authenticated_user):
        """Test HTMX response for marking prayer as answered"""
        user, session = mock_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        response = client.post(
            f"/prayer/{prayer_id}/answered",
            headers={"HX-Request": "true"},
            data={"testimony": "Praise the Lord!"}
        )
        
        assert response.status_code == 200
        assert "Prayer Answered!" in response.text
        assert "celebration feed" in response.text
        assert "bg-green-100" in response.text  # Celebration styling
    
    def test_mark_prayer_answered_not_author(self, client, test_session, mock_authenticated_user):
        """Test marking prayer as answered by non-author"""
        user, session = mock_authenticated_user
        author = UserFactory.create(display_name="Author")
        prayer = PrayerFactory.create(author_username=author.id)
        test_session.add_all([author, prayer])
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # User tries to mark someone else's prayer as answered
        response = client.post(f"/prayer/{prayer_id}/answered", follow_redirects=False)
        
        assert response.status_code == 403  # Forbidden
    
    def test_answered_celebration_page(self, client, test_session, mock_authenticated_user):
        """Test answered prayers celebration page"""
        user, session = mock_authenticated_user
        
        # Create answered prayer
        prayer = PrayerFactory.create(author_username=user.display_name, text="Test prayer")
        test_session.add(prayer)
        test_session.commit()
        
        prayer.set_attribute('answered', 'true', user.display_name, test_session)
        prayer.set_attribute('answer_testimony', 'God is faithful!', user.display_name, test_session)
        test_session.commit()
        
        # Access celebration page - no need to set cookies since current_user is mocked
        response = client.get("/answered")
        
        assert response.status_code == 200
        assert "Answered Prayers" in response.text
        assert "Celebrating how God has moved" in response.text
        assert "Test prayer" in response.text
        assert "God is faithful!" in response.text


@pytest.mark.integration
class TestPermissionChecks:
    """Test authorization for prayer status changes"""
    
    def test_pending_authentication_user_cannot_manage_prayers(self, client, test_session, mock_half_authenticated_user):
        """Test that users with pending authentication cannot manage prayer status"""
        user, session = mock_half_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # Try to archive prayer
        response = client.post(f"/prayer/{prayer_id}/archive", follow_redirects=False)
        assert response.status_code == 403  # Forbidden
        
        # Try to mark as answered
        response = client.post(f"/prayer/{prayer_id}/answered", follow_redirects=False)
        assert response.status_code == 403  # Forbidden
    
    def test_admin_can_manage_any_prayer(self, client, test_session, mock_admin_user):
        """Test that admin users can manage any prayer"""
        admin, session = mock_admin_user
        author = UserFactory.create(display_name="Regular User")
        prayer = PrayerFactory.create(author_username=author.id)
        
        test_session.add_all([author, prayer])
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # Admin should be able to archive prayer
        response = client.post(f"/prayer/{prayer_id}/archive", follow_redirects=False)
        assert response.status_code == 303  # Success (redirect)
        
        # Verify prayer was archived by re-fetching from test database
        updated_prayer = test_session.get(Prayer, prayer_id)
        assert updated_prayer is not None
        assert updated_prayer.is_archived(test_session) == True
    
    def test_session_expiry_blocks_access(self, client, test_session):
        """Test that expired sessions cannot manage prayers"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # No session cookie set - should be unauthorized
        response = client.post(f"/prayer/{prayer_id}/archive", follow_redirects=False)
        assert response.status_code == 401  # Unauthorized


@pytest.mark.integration
class TestHTMXResponses:
    """Test HTMX-specific response formats"""
    
    def test_htmx_headers_detected(self, client, test_session, mock_authenticated_user):
        """Test that HTMX headers are properly detected"""
        user, session = mock_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # Test with HTMX header
        response_htmx = client.post(
            f"/prayer/{prayer_id}/archive",
            headers={"HX-Request": "true"}
        )
        
        # Test without HTMX header - restore prayer first
        updated_prayer = test_session.get(Prayer, prayer_id)
        updated_prayer.remove_attribute('archived', test_session, user.display_name)
        test_session.commit()
        
        response_normal = client.post(f"/prayer/{prayer_id}/archive", follow_redirects=False)
        
        # HTMX should return HTML content
        assert response_htmx.status_code == 200
        assert "text/html" in response_htmx.headers.get("content-type", "")
        
        # Normal should redirect
        assert response_normal.status_code == 303
    
    def test_htmx_response_content_format(self, client, test_session, mock_authenticated_user):
        """Test HTMX response content formatting"""
        user, session = mock_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # Test archive HTMX response
        response = client.post(
            f"/prayer/{prayer_id}/archive",
            headers={"HX-Request": "true"}
        )
        
        assert response.status_code == 200
        
        # Should contain proper CSS classes and structure
        content = response.text
        assert 'class="prayer-archived' in content
        assert 'bg-amber-50' in content
        assert 'Prayer archived successfully' in content
        
        # Test answered HTMX response - restore prayer first
        updated_prayer = test_session.get(Prayer, prayer_id)
        updated_prayer.remove_attribute('archived', test_session, user.display_name)
        test_session.commit()
        
        response = client.post(
            f"/prayer/{prayer_id}/answered",
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
    
    def test_archive_creates_activity_log(self, client, test_session, mock_authenticated_user):
        """Test that archiving creates activity log"""
        user, session = mock_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Count initial logs
        initial_count = len(test_session.exec(select(PrayerActivityLog)).all())
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        user_id = user.display_name
        
        # Archive prayer
        response = client.post(f"/prayer/{prayer_id}/archive", follow_redirects=False)
        assert response.status_code == 303
        
        # Should have created activity log
        logs = test_session.exec(select(PrayerActivityLog)).all()
        assert len(logs) == initial_count + 1
        
        # Verify log content
        log = logs[-1]
        assert log.prayer_id == prayer_id
        assert log.user_id == user_id
        assert log.action == 'set_archived'
        assert log.new_value == 'true'
    
    def test_answered_creates_multiple_logs(self, client, test_session, mock_authenticated_user):
        """Test that marking as answered creates multiple activity logs"""
        user, session = mock_authenticated_user
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        # Count initial logs
        initial_count = len(test_session.exec(select(PrayerActivityLog)).all())
        
        # Store prayer ID before API call to avoid detached instance issues
        prayer_id = prayer.id
        
        # Mark as answered with testimony
        response = client.post(
            f"/prayer/{prayer_id}/answered",
            data={"testimony": "Praise God!"},
            follow_redirects=False
        )
        assert response.status_code == 303
        
        # Should have created multiple activity logs
        logs = test_session.exec(select(PrayerActivityLog)).all()
        
        # Should create logs for: answered, answer_date, answer_testimony, testimony
        assert len(logs) >= initial_count + 3
        
        # Verify log actions - get all logs created by this operation
        recent_logs = logs[initial_count:]
        actions = [log.action for log in recent_logs]
        assert 'set_answered' in actions
        assert 'set_answer_date' in actions
        assert 'set_answer_testimony' in actions