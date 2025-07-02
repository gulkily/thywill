"""
Integration tests for archive download functionality.
Tests the complete workflow from service to API to file generation.
"""

import pytest
import json
import zipfile
import tempfile
import os
import uuid
from pathlib import Path
from datetime import datetime
from sqlmodel import Session
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

from models import User, Prayer, PrayerMark
from app import app
from app_helpers.services.archive_download_service import ArchiveDownloadService


class TestArchiveDownloadIntegration:
    """Integration tests for complete archive download workflow."""
    
    @pytest.fixture
    def test_archive_environment(self):
        """Set up complete test environment with real archive files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create archive directory structure
            archive_dir = Path(temp_dir) / "integration_archives"
            archive_dir.mkdir()
            
            # Create realistic directory structure
            prayers_2024_06 = archive_dir / "prayers" / "2024" / "06"
            prayers_2024_06.mkdir(parents=True)
            
            users_dir = archive_dir / "users"
            users_dir.mkdir()
            
            activity_dir = archive_dir / "activity"
            activity_dir.mkdir()
            
            downloads_dir = archive_dir / "downloads"
            downloads_dir.mkdir()
            
            # Create realistic archive files
            prayer1_file = prayers_2024_06 / "2024_06_15_prayer_at_1030.txt"
            prayer1_content = """Prayer 1001 by IntegrationUser
Submitted June 15 2024 at 10:30
Project: healing
Audience: all

Please pray for my recovery from illness and strength for my family.

Generated Prayer:
Heavenly Father, we lift up IntegrationUser who is facing illness and asks for your healing touch. We pray for physical restoration and strength for their family during this challenging time. Grant them peace, comfort, and your divine presence. In your holy name we pray, Amen.

Activity:
June 15 2024 at 14:30 - TestUser2 prayed this prayer
June 16 2024 at 09:15 - TestUser3 prayed this prayer
June 16 2024 at 18:00 - IntegrationUser marked this prayer as answered
June 16 2024 at 18:01 - IntegrationUser added testimony: Feeling much better, thank you all for your prayers!
"""
            
            prayer2_file = prayers_2024_06 / "2024_06_16_prayer_at_1400.txt"
            prayer2_content = """Prayer 1002 by TestUser2
Submitted June 16 2024 at 14:00
Project: family
Audience: all

Please pray for wisdom in a difficult family situation.

Generated Prayer:
Lord, we ask for your wisdom and guidance for TestUser2 as they navigate a challenging family situation. Grant them discernment, patience, and the right words to speak. Help bring healing and understanding to all involved. We trust in your perfect timing and love.

Activity:
June 16 2024 at 16:30 - IntegrationUser prayed this prayer
June 17 2024 at 08:45 - TestUser3 prayed this prayer
"""
            
            prayer1_file.write_text(prayer1_content, encoding='utf-8')
            prayer2_file.write_text(prayer2_content, encoding='utf-8')
            
            # Create user registration file
            users_file = users_dir / "2024_06_users.txt"
            users_content = """User Registrations for June 2024

June 1 2024 at 09:15 - IntegrationUser joined directly
June 3 2024 at 14:22 - TestUser2 joined on invitation from IntegrationUser
June 5 2024 at 11:30 - TestUser3 joined on invitation from TestUser2
"""
            users_file.write_text(users_content, encoding='utf-8')
            
            # Create activity file
            activity_file = activity_dir / "activity_2024_06.txt"
            activity_content = """Activity for June 2024

June 15 2024
10:30 - IntegrationUser submitted prayer 1001 (healing)
14:30 - TestUser2 prayed for prayer 1001

June 16 2024
09:15 - TestUser3 prayed for prayer 1001
14:00 - TestUser2 submitted prayer 1002 (family)
16:30 - IntegrationUser prayed for prayer 1002
18:00 - IntegrationUser marked prayer 1001 as answered
18:01 - IntegrationUser added testimony for prayer 1001

