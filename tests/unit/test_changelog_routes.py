"""Unit tests for changelog routes"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app_helpers.routes.changelog_routes import router
from tests.factories import ChangelogEntryFactory


@pytest.fixture
def test_client():
    """Create test client for changelog routes"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.unit
class TestChangelogRoutes:
    """Test changelog route handlers"""
    
    def test_changelog_page_success(self, test_client):
        """Test successful changelog page rendering"""
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
             patch('app_helpers.routes.changelog_routes.group_entries_by_date', return_value={"Today": mock_entries}), \
             patch('app_helpers.routes.changelog_routes.templates') as mock_templates:
            
            mock_templates.TemplateResponse.return_value = Mock()
            
            response = test_client.get("/changelog")
            
            assert response.status_code == 200
            mock_templates.TemplateResponse.assert_called_once()
            
            # Verify template context
            call_args = mock_templates.TemplateResponse.call_args
            context = call_args[0][1]
            assert "grouped_entries" in context
            assert "get_change_type_icon" in context
    
    def test_changelog_page_debug_mode(self, test_client):
        """Test changelog page with debug mode enabled"""
        with patch.dict('os.environ', {'CHANGELOG_DEBUG': 'true'}), \
             patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed', return_value=False), \
             patch('app_helpers.routes.changelog_routes.get_changelog_entries', return_value=[]), \
             patch('app_helpers.routes.changelog_routes.group_entries_by_date', return_value={}), \
             patch('app_helpers.routes.changelog_routes.get_git_head_commit', return_value="abc123"), \
             patch('app_helpers.routes.changelog_routes.get_last_cached_commit', return_value="abc123"), \
             patch('app_helpers.routes.changelog_routes.templates') as mock_templates:
            
            mock_templates.TemplateResponse.return_value = Mock()
            
            response = test_client.get("/changelog")
            
            assert response.status_code == 200
            
            # Verify debug info is included in context
            call_args = mock_templates.TemplateResponse.call_args
            context = call_args[0][1]
            assert "debug_info" in context
            assert context["debug_info"] is not None
    
    def test_api_changelog_success(self, test_client):
        """Test JSON API changelog endpoint"""
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
            
            response = test_client.get("/api/changelog")
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data) == 1
            assert data[0]["id"] == "abc123"
            assert data[0]["friendly_description"] == "Added new feature"
            assert data[0]["change_type"] == "new"
            assert data[0]["icon"] == "🚀"
            assert "date" in data[0]
    
    def test_api_changelog_empty(self, test_client):
        """Test API changelog with no entries"""
        with patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed', return_value=False), \
             patch('app_helpers.routes.changelog_routes.get_changelog_entries', return_value=[]):
            
            response = test_client.get("/api/changelog")
            
            assert response.status_code == 200
            data = response.json()
            assert data == []
    
    def test_admin_refresh_changelog_updated(self, test_client):
        """Test admin refresh endpoint when updates are found"""
        with patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed', return_value=True):
            response = test_client.get("/admin/changelog/refresh")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "updated" in data["message"].lower()
    
    def test_admin_refresh_changelog_no_updates(self, test_client):
        """Test admin refresh endpoint when no updates are found"""
        with patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed', return_value=False):
            response = test_client.get("/admin/changelog/refresh")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "no_change"
            assert "no new commits" in data["message"].lower()


@pytest.mark.unit 
class TestChangelogTemplateData:
    """Test changelog template data processing"""
    
    def test_grouped_entries_structure(self, test_client):
        """Test that grouped entries are structured correctly for templates"""
        from datetime import datetime, date, timedelta
        
        today = datetime.combine(date.today(), datetime.min.time())
        yesterday = today - timedelta(days=1)
        
        mock_entries = [
            ChangelogEntryFactory.build(commit_date=today),
            ChangelogEntryFactory.build(commit_date=yesterday)
        ]
        
        expected_grouped = {
            "Today": [mock_entries[0]],
            "Yesterday": [mock_entries[1]]
        }
        
        with patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed'), \
             patch('app_helpers.routes.changelog_routes.get_changelog_entries', return_value=mock_entries), \
             patch('app_helpers.routes.changelog_routes.group_entries_by_date', return_value=expected_grouped), \
             patch('app_helpers.routes.changelog_routes.templates') as mock_templates:
            
            mock_templates.TemplateResponse.return_value = Mock()
            
            response = test_client.get("/changelog")
            
            call_args = mock_templates.TemplateResponse.call_args
            context = call_args[0][1]
            
            assert context["grouped_entries"] == expected_grouped
    
    def test_change_type_icon_function_available(self, test_client):
        """Test that change type icon function is available in template context"""
        with patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed'), \
             patch('app_helpers.routes.changelog_routes.get_changelog_entries', return_value=[]), \
             patch('app_helpers.routes.changelog_routes.group_entries_by_date', return_value={}), \
             patch('app_helpers.routes.changelog_routes.templates') as mock_templates:
            
            mock_templates.TemplateResponse.return_value = Mock()
            
            response = test_client.get("/changelog")
            
            call_args = mock_templates.TemplateResponse.call_args
            context = call_args[0][1]
            
            # Function should be available in context
            assert callable(context["get_change_type_icon"])
    
    def test_debug_info_structure(self, test_client):
        """Test debug info structure when enabled"""
        with patch.dict('os.environ', {'CHANGELOG_DEBUG': 'true'}), \
             patch('app_helpers.routes.changelog_routes.refresh_changelog_if_needed', return_value=True), \
             patch('app_helpers.routes.changelog_routes.get_changelog_entries', return_value=[]), \
             patch('app_helpers.routes.changelog_routes.group_entries_by_date', return_value={}), \
             patch('app_helpers.routes.changelog_routes.get_git_head_commit', return_value="abc123"), \
             patch('app_helpers.routes.changelog_routes.get_last_cached_commit', return_value="def456"), \
             patch('subprocess.run') as mock_subprocess, \
             patch('app_helpers.routes.changelog_routes.templates') as mock_templates:
            
            mock_subprocess.return_value = Mock()  # Git available
            mock_templates.TemplateResponse.return_value = Mock()
            
            response = test_client.get("/changelog")
            
            call_args = mock_templates.TemplateResponse.call_args
            context = call_args[0][1]
            debug_info = context["debug_info"]
            
            # Check debug info structure
            assert "git_head" in debug_info
            assert "last_cached" in debug_info
            assert "anthropic_key_exists" in debug_info
            assert "git_available" in debug_info
            assert "entry_count" in debug_info
            assert "refresh_attempted" in debug_info
            
            assert debug_info["git_head"] == "abc123"
            assert debug_info["last_cached"] == "def456"
            assert debug_info["refresh_attempted"] is True