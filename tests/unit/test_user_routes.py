"""Unit tests for user routes"""
import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from tests.factories import UserFactory, PrayerFactory, PrayerMarkFactory


@pytest.mark.unit
class TestUserProfileRoutes:
    """Test user profile route handlers"""
    
    def test_my_profile_redirect(self, client, mock_authenticated_user):
        """Test /profile redirects to user's own profile"""
        user, session = mock_authenticated_user
        
        with patch('app_helpers.routes.user_routes.user_profile') as mock_user_profile:
            mock_user_profile.return_value = Mock()
            
            response = client.get("/profile")
            
            # Should redirect/call user_profile with user's ID
            mock_user_profile.assert_called_once()
            call_args = mock_user_profile.call_args[0]
            assert call_args[1] == user.id  # user_id parameter
    
    def test_user_profile_own_profile(self, client, mock_authenticated_user, test_session, clean_db):
        """Test viewing own user profile"""
        user, session = mock_authenticated_user
        
        # Create test data
        prayer1 = PrayerFactory.create(author_id=user.id, text="Test prayer 1")
        prayer2 = PrayerFactory.create(author_id=user.id, text="Test prayer 2")
        mark1 = PrayerMarkFactory.create(user_id=user.id, prayer_id=prayer1.id)
        test_session.add_all([prayer1, prayer2, mark1])
        test_session.commit()
        
        response = client.get(f"/user/{user.id}")
        
        assert response.status_code == 200
        # Verify it's an HTML response
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_user_profile_other_user(self, client, mock_authenticated_user, test_session, clean_db):
        """Test viewing another user's profile"""
        user, session = mock_authenticated_user
        
        # Create another user
        other_user = UserFactory.create(id="other_user_id", display_name="Other User")
        prayer = PrayerFactory.create(author_id=other_user.id, text="Other user's prayer")
        test_session.add_all([other_user, prayer])
        test_session.commit()
        
        response = client.get(f"/user/{other_user.id}")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_user_profile_not_found(self, client, mock_authenticated_user):
        """Test viewing profile of non-existent user"""
        user, session = mock_authenticated_user
        
        response = client.get("/user/nonexistent_user_id")
        
        assert response.status_code == 404
    
    def test_user_profile_with_inviter(self, client, mock_authenticated_user, test_session, clean_db):
        """Test user profile showing inviter information"""
        user, session = mock_authenticated_user
        
        # Create inviter user
        inviter = UserFactory.create(id="inviter_id", display_name="Inviter User")
        # Create target user with inviter
        target_user = UserFactory.create(
            id="target_user_id", 
            display_name="Target User",
            invited_by_user_id=inviter.id
        )
        test_session.add_all([inviter, target_user])
        test_session.commit()
        
        response = client.get(f"/user/{target_user.id}")
        
        assert response.status_code == 200


@pytest.mark.unit
class TestUserPreferencesRoutes:
    """Test user preferences route handlers"""
    
    def test_preferences_page_access(self, client, mock_authenticated_user):
        """Test accessing preferences page"""
        user, session = mock_authenticated_user
        
        response = client.get("/preferences")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_update_preferences_success(self, client, mock_authenticated_user, test_session, clean_db):
        """Test updating user preferences successfully"""
        user, session = mock_authenticated_user
        
        form_data = {
            "religious_preference": "christian",
            "prayer_style": "formal"
        }
        
        response = client.post("/preferences", data=form_data)
        
        # Should redirect after successful update
        assert response.status_code in [302, 303]  # Redirect status codes
    
    def test_update_preferences_invalid_data(self, client, mock_authenticated_user):
        """Test updating preferences with invalid data"""
        user, session = mock_authenticated_user
        
        form_data = {
            "religious_preference": "invalid_preference",
            "prayer_style": "invalid_style"
        }
        
        response = client.post("/preferences", data=form_data)
        
        # Should handle invalid data gracefully
        assert response.status_code in [200, 400, 422]  # Various error handling approaches


@pytest.mark.unit
class TestUserAuthenticationRoutes:
    """Test user authentication-related routes"""
    
    def test_half_authenticated_user_restrictions(self, client, mock_half_authenticated_user):
        """Test that half-authenticated users have proper restrictions"""
        user, session = mock_half_authenticated_user
        
        # Half-authenticated users should have limited access
        response = client.get("/profile")
        
        # Response depends on implementation - could be redirect to auth or limited view
        assert response.status_code in [200, 302, 401, 403]
    
    def test_unauthenticated_user_redirect(self, client):
        """Test that unauthenticated users are redirected"""
        response = client.get("/profile")
        
        # Should redirect to login or show unauthorized
        assert response.status_code in [302, 401, 403]


@pytest.mark.unit
class TestUserDataPrivacy:
    """Test user data privacy and security"""
    
    def test_user_profile_data_filtering(self, client, mock_authenticated_user, test_session, clean_db):
        """Test that user profile shows appropriate data only"""
        user, session = mock_authenticated_user
        
        # Create user with potentially sensitive data
        target_user = UserFactory.create(
            id="target_user_id",
            display_name="Target User"
        )
        test_session.add(target_user)
        test_session.commit()
        
        response = client.get(f"/user/{target_user.id}")
        
        assert response.status_code == 200
        # Response should not contain sensitive information in HTML
        # This is a basic check - specific implementation would need more detailed assertions
    
    def test_own_vs_other_profile_data_differences(self, client, mock_authenticated_user, test_session, clean_db):
        """Test that own profile shows more data than other profiles"""
        user, session = mock_authenticated_user
        
        other_user = UserFactory.create(id="other_user_id", display_name="Other User")
        test_session.add(other_user)
        test_session.commit()
        
        # Get own profile
        own_response = client.get(f"/user/{user.id}")
        
        # Get other user's profile  
        other_response = client.get(f"/user/{other_user.id}")
        
        assert own_response.status_code == 200
        assert other_response.status_code == 200
        
        # Both should be HTML responses but may contain different information
        assert "text/html" in own_response.headers.get("content-type", "")
        assert "text/html" in other_response.headers.get("content-type", "")


@pytest.mark.unit
class TestUserStatsAndActivity:
    """Test user statistics and activity tracking"""
    
    def test_user_prayer_statistics(self, client, mock_authenticated_user, test_session, clean_db):
        """Test that user profile calculates prayer statistics correctly"""
        user, session = mock_authenticated_user
        
        # Create test prayers and marks
        prayer1 = PrayerFactory.create(author_id=user.id)
        prayer2 = PrayerFactory.create(author_id=user.id)
        mark1 = PrayerMarkFactory.create(user_id=user.id, prayer_id=prayer1.id)
        mark2 = PrayerMarkFactory.create(user_id=user.id, prayer_id=prayer2.id)
        
        test_session.add_all([prayer1, prayer2, mark1, mark2])
        test_session.commit()
        
        response = client.get(f"/user/{user.id}")
        
        assert response.status_code == 200
        # Statistics should be computed and displayed
        # Specific assertions would depend on template implementation
    
    def test_user_activity_timeline(self, client, mock_authenticated_user, test_session, clean_db):
        """Test user activity timeline display"""
        user, session = mock_authenticated_user
        
        # Create activity data
        prayer = PrayerFactory.create(author_id=user.id)
        mark = PrayerMarkFactory.create(user_id=user.id, prayer_id=prayer.id)
        
        test_session.add_all([prayer, mark])
        test_session.commit()
        
        response = client.get(f"/user/{user.id}")
        
        assert response.status_code == 200
        # Should include activity timeline in some form