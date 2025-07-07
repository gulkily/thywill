"""
Tests for archive download API routes.
Validates authentication, permissions, and HTTP responses.
"""

import pytest
import json
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from sqlmodel import Session
from models import User, Prayer, PrayerMark, engine
from app import app


class TestArchiveRoutes:
    """Test suite for archive download API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def temp_archive_setup(self):
        """Setup temporary archive directory and mock service."""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / "test_archives"
            archive_dir.mkdir()
            
            # Create test archive structure
            prayers_dir = archive_dir / "prayers" / "2024" / "06"
            prayers_dir.mkdir(parents=True)
            
            (archive_dir / "users").mkdir()
            (archive_dir / "activity").mkdir()
            (archive_dir / "downloads").mkdir()
            
            # Create sample files
            prayer_file = prayers_dir / "test_prayer.txt"
            prayer_file.write_text("Test prayer content", encoding='utf-8')
            
            with patch('app.TEXT_ARCHIVE_BASE_DIR', str(archive_dir)):
                yield str(archive_dir)
    
    @pytest.fixture
    def auth_user(self, test_session):
        """Create authenticated user session."""
        user_id = "test_auth_user_123"
        
        user = User(
            id=user_id,
            display_name="AuthUser",
            created_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        # Mock session and auth
        mock_user = Mock()
        mock_user.display_name = user_id
        mock_user.display_name = "AuthUser"
        
        mock_session = Mock()
        mock_session.is_fully_authenticated = True
        
        yield (mock_user, mock_session)
    
    @pytest.fixture
    def admin_user(self, test_session):
        """Create admin user session."""
        user_id = "admin_user_123"
        
        user = User(
            id=user_id,
            display_name="admin",
            created_at=datetime.now()
        )
        test_session.add(user)
        test_session.commit()
        
        mock_user = Mock()
        mock_user.display_name = user_id
        mock_user.display_name = "admin"
        
        mock_session = Mock()
        mock_session.is_fully_authenticated = True
        
        yield (mock_user, mock_session)
    
    @pytest.fixture
    def test_prayer_data(self, auth_user, test_session):
        """Create test prayer with archive file."""
        prayer_id = "test_prayer_123"
        user_mock, _ = auth_user
        
        prayer = Prayer(
            id=prayer_id,
            author_username=user_mock.display_name,
            text="Test prayer request",
            generated_prayer="Test generated prayer",
            created_at=datetime.now(),
            text_file_path="/test/path/prayer.txt"
        )
        test_session.add(prayer)
        test_session.commit()
        
        yield prayer
    
    def test_download_user_archive_own_data(self, client, temp_archive_setup, auth_user):
        """Test downloading own user archive."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        user_mock, session_mock = auth_user
        
        # Override the dependency
        def override_require_full_auth():
            return user_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        try:
            with patch('app_helpers.services.archive_download_service.ArchiveDownloadService.create_user_archive_zip') as mock_create:
                mock_zip_path = Path(temp_archive_setup) / "downloads" / "test_archive.zip"
                
                # Create a real ZIP file for the test
                with zipfile.ZipFile(mock_zip_path, 'w') as zf:
                    zf.writestr("test_file.txt", "test content")
                
                mock_create.return_value = str(mock_zip_path)
                
                response = client.get(f"/api/archive/user/{user_mock.id}/download")
                
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/zip"
                assert "attachment" in response.headers["content-disposition"]
                mock_create.assert_called_once_with(user_mock.id, True)
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_download_user_archive_access_denied(self, client, temp_archive_setup, auth_user):
        """Test downloading another user's archive (should be denied)."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        user_mock, session_mock = auth_user
        other_user_id = "other_user_456"
        
        # Override the dependency
        def override_require_full_auth():
            return user_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        try:
            response = client.get(f"/api/archive/user/{other_user_id}/download")
            
            assert response.status_code == 403
            # The 403 response is now a JSON response for API routes
            data = response.json()
            assert "detail" in data
            assert "Access denied" in data["detail"] or "Forbidden" in data["detail"]
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_download_user_archive_admin_access(self, client, temp_archive_setup, admin_user):
        """Test admin can download any user's archive."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        admin_mock, session_mock = admin_user
        target_user_id = "other_user_789"
        
        # Override the dependency
        def override_require_full_auth():
            return admin_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        try:
            with patch('app_helpers.services.archive_download_service.ArchiveDownloadService.create_user_archive_zip') as mock_create:
                mock_zip_path = Path(temp_archive_setup) / "downloads" / "admin_archive.zip"
                
                with zipfile.ZipFile(mock_zip_path, 'w') as zf:
                    zf.writestr("admin_test.txt", "admin content")
                
                mock_create.return_value = str(mock_zip_path)
                
                response = client.get(f"/api/archive/user/{target_user_id}/download")
                
                assert response.status_code == 200
                mock_create.assert_called_once_with(target_user_id, True)
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_get_user_archive_metadata(self, client, temp_archive_setup, auth_user):
        """Test getting user archive metadata."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        user_mock, session_mock = auth_user
        
        # Override the dependency
        def override_require_full_auth():
            return user_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        try:
            with patch('app_helpers.services.archive_download_service.ArchiveDownloadService.get_user_archive_metadata') as mock_metadata:
                mock_metadata.return_value = {
                    "user": {"id": user_mock.id, "display_name": "AuthUser"},
                    "prayers": [],
                    "activities": [],
                    "archive_statistics": {"total_prayers": 0, "total_activities": 0}
                }
                
                response = client.get(f"/api/archive/user/{user_mock.id}/metadata")
                
                assert response.status_code == 200
                data = response.json()
                assert data["user"]["id"] == user_mock.id
                assert "archive_statistics" in data
                mock_metadata.assert_called_once_with(user_mock.id)
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_list_community_archives(self, client, temp_archive_setup, auth_user):
        """Test listing community archives."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        user_mock, session_mock = auth_user
        
        # Override the dependency
        def override_require_full_auth():
            return user_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        try:
            with patch('app_helpers.services.archive_download_service.ArchiveDownloadService.list_community_archives') as mock_list:
                mock_list.return_value = [
                    {"type": "prayers", "period": "2024-06", "file_count": 5, "compressed": False},
                    {"type": "users", "period": "2024_06", "file_count": 1, "compressed": False}
                ]
                
                response = client.get("/api/archive/community/list")
                
                assert response.status_code == 200
                data = response.json()
                assert "archives" in data
                assert len(data["archives"]) == 2
                mock_list.assert_called_once()
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_download_community_archive(self, client, temp_archive_setup, auth_user):
        """Test downloading complete community archive."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        user_mock, session_mock = auth_user
        
        # Override the dependency
        def override_require_full_auth():
            return user_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        try:
            with patch('app_helpers.services.archive_download_service.ArchiveDownloadService.create_full_community_zip') as mock_create:
                mock_zip_path = Path(temp_archive_setup) / "downloads" / "community_archive.zip"
                
                with zipfile.ZipFile(mock_zip_path, 'w') as zf:
                    zf.writestr("community_data.txt", "community content")
                
                mock_create.return_value = str(mock_zip_path)
                
                response = client.get("/api/archive/community/download")
                
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/zip"
                mock_create.assert_called_once()
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_get_prayer_archive_file(self, client, temp_archive_setup, auth_user, test_prayer_data, test_session):
        """Test downloading individual prayer archive file."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        user_mock, session_mock = auth_user
        prayer = test_prayer_data
        
        # Override the dependency
        def override_require_full_auth():
            return user_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        # Mock Session to use test_session 
        def mock_session_context_manager(engine_arg):
            return test_session
        
        try:
            with patch('app_helpers.routes.archive_routes.Session', mock_session_context_manager):
                with patch('app_helpers.services.archive_download_service.ArchiveDownloadService._read_archive_file') as mock_read:
                    mock_read.return_value = "Prayer archive content\nWith multiple lines"
                    
                    response = client.get(f"/api/archive/prayer/{prayer.id}/file")
                    
                    assert response.status_code == 200
                    assert response.headers["content-type"] == "text/plain; charset=utf-8"
                    assert "attachment" in response.headers["content-disposition"]
                    assert f"prayer_{prayer.id}" in response.headers["content-disposition"]
                    mock_read.assert_called_once_with(prayer.text_file_path)
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_get_prayer_archive_file_not_found(self, client, temp_archive_setup, auth_user, test_session):
        """Test downloading archive file for nonexistent prayer."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        user_mock, session_mock = auth_user
        
        # Override the dependency
        def override_require_full_auth():
            return user_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        # Mock Session to use test_session 
        class MockSession:
            def __init__(self, engine_arg):
                pass
            def __enter__(self):
                return test_session
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        
        try:
            with patch('app_helpers.routes.archive_routes.Session', MockSession):
                response = client.get("/api/archive/prayer/99999/file")
                
                assert response.status_code == 404
                assert "Prayer not found" in response.json()["detail"]
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_get_prayer_archive_file_no_archive(self, client, temp_archive_setup, auth_user, test_session):
        """Test downloading archive file for prayer without archive."""
        user_mock, session_mock = auth_user
        
        # Create prayer using test_session instead of production Session
        prayer = Prayer(
            id="no_archive_prayer",
            author_username=user_mock.display_name,
            text="Prayer without archive",
            created_at=datetime.now(),
            text_file_path=None  # No archive file
        )
        
        test_session.add(prayer)
        test_session.commit()
        
        # Override the dependency
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        def override_require_full_auth():
            return user_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        # Mock Session to use test_session 
        def mock_session_context_manager(engine_arg):
            return test_session
        
        try:
            with patch('app_helpers.routes.archive_routes.Session', mock_session_context_manager):
                response = client.get(f"/api/archive/prayer/{prayer.id}/file")
                
                assert response.status_code == 404
                assert "No archive file for this prayer" in response.json()["detail"]
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
            
            # Cleanup prayer
            test_session.delete(prayer)
            test_session.commit()
    
    def test_cleanup_old_downloads_admin_only(self, client, temp_archive_setup, admin_user):
        """Test cleanup endpoint requires admin access."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        admin_mock, session_mock = admin_user
        
        # Override the dependency
        def override_require_full_auth():
            return admin_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        try:
            with patch('app_helpers.services.archive_download_service.ArchiveDownloadService.cleanup_old_downloads') as mock_cleanup:
                response = client.delete("/api/archive/downloads/cleanup")
                
                assert response.status_code == 200
                assert "cleanup scheduled" in response.json()["message"]
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_cleanup_old_downloads_non_admin_denied(self, client, temp_archive_setup, auth_user):
        """Test cleanup endpoint denies non-admin access."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        user_mock, session_mock = auth_user
        
        # Override the dependency
        def override_require_full_auth():
            return user_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        try:
            response = client.delete("/api/archive/downloads/cleanup")
            
            assert response.status_code == 403
            # The 403 response is now a JSON response for API routes
            data = response.json()
            assert "detail" in data
            assert "Admin access required" in data["detail"] or "Forbidden" in data["detail"]
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_download_with_include_community_parameter(self, client, temp_archive_setup, auth_user):
        """Test download with include_community parameter."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        user_mock, session_mock = auth_user
        
        # Override the dependency
        def override_require_full_auth():
            return user_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        try:
            with patch('app_helpers.services.archive_download_service.ArchiveDownloadService.create_user_archive_zip') as mock_create:
                mock_zip_path = Path(temp_archive_setup) / "downloads" / "test_no_community.zip"
                
                with zipfile.ZipFile(mock_zip_path, 'w') as zf:
                    zf.writestr("personal_only.txt", "personal content")
                
                mock_create.return_value = str(mock_zip_path)
                
                response = client.get(f"/api/archive/user/{user_mock.id}/download?include_community=false")
                
                assert response.status_code == 200
                mock_create.assert_called_once_with(user_mock.id, False)
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_api_error_handling(self, client, temp_archive_setup, auth_user):
        """Test API error handling for service failures."""
        from app import app
        from app_helpers.services.auth_helpers import require_full_auth
        
        user_mock, session_mock = auth_user
        
        # Override the dependency
        def override_require_full_auth():
            return user_mock, session_mock
        
        app.dependency_overrides[require_full_auth] = override_require_full_auth
        
        try:
            with patch('app_helpers.services.archive_download_service.ArchiveDownloadService.create_user_archive_zip') as mock_create:
                mock_create.side_effect = Exception("Service error")
                
                response = client.get(f"/api/archive/user/{user_mock.id}/download")
                
                assert response.status_code == 500
                assert "Archive creation failed" in response.json()["detail"]
                assert "Service error" in response.json()["detail"]
        finally:
            # Clean up dependency override
            if require_full_auth in app.dependency_overrides:
                del app.dependency_overrides[require_full_auth]
    
    def test_authentication_required(self, client, temp_archive_setup):
        """Test that all endpoints require authentication."""
        # Test without authentication mock
        endpoints = [
            "/api/archive/user/123/download",
            "/api/archive/user/123/metadata", 
            "/api/archive/community/list",
            "/api/archive/community/download",
            "/api/archive/prayer/123/file"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should fail due to missing authentication
            assert response.status_code in [401, 422]  # 422 for missing dependency