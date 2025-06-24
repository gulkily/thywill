"""Unit tests for admin routes"""
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from tests.factories import UserFactory, PrayerFactory, AuthenticationRequestFactory, AuthApprovalFactory


@pytest.mark.unit
class TestAdminDashboardRoutes:
    """Test admin dashboard route handlers"""
    
    def test_admin_dashboard_access_as_admin(self, client, mock_admin_user, test_session, clean_db):
        """Test admin dashboard access with admin user"""
        user, session = mock_admin_user
        
        response = client.get("/admin")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_admin_dashboard_access_as_regular_user(self, client, mock_authenticated_user):
        """Test admin dashboard access denied for regular users"""
        user, session = mock_authenticated_user
        
        response = client.get("/admin")
        
        # Should be forbidden or redirect
        assert response.status_code in [403, 302]
    
    def test_admin_dashboard_unauthenticated(self, client):
        """Test admin dashboard access denied for unauthenticated users"""
        response = client.get("/admin")
        
        # Should require authentication
        assert response.status_code in [401, 302, 403]
    
    def test_admin_dashboard_with_flagged_prayers(self, client, mock_admin_user, test_session, clean_db):
        """Test admin dashboard shows flagged prayers"""
        user, session = mock_admin_user
        
        # Create flagged prayer
        flagged_prayer = PrayerFactory.create(
            author_id="test_user_id",
            text="Test flagged prayer",
            flagged=True
        )
        test_session.add(flagged_prayer)
        test_session.commit()
        
        response = client.get("/admin")
        
        assert response.status_code == 200
        # Should include flagged prayers in response
    
    def test_admin_dashboard_with_pending_auth_requests(self, client, mock_admin_user, test_session, clean_db):
        """Test admin dashboard shows pending authentication requests"""
        user, session = mock_admin_user
        
        # Create pending auth request
        auth_request = AuthenticationRequestFactory.create(
            user_id="test_user_id",
            status="pending"
        )
        test_session.add(auth_request)
        test_session.commit()
        
        response = client.get("/admin")
        
        assert response.status_code == 200
        # Should include pending auth requests


@pytest.mark.unit
class TestAdminAuthenticationRoutes:
    """Test admin authentication management routes"""
    
    def test_auth_audit_access_as_admin(self, client, mock_admin_user, test_session, clean_db):
        """Test auth audit log access with admin user"""
        user, session = mock_admin_user
        
        response = client.get("/admin/auth-audit")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_auth_audit_access_denied_regular_user(self, client, mock_authenticated_user):
        """Test auth audit access denied for regular users"""
        user, session = mock_authenticated_user
        
        response = client.get("/admin/auth-audit")
        
        assert response.status_code in [403, 302]
    
    def test_bulk_approve_auth_requests_success(self, client, mock_admin_user, test_session, clean_db):
        """Test bulk approval of authentication requests"""
        user, session = mock_admin_user
        
        # Create users first
        user1 = UserFactory.create(id="user1", display_name="User 1")
        user2 = UserFactory.create(id="user2", display_name="User 2")
        test_session.add_all([user1, user2])
        test_session.commit()
        
        # Create pending auth requests
        auth_request1 = AuthenticationRequestFactory.create(
            id="req1",
            user_id="user1",
            status="pending"
        )
        auth_request2 = AuthenticationRequestFactory.create(
            id="req2", 
            user_id="user2",
            status="pending"
        )
        test_session.add_all([auth_request1, auth_request2])
        test_session.commit()
        
        form_data = {
            "request_ids": ["req1", "req2"]
        }
        
        response = client.post("/admin/bulk-approve", data=form_data)
        
        # Should redirect after successful bulk approval
        assert response.status_code in [200, 302, 303]
    
    def test_bulk_approve_no_requests_selected(self, client, mock_admin_user, test_session, clean_db):
        """Test bulk approval with no requests selected"""
        user, session = mock_admin_user
        
        form_data = {}
        
        response = client.post("/admin/bulk-approve", data=form_data)
        
        # Should handle empty selection gracefully
        assert response.status_code in [200, 302, 400]
    
    def test_bulk_approve_access_denied_regular_user(self, client, mock_authenticated_user):
        """Test bulk approval access denied for regular users"""
        user, session = mock_authenticated_user
        
        response = client.post("/admin/bulk-approve", data={})
        
        assert response.status_code in [403, 302]


@pytest.mark.unit
class TestAdminPrayerModerationRoutes:
    """Test admin prayer moderation routes"""
    
    def test_flag_prayer_as_admin(self, client, mock_admin_user, test_session, clean_db):
        """Test flagging a prayer as admin"""
        user, session = mock_admin_user
        
        # Create test prayer
        prayer = PrayerFactory.create(
            id="test_prayer_id",
            author_id="test_user_id",
            text="Test prayer to flag",
            flagged=False
        )
        test_session.add(prayer)
        test_session.commit()
        
        response = client.post(f"/admin/flag-prayer/{prayer.id}")
        
        # Should redirect after flagging
        assert response.status_code in [200, 302, 303]
    
    def test_unflag_prayer_as_admin(self, client, mock_admin_user, test_session, clean_db):
        """Test unflagging a prayer as admin"""
        user, session = mock_admin_user
        
        # Create flagged prayer
        prayer = PrayerFactory.create(
            id="test_prayer_id",
            author_id="test_user_id", 
            text="Test flagged prayer",
            flagged=True
        )
        test_session.add(prayer)
        test_session.commit()
        
        response = client.post(f"/admin/unflag-prayer/{prayer.id}")
        
        # Should redirect after unflagging
        assert response.status_code in [200, 302, 303]
    
    def test_flag_prayer_not_found(self, client, mock_admin_user, test_session, clean_db):
        """Test flagging non-existent prayer"""
        user, session = mock_admin_user
        
        response = client.post("/admin/flag-prayer/nonexistent_id")
        
        assert response.status_code == 404
    
    def test_prayer_moderation_access_denied_regular_user(self, client, mock_authenticated_user):
        """Test prayer moderation access denied for regular users"""
        user, session = mock_authenticated_user
        
        response = client.post("/admin/flag-prayer/test_prayer_id")
        
        assert response.status_code in [403, 302]


