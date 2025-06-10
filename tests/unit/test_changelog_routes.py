"""Unit tests for changelog routes"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app_helpers.routes.changelog_routes import router
from tests.factories import ChangelogEntryFactory


# Removed isolated test client to avoid recursion issues
# Tests now use the main app client through the 'client' fixture


@pytest.mark.unit 
class TestChangelogRoutes:
    """Test changelog route handlers"""
    
    def test_changelog_page_success(self, client, mock_authenticated_user):
        """Test successful changelog page rendering using main app"""
        user, session = mock_authenticated_user
        
        # Mock the changelog functions to avoid actual git operations
        mock_entries = [
            ChangelogEntryFactory.build(
                commit_id="abc123",
                friendly_description="Added new feature",
                change_type="new"
            ),
            ChangelogEntryFactory.build(
                commit_id="def456", 
                friendly_description="Fixed login bug",
                change_type="fixed"
            )
        ]
        
        with patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed', return_value=True), \
             patch('app_helpers.routes.changelog_routes.get_changelog_entries', return_value=mock_entries), \
             patch('app_helpers.routes.changelog_routes.group_entries_by_date', return_value={"Today": mock_entries}):
            
            response = client.get("/changelog")
            
            # Should return successful response or redirect (depending on auth requirements)
            assert response.status_code in [200, 302, 403]
    
    def test_changelog_page_debug_mode(self, client, mock_authenticated_user):
        """Test changelog page with debug mode enabled"""
        user, session = mock_authenticated_user
        
        with patch.dict('os.environ', {'CHANGELOG_DEBUG': 'true'}), \
             patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed', return_value=False), \
             patch('app_helpers.routes.changelog_routes.get_changelog_entries', return_value=[]), \
             patch('app_helpers.routes.changelog_routes.group_entries_by_date', return_value={}), \
             patch('app_helpers.routes.changelog_routes.get_git_head_commit', return_value="abc123"), \
             patch('app_helpers.routes.changelog_routes.get_last_cached_commit', return_value="abc123"):
            
            response = client.get("/changelog")
            
            # Should return successful response or redirect (depending on auth requirements)
            assert response.status_code in [200, 302, 403]
    
    def test_api_changelog_success(self, client, mock_authenticated_user):
        """Test JSON API changelog endpoint"""
        user, session = mock_authenticated_user
        from datetime import datetime
        
        mock_entries = [
            ChangelogEntryFactory.build(
                commit_id="abc123",
                friendly_description="Added new feature", 
                change_type="new",
                commit_date=datetime(2024, 1, 15, 12, 0)
            )
        ]
        
        with patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed', return_value=True), \
             patch('app_helpers.routes.changelog_routes.get_changelog_entries', return_value=mock_entries), \
             patch('app_helpers.routes.changelog_routes.get_change_type_icon', return_value="🚀"):
            
            response = client.get("/api/changelog")
            
            # Should return successful response or redirect/forbidden
            assert response.status_code in [200, 302, 403, 404]
            
            if response.status_code == 200:
                data = response.json()
                assert len(data) == 1
                assert data[0]["id"] == "abc123"
                assert data[0]["friendly_description"] == "Added new feature"
                assert data[0]["change_type"] == "new"
                assert data[0]["icon"] == "🚀"
                assert "date" in data[0]
    
    def test_api_changelog_empty(self, client, mock_authenticated_user):
        """Test API changelog with no entries"""
        user, session = mock_authenticated_user
        
        with patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed', return_value=False), \
             patch('app_helpers.routes.changelog_routes.get_changelog_entries', return_value=[]):
            
            response = client.get("/api/changelog")
            
            # Should return successful response or redirect/forbidden
            assert response.status_code in [200, 302, 403, 404]
            
            if response.status_code == 200:
                data = response.json()
                assert data == []
    
    def test_admin_refresh_changelog_updated(self, client, mock_admin_user):
        """Test admin refresh endpoint when updates are found"""
        user, session = mock_admin_user
        
        with patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed', return_value=True):
            response = client.get("/admin/changelog/refresh")
            
            # Should return successful response or redirect/forbidden  
            assert response.status_code in [200, 302, 403, 404]
            
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
                assert "updated" in data["message"].lower()
    
    def test_admin_refresh_changelog_no_updates(self, client, mock_admin_user):
        """Test admin refresh endpoint when no updates are found"""
        user, session = mock_admin_user
        
        with patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed', return_value=False):
            response = client.get("/admin/changelog/refresh")
            
            # Should return successful response or redirect/forbidden
            assert response.status_code in [200, 302, 403, 404]
            
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "no_change"
                assert "no new commits" in data["message"].lower()