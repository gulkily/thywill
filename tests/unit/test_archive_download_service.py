"""
Tests for the archive download service.
Validates ZIP creation, user data filtering, and archive metadata generation.
"""

import pytest
import json
import zipfile
import tempfile
import os
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from sqlmodel import Session
from models import User, Prayer, PrayerMark, engine
from app_helpers.services.archive_download_service import ArchiveDownloadService


class TestArchiveDownloadService:
    """Test suite for archive download functionality."""
    
    @pytest.fixture
    def temp_archive_dir(self):
        """Create temporary directory for testing archives."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test archive structure
            archive_dir = Path(temp_dir) / "test_archives"
            archive_dir.mkdir(exist_ok=True)
            
            # Create prayers directory structure
            prayers_dir = archive_dir / "prayers" / "2024" / "06"
            prayers_dir.mkdir(parents=True)
            
            # Create users and activity directories
            (archive_dir / "users").mkdir()
            (archive_dir / "activity").mkdir()
            
            # Create sample prayer file
            prayer_file = prayers_dir / "2024_06_15_prayer_at_1030.txt"
            prayer_content = """Prayer 1 by TestUser
Submitted June 15 2024 at 10:30
Project: healing
Audience: all

Please pray for my health recovery.

Generated Prayer:
Heavenly Father, we lift up TestUser and ask for your healing touch...

Activity:
June 15 2024 at 14:30 - AnotherUser prayed this prayer
"""
            prayer_file.write_text(prayer_content, encoding='utf-8')
            
            # Create sample user file
            user_file = archive_dir / "users" / "2024_06_users.txt"
            user_content = """User Registrations for June 2024

June 1 2024 at 09:15 - TestUser joined directly
June 3 2024 at 14:22 - AnotherUser joined on invitation from TestUser
"""
            user_file.write_text(user_content, encoding='utf-8')
            
            # Create sample activity file
            activity_file = archive_dir / "activity" / "activity_2024_06.txt"
            activity_content = """Activity for June 2024

