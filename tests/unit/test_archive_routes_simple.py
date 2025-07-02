"""
Simplified tests for archive download API routes.
Tests core functionality without complex authentication mocking.
"""

import pytest
import json
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock
from sqlmodel import Session
from models import User, Prayer, PrayerMark, engine
from app_helpers.services.archive_download_service import ArchiveDownloadService


class TestArchiveDownloadServiceIntegration:
    """Test archive service with mocked authentication requirements."""
    
    @pytest.fixture
    def temp_archive_setup(self):
        """Setup temporary archive directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / "test_archives"
            archive_dir.mkdir()
            
            # Create test archive structure
            prayers_dir = archive_dir / "prayers" / "2024" / "06"
            prayers_dir.mkdir(parents=True)
            
            (archive_dir / "users").mkdir()
            (archive_dir / "activity").mkdir()
            (archive_dir / "downloads").mkdir()
            
            # Create sample prayer file
            prayer_file = prayers_dir / "test_prayer.txt"
            prayer_content = """Prayer 123 by TestUser
Submitted June 15 2024 at 10:30
Project: test
Audience: all

Test prayer content.

Generated Prayer:
Test generated prayer.

Activity:
June 15 2024 at 14:30 - AnotherUser prayed this prayer
"""
            prayer_file.write_text(prayer_content, encoding='utf-8')
            
            # Create user file
            user_file = archive_dir / "users" / "2024_06_users.txt"
            user_file.write_text("June 1 2024 at 09:15 - TestUser joined directly\n", encoding='utf-8')
            
            # Create activity file
            activity_file = archive_dir / "activity" / "activity_2024_06.txt"
            activity_file.write_text("June 15 2024\n10:30 - TestUser submitted prayer 123\n", encoding='utf-8')
            
            yield str(archive_dir)
    
    @pytest.fixture
    def test_user_data(self, temp_archive_setup, test_session):
        """Create test user data."""
        test_user_id = "test_user_123"
        
        user = User(
            id=test_user_id,
            display_name="TestUser",
            created_at=datetime(2024, 6, 1, 9, 15),
            text_file_path=str(Path(temp_archive_setup) / "users" / "2024_06_users.txt")
        )
        
        prayer = Prayer(
            id="prayer_123",
            author_username=test_user_id,
            text="Test prayer content",
            generated_prayer="Test generated prayer",
            created_at=datetime(2024, 6, 15, 10, 30),
            text_file_path=str(Path(temp_archive_setup) / "prayers" / "2024" / "06" / "test_prayer.txt")
        )
        
        test_session.add_all([user, prayer])
        test_session.commit()
        
        yield {"user": user, "prayer": prayer, "archive_dir": temp_archive_setup}
    
    def test_archive_service_user_metadata(self, test_user_data, test_session):
        """Test getting user archive metadata through service."""
        data = test_user_data
        
        # Mock the Session to use test_session
        def mock_session_context_manager(engine_arg):
            return test_session
        
        with patch('app_helpers.services.archive_download_service.Session', mock_session_context_manager):
            service = ArchiveDownloadService(data["archive_dir"])
            metadata = service.get_user_archive_metadata(data["user"].id)
            
            assert metadata["user"]["display_name"] == "TestUser"
            assert metadata["archive_statistics"]["total_prayers"] == 1
            assert len(metadata["prayers"]) == 1
            assert metadata["prayers"][0]["id"] == "prayer_123"
    
    def test_archive_service_user_zip_creation(self, test_user_data, test_session):
        """Test creating user archive ZIP through service."""
        data = test_user_data
        
        # Mock the Session to use test_session
        def mock_session_context_manager(engine_arg):
            return test_session
        
        with patch('app_helpers.services.archive_download_service.Session', mock_session_context_manager):
            service = ArchiveDownloadService(data["archive_dir"])
            
            # Test personal archive creation
            zip_path = service.create_user_archive_zip(data["user"].id, include_community=False)
            
            assert Path(zip_path).exists()
            assert zip_path.endswith(".zip")
            
            # Verify ZIP contents
            with zipfile.ZipFile(zip_path, 'r') as zf:
                file_list = zf.namelist()
                
                # Should contain user's data
                personal_files = [f for f in file_list if "personal/" in f]
                prayer_files = [f for f in file_list if "prayers/" in f]
                
                assert len(personal_files) >= 1
                assert len(prayer_files) >= 1
            
            # Cleanup
            Path(zip_path).unlink()
    
    def test_archive_service_community_zip_creation(self, test_user_data):
        """Test creating community archive ZIP through service."""
        data = test_user_data
        service = ArchiveDownloadService(data["archive_dir"])
        
        zip_path = service.create_full_community_zip()
        
        assert Path(zip_path).exists()
        assert "complete_site_archive" in zip_path
        
        # Verify ZIP contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.namelist()
            
            # Should contain community data
            prayer_files = [f for f in file_list if "prayers/" in f]
            user_files = [f for f in file_list if "users/" in f]
            activity_files = [f for f in file_list if "activity/" in f]
            metadata_files = [f for f in file_list if "archive_metadata.json" in f]
            
            assert len(prayer_files) >= 1
            assert len(user_files) >= 1
            assert len(activity_files) >= 1
            assert len(metadata_files) == 1
        
        # Cleanup
        Path(zip_path).unlink()
    
    def test_archive_service_prayer_file_reading(self, test_user_data):
        """Test reading individual prayer archive files."""
        data = test_user_data
        service = ArchiveDownloadService(data["archive_dir"])
        
        prayer = data["prayer"]
        content = service._read_archive_file(prayer.text_file_path)
        
        assert "Test prayer content" in content
        assert "TestUser" in content
        assert "Generated Prayer" in content
        assert "Activity:" in content
    
    def test_archive_service_community_listing(self, test_user_data):
        """Test listing community archives."""
        data = test_user_data
        service = ArchiveDownloadService(data["archive_dir"])
        
        archives = service.list_community_archives()
        
        assert len(archives) >= 3  # prayers, users, activity
        
        # Check archive types
        types = [a["type"] for a in archives]
        assert "prayers" in types
        assert "users" in types  
        assert "activity" in types
        
        # Check prayer archive details
        prayer_archives = [a for a in archives if a["type"] == "prayers"]
        assert len(prayer_archives) >= 1
        assert prayer_archives[0]["file_count"] >= 1
        assert not prayer_archives[0]["compressed"]
    
    def test_archive_service_error_handling(self, temp_archive_setup, test_session):
        """Test service error handling."""
        # Mock the Session to use test_session
        def mock_session_context_manager(engine_arg):
            return test_session
        
        with patch('app_helpers.services.archive_download_service.Session', mock_session_context_manager):
            service = ArchiveDownloadService(temp_archive_setup)
            
            # Test nonexistent user
            with pytest.raises(ValueError, match="User 99999 not found"):
                service.get_user_archive_metadata("99999")
            
            # Test nonexistent file
            with pytest.raises(FileNotFoundError):
                service._read_archive_file("/nonexistent/file.txt")
    
    def test_archive_service_file_operations(self, temp_archive_setup):
        """Test archive service file operations."""
        service = ArchiveDownloadService(temp_archive_setup)
        
        # Test file counting
        test_zip = Path(temp_archive_setup) / "test.zip"
        with zipfile.ZipFile(test_zip, 'w') as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("file2.txt", "content2")
        
        count = service._count_zip_files(test_zip)
        assert count == 2
        
        # Test cleanup
        downloads_dir = Path(temp_archive_setup) / "downloads"
        downloads_dir.mkdir(exist_ok=True)
        
        old_file = downloads_dir / "old.zip"
        old_file.write_text("old content")
        
        # Set old timestamp
        import os
        old_time = datetime.now().timestamp() - (25 * 3600)  # 25 hours ago
        os.utime(old_file, (old_time, old_time))
        
        service.cleanup_old_downloads(max_age_hours=24)
        assert not old_file.exists()
        
        # Cleanup
        test_zip.unlink()
    
    def test_archive_service_readme_generation(self, temp_archive_setup):
        """Test README content generation."""
        service = ArchiveDownloadService(temp_archive_setup)
        
        readme = service._create_archive_readme()
        
        assert "ThyWill Text Archive" in readme
        assert "Directory Structure" in readme
        assert "prayers/" in readme
        assert "users/" in readme
        assert "activity/" in readme
        assert "Generated:" in readme