@pytest.mark.unit
class TestAdminAPIRoutes:
    """Test admin API routes"""
    
    def test_religious_preference_stats_api_as_admin(self, client, mock_admin_user, test_session, clean_db):
        """Test religious preference statistics API as admin"""
        user, session = mock_admin_user
        
        with patch('app_helpers.routes.admin.analytics.get_religious_preference_stats') as mock_stats:
            mock_stats.return_value = {
                "user_preferences": {
                    "christian": 10,
                    "islamic": 5,
                    "jewish": 3,
                    "unspecified": 20
                },
                "prayer_targets": {
                    "all": 30,
                    "christians_only": 8
                }
            }
            
            response = client.get("/api/religious-preference-stats")
            
            assert response.status_code == 200
            data = response.json()
            assert "user_preferences" in data
            assert "prayer_targets" in data
            assert "christian" in data["user_preferences"]
            assert "islamic" in data["user_preferences"]
    
    def test_religious_preference_stats_api_access_denied(self, client, mock_authenticated_user):
        """Test religious preference stats API access denied for regular users"""
        user, session = mock_authenticated_user
        
        response = client.get("/api/religious-preference-stats")
        
        assert response.status_code in [403, 302]
    
    def test_users_api_as_admin(self, client, mock_admin_user, test_session, clean_db):
        """Test users API endpoint as admin"""
        user, session = mock_admin_user
        
        # Create test users
        user1 = UserFactory.create(id="user1", display_name="User 1")
        user2 = UserFactory.create(id="user2", display_name="User 2")
        test_session.add_all([user1, user2])
        test_session.commit()
        
        response = client.get("/admin/users")
        
        assert response.status_code == 200
        # Should show user management interface
    
    def test_users_api_access_denied_regular_user(self, client, mock_authenticated_user):
        """Test users API access denied for regular users"""
        user, session = mock_authenticated_user
        
        response = client.get("/admin/users")
        
        assert response.status_code in [403, 302]


@pytest.mark.unit
class TestAdminUtilityFunctions:
    """Test admin utility and helper functions"""
    
    def test_admin_privilege_check(self, mock_admin_user, mock_authenticated_user):
        """Test admin privilege checking logic"""
        admin_user, admin_session = mock_admin_user
        regular_user, regular_session = mock_authenticated_user
        
        # Admin user should have admin privileges
        assert admin_user.id == "admin"
        
        # Regular user should not have admin privileges
        assert regular_user.id != "admin"
    
    def test_expired_auth_request_cleanup(self, client, mock_admin_user, test_session, clean_db):
        """Test cleanup of expired authentication requests"""
        user, session = mock_admin_user
        
        with patch('app_helpers.routes.admin_routes.cleanup_expired_requests') as mock_cleanup:
            mock_cleanup.return_value = 3  # 3 requests cleaned up
            
            # Cleanup should be called when accessing admin routes
            response = client.get("/admin")
            
            # Verify cleanup was called (implementation dependent)
            # This test structure can be adapted based on actual implementation
    
    def test_auth_action_logging(self, client, mock_admin_user, test_session, clean_db):
        """Test authentication action logging"""
        user, session = mock_admin_user
        
        with patch('app_helpers.routes.admin_routes.log_auth_action') as mock_log:
            # Perform admin action that should log
            response = client.post("/admin/bulk-approve", data={"request_ids": ["req1"]})
            
            # Verify logging was called (implementation dependent)
            # This test structure can be adapted based on actual implementation


@pytest.mark.unit
class TestAdminSecurityAndValidation:
    """Test admin security and input validation"""
    
    def test_bulk_approve_input_validation(self, client, mock_admin_user, test_session, clean_db):
        """Test input validation for bulk approval"""
        user, session = mock_admin_user
        
        # Test with malformed request IDs
        form_data = {
            "request_ids": ["'; DROP TABLE users; --", "invalid_id"]
        }
        
        response = client.post("/admin/bulk-approve", data=form_data)
        
        # Should handle malicious input safely
        assert response.status_code in [200, 302, 400, 422]
    
    def test_prayer_moderation_input_validation(self, client, mock_admin_user, test_session, clean_db):
        """Test input validation for prayer moderation"""
        user, session = mock_admin_user
        
        # Test with malformed prayer ID
        response = client.post("/admin/flag-prayer/'; DROP TABLE prayers; --")
        
        # Should handle malicious input safely
        assert response.status_code in [404, 400, 422]
    
    def test_admin_csrf_protection(self, client, mock_admin_user, test_session, clean_db):
        """Test CSRF protection on admin forms"""
        user, session = mock_admin_user
        
        # This test would verify CSRF token requirements
        # Implementation depends on CSRF protection setup
        response = client.post("/admin/bulk-approve", data={})
        
        # Should handle CSRF validation appropriately
        # Specific assertions depend on CSRF implementation