June 17 2024
08:45 - TestUser3 prayed for prayer 1002
"""
            activity_file.write_text(activity_content, encoding='utf-8')
            
            yield str(archive_dir)
    
    @pytest.fixture
    def integration_test_data(self, test_archive_environment, test_session):
        """Create comprehensive test data in database."""
        test_id = uuid.uuid4().hex[:8]
        user1_id = f"integration_user_{test_id}"
        user2_id = f"test_user_2_{test_id}"
        user3_id = f"test_user_3_{test_id}"
        prayer1_id = f"prayer_1001_{test_id}"
        prayer2_id = f"prayer_1002_{test_id}"
        
        session = test_session
        # Create users
        user1 = User(
            id=user1_id,
            display_name="IntegrationUser",
            created_at=datetime(2024, 6, 1, 9, 15),
            text_file_path=f"{test_archive_environment}/users/2024_06_users.txt"
        )
        
        user2 = User(
            id=user2_id,
            display_name="TestUser2",
            created_at=datetime(2024, 6, 3, 14, 22),
            text_file_path=f"{test_archive_environment}/users/2024_06_users.txt"
        )
        
        user3 = User(
            id=user3_id,
            display_name="TestUser3",
            created_at=datetime(2024, 6, 5, 11, 30),
            text_file_path=f"{test_archive_environment}/users/2024_06_users.txt"
        )
        
        # Create prayers
        prayer1 = Prayer(
            id=prayer1_id,
            author_username=user1_id,
            text="Please pray for my recovery from illness and strength for my family.",
            generated_prayer="Heavenly Father, we lift up IntegrationUser who is facing illness...",
            project_tag="healing",
            created_at=datetime(2024, 6, 15, 10, 30),
            text_file_path=f"{test_archive_environment}/prayers/2024/06/2024_06_15_prayer_at_1030.txt"
        )
        
        prayer2 = Prayer(
            id=prayer2_id,
            author_username=user2_id,
            text="Please pray for wisdom in a difficult family situation.",
            generated_prayer="Lord, we ask for your wisdom and guidance for TestUser2...",
            project_tag="family",
            created_at=datetime(2024, 6, 16, 14, 0),
            text_file_path=f"{test_archive_environment}/prayers/2024/06/2024_06_16_prayer_at_1400.txt"
        )
        
        # Create prayer marks
        mark1 = PrayerMark(
            username=user2_id,
            prayer_id=prayer1_id,
            created_at=datetime(2024, 6, 15, 14, 30),
            text_file_path=f"{test_archive_environment}/prayers/2024/06/2024_06_15_prayer_at_1030.txt"
        )
        
        mark2 = PrayerMark(
            username=user3_id,
            prayer_id=prayer1_id,
            created_at=datetime(2024, 6, 16, 9, 15),
            text_file_path=f"{test_archive_environment}/prayers/2024/06/2024_06_15_prayer_at_1030.txt"
        )
        
        mark3 = PrayerMark(
            username=user1_id,
            prayer_id=prayer2_id,
            created_at=datetime(2024, 6, 16, 16, 30),
            text_file_path=f"{test_archive_environment}/prayers/2024/06/2024_06_16_prayer_at_1400.txt"
        )
        
        mark4 = PrayerMark(
            username=user3_id,
            prayer_id=prayer2_id,
            created_at=datetime(2024, 6, 17, 8, 45),
            text_file_path=f"{test_archive_environment}/prayers/2024/06/2024_06_16_prayer_at_1400.txt"
        )
        
        session.add_all([user1, user2, user3, prayer1, prayer2, mark1, mark2, mark3, mark4])
        session.commit()
        
        yield {
            "archive_dir": test_archive_environment,
            "users": {"user1": user1, "user2": user2, "user3": user3},
            "prayers": {"prayer1": prayer1, "prayer2": prayer2},
            "marks": [mark1, mark2, mark3, mark4]
        }
    
    def test_complete_user_archive_workflow(self, integration_test_data, test_session):
        """Test complete user archive creation workflow."""
        data = integration_test_data
        user1 = data["users"]["user1"]
        
        # Mock the Session to use test_session
        def mock_session_context_manager(engine_arg):
            return test_session
        
        with patch('app_helpers.services.archive_download_service.Session', mock_session_context_manager):
            # Test with actual service
            service = ArchiveDownloadService(data["archive_dir"])
            
            # Get metadata first
            metadata = service.get_user_archive_metadata(user1.display_name)
            
            assert metadata["user"]["display_name"] == "IntegrationUser"
            assert metadata["archive_statistics"]["total_prayers"] == 1  # User1 authored 1 prayer
            assert metadata["archive_statistics"]["total_activities"] == 1  # User1 prayed for 1 prayer
            
            # Create personal archive
            zip_path = service.create_user_archive_zip(user1.display_name, include_community=False)
        
        assert os.path.exists(zip_path)
        
        # Verify ZIP contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.namelist()
            
            # Should have personal directories
            personal_files = [f for f in file_list if "personal/" in f]
            prayer_files = [f for f in file_list if "prayers/" in f]
            activity_files = [f for f in file_list if "activities/" in f]
            
            assert len(personal_files) >= 1
            assert len(prayer_files) >= 1
            assert len(activity_files) >= 1
            
            # Verify prayer content - look for the actual prayer file pattern
            prayer_files_in_zip = [f for f in file_list if f.endswith("_2024_06_15.txt") and "prayers/" in f]
            assert len(prayer_files_in_zip) == 1
            
            with zf.open(prayer_files_in_zip[0]) as prayer_file:
                prayer_content = prayer_file.read().decode('utf-8')
                assert "Please pray for my recovery from illness" in prayer_content
                assert "Heavenly Father, we lift up IntegrationUser" in prayer_content
                assert "TestUser2 prayed this prayer" in prayer_content
        
        # Cleanup
        os.unlink(zip_path)
    
    def test_complete_community_archive_workflow(self, integration_test_data):
        """Test complete community archive creation workflow."""
        data = integration_test_data
        
        service = ArchiveDownloadService(data["archive_dir"])
        
        # List community archives
        archives = service.list_community_archives()
        
        # Should have prayer, user, and activity archives
        assert len(archives) >= 3
        
        types = [a["type"] for a in archives]
        assert "prayers" in types
        assert "users" in types
        assert "activity" in types
        
        # Create full community archive
        zip_path = service.create_full_community_zip()
        
        assert os.path.exists(zip_path)
        assert "complete_site_archive" in zip_path
        
        # Verify comprehensive ZIP contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.namelist()
            
            # Should contain all archive types
            prayers_files = [f for f in file_list if "prayers/" in f]
            users_files = [f for f in file_list if "users/" in f]
            activity_files = [f for f in file_list if "activity/" in f]
            
            assert len(prayers_files) >= 2  # Should have both prayer files
            assert len(users_files) >= 1
            assert len(activity_files) >= 1
            
            # Should contain metadata and README
            metadata_files = [f for f in file_list if "archive_metadata.json" in f]
            readme_files = [f for f in file_list if "README.txt" in f]
            
            assert len(metadata_files) == 1
            assert len(readme_files) == 1
            
            # Verify metadata content
            with zf.open(metadata_files[0]) as metadata_file:
                metadata = json.loads(metadata_file.read().decode('utf-8'))
                assert metadata["export_type"] == "complete_site_archive"
                assert "prayers" in metadata["archive_structure"]
                assert "users" in metadata["archive_structure"]
                assert "activity" in metadata["archive_structure"]
            
            # Verify README content
            with zf.open(readme_files[0]) as readme_file:
                readme = readme_file.read().decode('utf-8')
                assert "ThyWill Text Archive" in readme
                assert "Directory Structure" in readme
                assert "prayers/" in readme
        
        # Cleanup
        os.unlink(zip_path)
    
    def test_api_integration_workflow(self, integration_test_data, test_session):
        """Test complete API workflow integration."""
        data = integration_test_data
        user1 = data["users"]["user1"]
        prayer1 = data["prayers"]["prayer1"]
        
        client = TestClient(app)
        
        # Mock authentication
        mock_user = Mock()
        mock_user.display_name = user1.display_name
        mock_user.display_name = user1.display_name
        
        mock_session = Mock()
        mock_session.is_fully_authenticated = True
        
        # Mock the Session to use test_session
        def mock_session_context_manager(engine_arg):
            return test_session
        
        with patch('app.TEXT_ARCHIVE_BASE_DIR', data["archive_dir"]):
            with patch('app_helpers.services.archive_download_service.Session', mock_session_context_manager):
                with patch('app_helpers.routes.archive_routes.Session', mock_session_context_manager):
                    from app_helpers.routes.archive_routes import require_full_auth
                    
                    # Override the dependency
                    def override_require_full_auth():
                        return mock_user, mock_session
                    
                    app.dependency_overrides[require_full_auth] = override_require_full_auth
                    
                    try:
                        # Test metadata endpoint
                        response = client.get(f"/api/archive/user/{user1.display_name}/metadata")
                        assert response.status_code == 200
                        
                        metadata = response.json()
                        assert metadata["user"]["display_name"] == "IntegrationUser"
                        assert metadata["archive_statistics"]["total_prayers"] == 1
                        
                        # Test community list endpoint
                        response = client.get("/api/archive/community/list")
                        assert response.status_code == 200
                        
                        archives = response.json()["archives"]
                        assert len(archives) >= 3
                        
                        # Test prayer file download
                        response = client.get(f"/api/archive/prayer/{prayer1.id}/file")
                        assert response.status_code == 200
                        assert response.headers["content-type"] == "text/plain; charset=utf-8"
                        
                        content = response.content.decode('utf-8')
                        assert "Please pray for my recovery from illness" in content
                        assert "IntegrationUser" in content
                        
                        # Test user archive download
                        response = client.get(f"/api/archive/user/{user1.display_name}/download")
                        assert response.status_code == 200
                        assert response.headers["content-type"] == "application/zip"
                        
                        # Test community archive download
                        response = client.get("/api/archive/community/download")
                        assert response.status_code == 200
                        assert response.headers["content-type"] == "application/zip"
                    
                    finally:
                        # Clean up the override
                        if require_full_auth in app.dependency_overrides:
                            del app.dependency_overrides[require_full_auth]
    
    def test_large_archive_performance(self, integration_test_data):
        """Test performance with larger archive sets."""
        data = integration_test_data
        
        # Create additional test files to simulate larger archive
        prayers_dir = Path(data["archive_dir"]) / "prayers" / "2024" / "06"
        
        # Create 10 more prayer files
        for i in range(10):
            prayer_file = prayers_dir / f"2024_06_{17+i:02d}_prayer_at_1000.txt"
            content = f"""Prayer {2000+i} by TestUser{i%3 + 1}