June 15 2024
10:30 - TestUser submitted prayer 1 (healing)
14:30 - AnotherUser prayed for prayer 1
"""
            activity_file.write_text(activity_content, encoding='utf-8')
            
            yield str(archive_dir)
    
    @pytest.fixture
    def archive_service(self, temp_archive_dir):
        """Create archive download service instance."""
        return ArchiveDownloadService(temp_archive_dir)
    
    @pytest.fixture
    def test_data(self, temp_archive_dir, test_session):
        """Create test data in database."""
        test_id = uuid.uuid4().hex[:8]
        user1_id = f"test_user_1_{test_id}"
        user2_id = f"test_user_2_{test_id}"
        prayer1_id = f"prayer_1_{test_id}"
        
        session = test_session
        # Create test users
        user1 = User(
            id=user1_id,
            display_name="TestUser",
            created_at=datetime(2024, 6, 1, 9, 15),
            text_file_path=str(Path(temp_archive_dir) / "users" / "2024_06_users.txt")
        )
        user2 = User(
            id=user2_id,
            display_name="AnotherUser",
            created_at=datetime(2024, 6, 3, 14, 22),
            text_file_path=str(Path(temp_archive_dir) / "users" / "2024_06_users.txt")
        )
        
        # Create test prayer
        prayer1 = Prayer(
            id=prayer1_id,
            author_id=user1_id,
            text="Please pray for my health recovery.",
            generated_prayer="Heavenly Father, we lift up TestUser and ask for your healing touch...",
            project_tag="healing",
            created_at=datetime(2024, 6, 15, 10, 30),
            text_file_path=str(Path(temp_archive_dir) / "prayers" / "2024" / "06" / "2024_06_15_prayer_at_1030.txt")
        )
        
        # Create prayer mark
        mark1 = PrayerMark(
            user_id=user2_id,
            prayer_id=prayer1_id,
            created_at=datetime(2024, 6, 15, 14, 30),
            text_file_path=str(Path(temp_archive_dir) / "prayers" / "2024" / "06" / "2024_06_15_prayer_at_1030.txt")
        )
        
        session.add_all([user1, user2, prayer1, mark1])
        session.commit()
        
        yield {
            "user1_id": user1_id,
            "user2_id": user2_id,
            "prayer1_id": prayer1_id,
            "user1": user1,
            "user2": user2,
            "prayer1": prayer1
        }
    
    def test_get_user_archive_metadata(self, archive_service, test_data, test_session):
        """Test getting user archive metadata."""
        user1_id = test_data["user1_id"]
        
        # Mock the Session to use test_session
        def mock_session_context_manager(engine_arg):
            return test_session
        
        from unittest.mock import patch
        with patch('app_helpers.services.archive_download_service.Session', mock_session_context_manager):
            metadata = archive_service.get_user_archive_metadata(user1_id)
            
            # Validate metadata structure
            assert "user" in metadata
            assert "prayers" in metadata
            assert "activities" in metadata
            assert "archive_statistics" in metadata
            
            # Validate user info
            user_info = metadata["user"]
            assert user_info["id"] == user1_id
            assert user_info["display_name"] == "TestUser"
            assert "users/2024_06_users.txt" in user_info["text_file_path"]
            
            # Validate statistics
            stats = metadata["archive_statistics"]
            assert stats["total_prayers"] == 1
            assert stats["total_activities"] == 0  # User1 has no prayer marks
            assert stats["date_range"]["earliest"] is not None
            assert stats["date_range"]["latest"] is not None
    
    def test_get_user_archive_metadata_nonexistent_user(self, archive_service, test_session):
        """Test getting metadata for nonexistent user."""
        # Mock the Session to use test_session
        def mock_session_context_manager(engine_arg):
            return test_session
        
        from unittest.mock import patch
        with patch('app_helpers.services.archive_download_service.Session', mock_session_context_manager):
            with pytest.raises(ValueError, match="User 99999 not found"):
                archive_service.get_user_archive_metadata("99999")
    
    def test_list_community_archives(self, archive_service):
        """Test listing all community archive files."""
        archives = archive_service.list_community_archives()
        
        # Should find prayer, user, and activity archives
        assert len(archives) >= 3
        
        # Check for prayer archives
        prayer_archives = [a for a in archives if a["type"] == "prayers"]
        assert len(prayer_archives) >= 1
        assert prayer_archives[0]["period"] == "2024-06"
        assert prayer_archives[0]["file_count"] == 1
        assert not prayer_archives[0]["compressed"]
        
        # Check for user archives
        user_archives = [a for a in archives if a["type"] == "users"]
        assert len(user_archives) >= 1
        assert "2024_06" in user_archives[0]["period"]
        
        # Check for activity archives
        activity_archives = [a for a in archives if a["type"] == "activity"]
        assert len(activity_archives) >= 1
        assert "2024_06" in activity_archives[0]["period"]
    
    def test_create_user_archive_zip_personal_only(self, archive_service, test_data, temp_archive_dir, test_session):
        """Test creating user archive ZIP with personal data only."""
        user1_id = test_data["user1_id"]
        
        # Mock the Session to use test_session
        def mock_session_context_manager(engine_arg):
            return test_session
        
        from unittest.mock import patch
        with patch('app_helpers.services.archive_download_service.Session', mock_session_context_manager):
            zip_path = archive_service.create_user_archive_zip(user1_id, include_community=False)
            
            # Verify ZIP file was created
            assert os.path.exists(zip_path)
            assert zip_path.endswith(".zip")
            
            # Verify ZIP contents
            with zipfile.ZipFile(zip_path, 'r') as zf:
                file_list = zf.namelist()
                
                # Should contain personal directories
                personal_files = [f for f in file_list if "personal/" in f]
                prayer_files = [f for f in file_list if "prayers/" in f]
                activity_files = [f for f in file_list if "activities/" in f]
                
                assert len(personal_files) >= 1
                assert len(prayer_files) >= 1
                assert len(activity_files) >= 1
                
                # Should NOT contain community directories (since include_community=False)
                community_files = [f for f in file_list if "community/" in f]
                assert len(community_files) == 0
            
            # Cleanup
            os.unlink(zip_path)
    
    def test_create_user_archive_zip_with_community(self, archive_service, test_data, temp_archive_dir, test_session):
        """Test creating user archive ZIP with community data."""
        user1_id = test_data["user1_id"]
        
        # Mock the Session to use test_session
        def mock_session_context_manager(engine_arg):
            return test_session
        
        from unittest.mock import patch
        with patch('app_helpers.services.archive_download_service.Session', mock_session_context_manager):
            zip_path = archive_service.create_user_archive_zip(user1_id, include_community=True)
            
            # Verify ZIP file was created
            assert os.path.exists(zip_path)
            
            # Verify ZIP contents include community data
            with zipfile.ZipFile(zip_path, 'r') as zf:
                file_list = zf.namelist()
                
                # Should contain community directories
                community_files = [f for f in file_list if "community/" in f]
                assert len(community_files) > 0
                
                # Should contain community activity and user files
                community_activity = [f for f in file_list if "community/activity/" in f]
                community_users = [f for f in file_list if "community/users/" in f]
                
                assert len(community_activity) >= 1
                assert len(community_users) >= 1
            
            # Cleanup
            os.unlink(zip_path)
    
    def test_create_full_community_zip(self, archive_service, temp_archive_dir):
        """Test creating complete community archive ZIP."""
        zip_path = archive_service.create_full_community_zip()
        
        # Verify ZIP file was created
        assert os.path.exists(zip_path)
        assert "complete_site_archive" in zip_path
        
        # Verify ZIP contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.namelist()
            
            # Should contain main archive directories
            prayers_files = [f for f in file_list if "prayers/" in f]
            users_files = [f for f in file_list if "users/" in f]
            activity_files = [f for f in file_list if "activity/" in f]
            
            assert len(prayers_files) >= 1
            assert len(users_files) >= 1
            assert len(activity_files) >= 1
            
            # Should contain metadata files
            metadata_files = [f for f in file_list if "archive_metadata.json" in f]
            readme_files = [f for f in file_list if "README.txt" in f]
            
            assert len(metadata_files) == 1
            assert len(readme_files) == 1
            
            # Verify metadata content
            with zf.open(metadata_files[0]) as metadata_file:
                metadata = json.loads(metadata_file.read().decode('utf-8'))
                assert metadata["export_type"] == "complete_site_archive"
                assert "export_date" in metadata
                assert "archive_structure" in metadata
                assert "format_info" in metadata
        
        # Cleanup
        os.unlink(zip_path)
    
    def test_read_archive_file_existing(self, archive_service, temp_archive_dir):
        """Test reading existing archive file."""
        # Create a test file
        test_file = Path(temp_archive_dir) / "test_file.txt"
        test_content = "Test archive content"
        test_file.write_text(test_content, encoding='utf-8')
        
        content = archive_service._read_archive_file(str(test_file))
        assert content == test_content
    
    def test_read_archive_file_nonexistent(self, archive_service):
        """Test reading nonexistent archive file."""
        with pytest.raises(FileNotFoundError):
            archive_service._read_archive_file("/nonexistent/path.txt")
    
    def test_extract_user_registration(self, archive_service, test_data):
        """Test extracting user registration information."""
        user = test_data["user1"]
        
        registration_info = archive_service._extract_user_registration(user)
        
        assert "TestUser" in registration_info
        assert "Registration" in registration_info
        assert "2024" in registration_info
    
    def test_create_user_activity_summary(self, archive_service, test_data, test_session):
        """Test creating user activity summary."""
        user = test_data["user1"]
        
        # Get prayer marks for user2 (who marked user1's prayer)
        user2_marks = test_session.query(PrayerMark).filter_by(user_id=test_data["user2_id"]).all()
        
        summary = archive_service._create_user_activity_summary(test_data["user2"], user2_marks)
        
        assert test_data["user2"].display_name in summary
        assert "Prayer Activities" in summary
        if user2_marks:
            assert "June" in summary  # Should contain activity dates
    
    def test_cleanup_old_downloads(self, archive_service, temp_archive_dir):
        """Test cleanup of old download files."""
        # Create downloads directory and old file
        downloads_dir = Path(temp_archive_dir) / "downloads"
        downloads_dir.mkdir(exist_ok=True)
        
        old_file = downloads_dir / "old_archive.zip"
        old_file.write_text("test")
        
        # Modify the file's timestamp to make it appear old
        old_time = datetime.now().timestamp() - (25 * 3600)  # 25 hours ago
        os.utime(old_file, (old_time, old_time))
        
        # Run cleanup (24 hour threshold)
        archive_service.cleanup_old_downloads(max_age_hours=24)
        
        # File should be deleted
        assert not old_file.exists()
    
    def test_count_zip_files(self, archive_service, temp_archive_dir):
        """Test counting files in ZIP archive."""
        # Create a test ZIP file
        zip_path = Path(temp_archive_dir) / "test.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("file2.txt", "content2")
            zf.writestr("dir/file3.txt", "content3")
        
        count = archive_service._count_zip_files(zip_path)
        assert count == 3
    
    def test_count_zip_files_invalid(self, archive_service, temp_archive_dir):
        """Test counting files in invalid ZIP."""
        # Create invalid ZIP file
        invalid_zip = Path(temp_archive_dir) / "invalid.zip"
        invalid_zip.write_text("not a zip file")
        
        count = archive_service._count_zip_files(invalid_zip)
        assert count == 0
    
    def test_create_archive_readme(self, archive_service):
        """Test creating archive README content."""
        readme = archive_service._create_archive_readme()
        
        assert "ThyWill Text Archive" in readme
        assert "Directory Structure" in readme
        assert "File Format" in readme
        assert "Timestamps" in readme
        assert "About This Archive" in readme
        assert "Generated:" in readme
        assert "prayers/" in readme
        assert "users/" in readme
        assert "activity/" in readme