Submitted June {17+i} 2024 at 10:00
Project: test
Audience: all

Test prayer request {i}.

Generated Prayer:
Test generated prayer {i}.

Activity:
June {17+i} 2024 at 15:00 - TestUser{(i+1)%3 + 1} prayed this prayer
"""
            prayer_file.write_text(content, encoding='utf-8')
        
        service = ArchiveDownloadService(data["archive_dir"])
        
        # Test that larger archives still work efficiently
        import time
        start_time = time.time()
        
        zip_path = service.create_full_community_zip()
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert creation_time < 10.0  # 10 seconds should be more than enough
        
        # Verify the archive contains all files
        with zipfile.ZipFile(zip_path, 'r') as zf:
            prayer_files = [f for f in zf.namelist() if f.endswith('.txt') and 'prayers/' in f]
            assert len(prayer_files) >= 12  # Original 2 + 10 new ones
        
        # Cleanup
        os.unlink(zip_path)
    
    def test_error_recovery_and_cleanup(self, integration_test_data):
        """Test error handling and cleanup mechanisms."""
        data = integration_test_data
        service = ArchiveDownloadService(data["archive_dir"])
        
        # Test cleanup of old downloads
        downloads_dir = Path(data["archive_dir"]) / "downloads"
        
        # Create old file
        old_file = downloads_dir / "old_archive.zip"
        old_file.write_text("old archive content")
        
        # Set old timestamp
        old_time = datetime.now().timestamp() - (25 * 3600)  # 25 hours ago
        os.utime(old_file, (old_time, old_time))
        
        # Create recent file
        recent_file = downloads_dir / "recent_archive.zip"
        recent_file.write_text("recent archive content")
        
        # Run cleanup
        service.cleanup_old_downloads(max_age_hours=24)
        
        # Old file should be deleted, recent file should remain
        assert not old_file.exists()
        assert recent_file.exists()
        
        # Cleanup
        recent_file.unlink()
    
    def test_archive_consistency_validation(self, integration_test_data, test_session):
        """Test that archives maintain data consistency."""
        data = integration_test_data
        user1 = data["users"]["user1"]
        
        # Mock the Session to use test_session
        def mock_session_context_manager(engine_arg):
            return test_session
        
        with patch('app_helpers.services.archive_download_service.Session', mock_session_context_manager):
            service = ArchiveDownloadService(data["archive_dir"])
            
            # Create user archive
            zip_path = service.create_user_archive_zip(user1.display_name, include_community=True)
            
            # Extract and validate contents
            extract_dir = Path(zip_path).parent / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
            
            # Verify user data consistency
            user_archive_dir = extract_dir / f"{user1.display_name}_text_archive"
            assert user_archive_dir.exists()
            
            # Check personal directory
            personal_dir = user_archive_dir / "personal"
            assert personal_dir.exists()
            
            registration_file = personal_dir / "registration.txt"
            if registration_file.exists():
                registration_content = registration_file.read_text()
                assert user1.display_name in registration_content
            
            # Check prayers directory
            prayers_dir = user_archive_dir / "prayers"
            assert prayers_dir.exists()
            
            prayer_files = list(prayers_dir.glob("*.txt"))
            assert len(prayer_files) >= 1
            
            # Verify prayer content matches database
            prayer_content = prayer_files[0].read_text()
            assert "Please pray for my recovery from illness" in prayer_content
            
            # Check activities directory
            activities_dir = user_archive_dir / "activities"
            assert activities_dir.exists()
            
            activity_file = activities_dir / "my_prayer_activities.txt"
            assert activity_file.exists()
            
            activity_content = activity_file.read_text()
            assert user1.display_name in activity_content
            
            # Cleanup
            import shutil
            shutil.rmtree(extract_dir)
            os.unlink(zip_path)