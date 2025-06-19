"""
Tests for the community database export service.
Validates data filtering, security exclusions, and JSON serialization.
"""

import pytest
import json
import uuid
import zipfile
import io
from datetime import datetime, timedelta
from sqlmodel import Session, select
from models import (
    User, Prayer, PrayerAttribute, PrayerMark, PrayerSkip,
    PrayerActivityLog, Role, UserRole, InviteToken, ChangelogEntry,
    engine
)
from app_helpers.services.export_service import CommunityExportService


class TestCommunityExportService:
    """Test suite for community database export functionality."""
    
    @pytest.fixture
    def export_service(self, test_session):
        """Create export service instance with mocked session."""
        from unittest.mock import patch
        
        # Mock the Session to use test_session
        def mock_session_context_manager(engine_arg):
            return test_session
        
        with patch('app_helpers.services.export_service.Session', mock_session_context_manager):
            yield CommunityExportService()
    
    @pytest.fixture
    def sample_data(self, test_session):
        """Create sample data for testing."""
        # Generate unique IDs for this test run
        test_id = uuid.uuid4().hex[:8]
        user1_id = f"test_user_1_{test_id}"
        user2_id = f"test_user_2_{test_id}"
        prayer1_id = f"prayer_1_{test_id}"
        prayer2_id = f"prayer_2_{test_id}"
        role1_id = f"test_role_1_{test_id}"
        token1_name = f"test_token_1_{test_id}"
        token2_name = f"test_token_2_{test_id}"
        role_name = f"test_user_role_{test_id}"
        
        session = test_session
        # Create test users
        user1 = User(
            id=user1_id,
            display_name="Test User 1",
            religious_preference="christian",
            prayer_style="in_jesus_name",
            invited_by_user_id=None,
            invite_token_used=token1_name
        )
        user2 = User(
            id=user2_id, 
            display_name="Test User 2",
            religious_preference="unspecified",
            invited_by_user_id=user1_id,
            invite_token_used=token2_name
        )
        session.add(user1)
        session.add(user2)
        
        # Create test prayers (both flagged and non-flagged)
        prayer1 = Prayer(
            id=prayer1_id,
            author_id=user1_id,
            text="Please pray for healing",
            generated_prayer="Lord, we pray for healing...",
            target_audience="all",
            flagged=False
        )
        prayer2 = Prayer(
            id=prayer2_id,
            author_id=user2_id, 
            text="This is a flagged prayer",
            flagged=True
        )
        session.add(prayer1)
        session.add(prayer2)
        
        # Create prayer attributes
        attr1 = PrayerAttribute(
            prayer_id=prayer1_id,
            attribute_name="answered",
            attribute_value="true",
            created_by=user1_id
        )
        attr2 = PrayerAttribute(
            prayer_id=prayer2_id,
            attribute_name="flagged", 
            attribute_value="true",
            created_by="admin"
        )
        session.add(attr1)
        session.add(attr2)
        
        # Create prayer marks and skips
        mark1 = PrayerMark(
            user_id=user1_id,
            prayer_id=prayer1_id
        )
        skip1 = PrayerSkip(
            user_id=user2_id,
            prayer_id=prayer1_id  
        )
        session.add(mark1)
        session.add(skip1)
        
        # Create activity logs
        log1 = PrayerActivityLog(
            prayer_id=prayer1_id,
            user_id=user1_id,
            action="set_answered",
            old_value=None,
            new_value="true"
        )
        session.add(log1)
        
        # Create roles and user roles
        role1 = Role(
            id=role1_id,
            name=role_name,
            description="Test user role",
            permissions='["read", "write"]',
            is_system_role=False
        )
        session.add(role1)
        
        user_role1 = UserRole(
            user_id=user1_id,
            role_id=role1_id,
            granted_by="admin"
        )
        session.add(user_role1)
        
        # Create invite tokens
        token1 = InviteToken(
            token=token1_name,
            created_by_user="admin",
            used=True,
            expires_at=datetime.utcnow() + timedelta(days=7), 
            used_by_user_id=user1_id
        )
        session.add(token1)
        
        # Create changelog entries
        changelog1 = ChangelogEntry(
            commit_id=f"abc123_{test_id}",
            original_message="Add export feature",
            friendly_description="Added database export functionality",
            change_type="new",
            commit_date=datetime.utcnow()
        )
        session.add(changelog1)
        
        session.commit()
        
        yield {
            "users": [user1, user2],
            "prayers": [prayer1, prayer2], 
            "attributes": [attr1, attr2],
            "marks": [mark1],
            "skips": [skip1],
            "logs": [log1],
            "roles": [role1],
            "user_roles": [user_role1],
            "tokens": [token1],
            "changelog": [changelog1],
            "prayer1_id": prayer1_id,
            "prayer2_id": prayer2_id,
            "user1_id": user1_id,
            "user2_id": user2_id
        }
        
        # Cleanup
        session.delete(user1)
        session.delete(user2)
        session.delete(prayer1)
        session.delete(prayer2)
        session.delete(attr1)
        session.delete(attr2)
        session.delete(mark1)
        session.delete(skip1)
        session.delete(log1)
        session.delete(role1)
        session.delete(user_role1)
        session.delete(token1)
        session.delete(changelog1)
        session.commit()
    
    def test_export_metadata_structure(self, export_service):
        """Test that export metadata has correct structure."""
        data = export_service.export_community_data()
        
        assert "export_metadata" in data
        metadata = data["export_metadata"]
        
        assert "version" in metadata
        assert "export_date" in metadata
        assert "source_instance" in metadata
        assert "schema_version" in metadata
        
        assert metadata["version"] == "1.0"
        assert metadata["source_instance"] == "thywill_community"
        
        # Verify date format
        export_date = datetime.fromisoformat(metadata["export_date"].replace('Z', '+00:00'))
        assert isinstance(export_date, datetime)
    
    def test_export_data_structure(self, export_service):
        """Test that export has all required data sections."""
        data = export_service.export_community_data()
        
        required_sections = [
            "export_metadata",
            "users", 
            "prayers",
            "prayer_attributes",
            "prayer_marks",
            "prayer_skips", 
            "prayer_activity_log",
            "roles",
            "user_roles",
            "changelog_entries"
        ]
        
        for section in required_sections:
            assert section in data
            assert isinstance(data[section], (list, dict))
    
    def test_flagged_prayers_excluded(self, export_service, sample_data): 
        """Test that flagged prayers are excluded from export."""
        data = export_service.export_community_data()
        
        # Check prayers section
        prayers = data["prayers"]
        prayer_ids = [p["id"] for p in prayers]
        
        assert sample_data["prayer1_id"] in prayer_ids  # Non-flagged prayer should be included
        assert sample_data["prayer2_id"] not in prayer_ids  # Flagged prayer should be excluded
    
    def test_flagged_prayer_attributes_excluded(self, export_service, sample_data):
        """Test that attributes for flagged prayers are excluded."""
        data = export_service.export_community_data()
        
        # Check prayer attributes
        attributes = data["prayer_attributes"] 
        prayer_ids = [attr["prayer_id"] for attr in attributes]
        attribute_names = [attr["attribute_name"] for attr in attributes]
        
        # Should include attributes for non-flagged prayers but exclude 'flagged' attributes
        # At minimum, we should not have flagged attributes and flagged prayer data
        assert sample_data["prayer2_id"] not in prayer_ids  # Flagged prayer excluded
        assert "flagged" not in attribute_names  # 'flagged' attribute excluded
        
        # If we have any attributes, they should be for non-flagged prayers
        if prayer_ids:
            assert all(pid != sample_data["prayer2_id"] for pid in prayer_ids)
    
    def test_flagged_prayer_marks_excluded(self, export_service, sample_data):
        """Test that marks for flagged prayers are excluded."""
        data = export_service.export_community_data()
        
        marks = data["prayer_marks"]
        prayer_ids = [mark["prayer_id"] for mark in marks]
        
        # Should not include marks for flagged prayers
        assert sample_data["prayer2_id"] not in prayer_ids
        
        # If we have any marks, they should be for non-flagged prayers
        if prayer_ids:
            assert all(pid != sample_data["prayer2_id"] for pid in prayer_ids)
    
    def test_flagged_prayer_skips_excluded(self, export_service, sample_data):
        """Test that skips for flagged prayers are excluded.""" 
        data = export_service.export_community_data()
        
        skips = data["prayer_skips"]
        prayer_ids = [skip["prayer_id"] for skip in skips]
        
        # Should not include skips for flagged prayers
        assert sample_data["prayer2_id"] not in prayer_ids
        
        # If we have any skips, they should be for non-flagged prayers
        if prayer_ids:
            assert all(pid != sample_data["prayer2_id"] for pid in prayer_ids)
    
    def test_flagged_prayer_activity_excluded(self, export_service, sample_data):
        """Test that activity logs for flagged prayers are excluded."""
        data = export_service.export_community_data()
        
        logs = data["prayer_activity_log"]
        prayer_ids = [log["prayer_id"] for log in logs]
        
        # Should not include logs for flagged prayers
        assert sample_data["prayer2_id"] not in prayer_ids
        
        # If we have any logs, they should be for non-flagged prayers
        if prayer_ids:
            assert all(pid != sample_data["prayer2_id"] for pid in prayer_ids)
    
    def test_users_export_structure(self, export_service, sample_data):
        """Test user export structure and content."""
        data = export_service.export_community_data()
        
        users = data["users"]
        assert len(users) >= 2
        
        user = users[0]
        required_fields = [
            "id", "display_name", "created_at", "religious_preference",
            "prayer_style", "invited_by_user_id", "welcome_message_dismissed"
        ]
        
        for field in required_fields:
            assert field in user
    
    def test_prayers_export_structure(self, export_service, sample_data):
        """Test prayer export structure and content."""
        data = export_service.export_community_data()
        
        prayers = data["prayers"]
        if prayers:  # Only test if there are non-flagged prayers
            prayer = prayers[0]
            required_fields = [
                "id", "author_id", "text", "generated_prayer", 
                "project_tag", "created_at", "target_audience"
            ]
            
            for field in required_fields:
                assert field in prayer
    
    def test_json_serialization(self, export_service):
        """Test that export data can be serialized to valid JSON."""
        json_string = export_service.export_to_json_string()
        
        # Should be valid JSON
        parsed = json.loads(json_string)
        assert isinstance(parsed, dict)
        
        # Should have proper structure
        assert "export_metadata" in parsed
        assert "users" in parsed
        assert "prayers" in parsed
    
    def test_datetime_serialization(self, export_service, sample_data):
        """Test that datetime fields are properly serialized."""
        data = export_service.export_community_data()
        json_string = export_service.export_to_json_string()
        
        # Should not raise exception during JSON serialization
        parsed = json.loads(json_string)
        
        # Check that datetime fields are in ISO format
        if parsed["users"]:
            user = parsed["users"][0]
            # Should be able to parse the datetime back
            created_at = datetime.fromisoformat(user["created_at"].replace('Z', '+00:00'))
            assert isinstance(created_at, datetime)
    
    def test_empty_database_export(self, export_service):
        """Test export behavior with empty database."""
        # This test runs against potentially empty database
        data = export_service.export_community_data()
        
        # Should still have all sections, even if empty
        required_sections = [
            "export_metadata", "users", "prayers", "prayer_attributes",
            "prayer_marks", "prayer_skips", "prayer_activity_log", 
            "roles", "user_roles", "changelog_entries"
        ]
        
        for section in required_sections:
            assert section in data
            if section != "export_metadata":
                assert isinstance(data[section], list)
    
    def test_export_excludes_sensitive_tables(self, export_service):
        """Test that sensitive tables are not included in export."""
        data = export_service.export_community_data()
        
        # These sensitive tables should NOT be in the export
        sensitive_sections = [
            "session", "authenticationrequest", "authapproval", 
            "authauditlog", "securitylog", "notificationstate", "invite_tokens"
        ]
        
        for section in sensitive_sections:
            assert section not in data
    
    def test_role_permissions_included(self, export_service, sample_data):
        """Test that role permissions are included in export."""
        data = export_service.export_community_data()
        
        roles = data["roles"]
        if roles:
            role = roles[0]
            assert "permissions" in role
            # Should be able to parse permissions as JSON
            permissions = json.loads(role["permissions"])
            assert isinstance(permissions, list)
    
    def test_zip_export_creation(self, export_service):
        """Test that ZIP export creates valid ZIP file with multiple JSON files."""
        zip_data, from_cache = export_service.export_to_zip()
        
        # Should return bytes
        assert isinstance(zip_data, bytes)
        assert len(zip_data) > 0
        
        # Should indicate cache status
        assert isinstance(from_cache, bool)
        
        # Should be valid ZIP file
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            file_list = zip_file.namelist()
            
            # Expected files
            expected_files = [
                'metadata.json',
                'users.json', 
                'prayers.json',
                'prayer_attributes.json',
                'prayer_marks.json',
                'prayer_skips.json',
                'prayer_activity_log.json',
                'roles.json',
                'user_roles.json',
                'changelog_entries.json',
                'README.txt'
            ]
            
            # Should contain all expected individual files
            for expected_file in expected_files:
                assert expected_file in file_list
            
            # Should also contain combined JSON file
            combined_files = [f for f in file_list if f.startswith('community_export_') and f.endswith('.json')]
            assert len(combined_files) == 1
            
            # Total JSON files should be individual tables + combined + metadata
            json_files = [f for f in file_list if f.endswith('.json')]
            assert len(json_files) == 11  # 9 table files + metadata + combined
            
            readme_files = [f for f in file_list if f == 'README.txt']
            assert len(readme_files) == 1
    
    def test_zip_export_json_content(self, export_service):
        """Test that ZIP export contains valid JSON data in individual files."""
        zip_data, from_cache = export_service.export_to_zip()
        
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            # Test metadata file
            metadata_content = zip_file.read('metadata.json').decode('utf-8')
            metadata = json.loads(metadata_content)
            assert metadata["version"] == "1.0"
            assert metadata["source_instance"] == "thywill_community"
            assert metadata["schema_version"] == "current"
            assert "export_date" in metadata
            
            # Test individual table files
            table_files = [
                'users.json', 'prayers.json', 'prayer_attributes.json',
                'prayer_marks.json', 'prayer_skips.json', 'prayer_activity_log.json',
                'roles.json', 'user_roles.json', 'changelog_entries.json'
            ]
            
            for table_file in table_files:
                # Each file should contain valid JSON array
                table_content = zip_file.read(table_file).decode('utf-8')
                table_data = json.loads(table_content)
                assert isinstance(table_data, list)
            
            # Test combined file exists and has correct structure
            combined_files = [f for f in zip_file.namelist() if f.startswith('community_export_')]
            assert len(combined_files) == 1
            
            combined_content = zip_file.read(combined_files[0]).decode('utf-8')
            combined_data = json.loads(combined_content)
            
            # Should have expected structure
            assert "export_metadata" in combined_data
            assert "users" in combined_data
            assert "prayers" in combined_data
            
            # Verify individual files match combined file data
            direct_data = export_service.export_community_data()
            
            for section in ["users", "prayers", "prayer_attributes", "prayer_marks", 
                          "prayer_skips", "prayer_activity_log", "roles", "user_roles", "changelog_entries"]:
                # Individual file should match section in combined data
                individual_content = zip_file.read(f"{section}.json").decode('utf-8')
                individual_data = json.loads(individual_content)
                assert individual_data == direct_data[section]
    
    def test_zip_export_readme_content(self, export_service):
        """Test that ZIP export contains proper README."""
        zip_data, from_cache = export_service.export_to_zip()
        
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            # Extract README content
            readme_content = zip_file.read('README.txt').decode('utf-8')
            
            # Should contain expected sections
            assert "ThyWill Community Export" in readme_content
            assert "CONTENTS" in readme_content
            assert "DATA INCLUDED" in readme_content
            assert "DATA EXCLUDED" in readme_content
            assert "FILE STRUCTURE" in readme_content
            assert "USAGE" in readme_content
            
            # Should contain version info
            assert "Export Version: 1.0" in readme_content
    
    def test_export_info_statistics(self, export_service):
        """Test export info provides accurate statistics."""
        info = export_service.get_export_info()
        
        # Should have required fields
        required_fields = ["users", "prayers", "roles", "changelog_entries", "estimated_size", "estimated_bytes"]
        for field in required_fields:
            assert field in info
        
        # Values should be non-negative integers (except size strings)
        assert isinstance(info["users"], int) and info["users"] >= 0
        assert isinstance(info["prayers"], int) and info["prayers"] >= 0
        assert isinstance(info["roles"], int) and info["roles"] >= 0
        assert isinstance(info["changelog_entries"], int) and info["changelog_entries"] >= 0
        assert isinstance(info["estimated_bytes"], int) and info["estimated_bytes"] >= 0
        assert isinstance(info["estimated_size"], str)
    
    def test_export_info_size_formatting(self, export_service):
        """Test that export info formats file sizes correctly."""
        info = export_service.get_export_info()
        
        size_str = info["estimated_size"]
        
        # Should end with bytes, KB, or MB
        assert any(size_str.endswith(unit) for unit in ["bytes", "KB", "MB"])
        
        # Should start with a number
        size_part = size_str.split()[0]
        assert size_part.isdigit()
    
    def test_individual_json_files_structure(self, export_service):
        """Test that individual JSON files have correct structure and content."""
        zip_data, from_cache = export_service.export_to_zip()
        
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            # Test that each individual file is a valid JSON array
            table_files = {
                'users.json': 'users',
                'prayers.json': 'prayers', 
                'prayer_attributes.json': 'prayer_attributes',
                'prayer_marks.json': 'prayer_marks',
                'prayer_skips.json': 'prayer_skips',
                'prayer_activity_log.json': 'prayer_activity_log',
                'roles.json': 'roles',
                'user_roles.json': 'user_roles',
                'changelog_entries.json': 'changelog_entries'
            }
            
            # Get original data for comparison
            original_data = export_service.export_community_data()
            
            for filename, section_name in table_files.items():
                # Read individual file
                file_content = zip_file.read(filename).decode('utf-8')
                file_data = json.loads(file_content)
                
                # Should be a list
                assert isinstance(file_data, list)
                
                # Should match the corresponding section in original data
                assert file_data == original_data[section_name]
                
                # Should be properly formatted JSON (no parse errors)
                # Re-encode and decode to verify formatting
                reformatted = json.dumps(file_data, indent=2, ensure_ascii=False)
                assert json.loads(reformatted) == file_data
    
    def test_export_caching_functionality(self, export_service):
        """Test that export caching works correctly."""
        # Clear any existing cache files first
        import os
        import glob
        cache_pattern = os.path.join(export_service.cache_dir, "export_*.zip")
        for cache_file in glob.glob(cache_pattern):
            try:
                os.remove(cache_file)
            except OSError:
                pass
        
        # First export should not be from cache
        zip_data1, from_cache1 = export_service.export_to_zip()
        assert not from_cache1
        assert isinstance(zip_data1, bytes)
        assert len(zip_data1) > 0
        
        # Second export should be from cache (same data fingerprint)
        zip_data2, from_cache2 = export_service.export_to_zip()
        
        # Data should be identical
        assert zip_data1 == zip_data2
        
        # Second call should use cache
        assert from_cache2
        
        # Test cache bypass
        zip_data3, from_cache3 = export_service.export_to_zip(use_cache=False)
        assert not from_cache3
        # Data content should be the same size (timestamps may differ)
        assert len(zip_data1) == len(zip_data3) or abs(len(zip_data1) - len(zip_data3)) < 100
    
    def test_export_cache_info(self, export_service):
        """Test that export info includes cache information."""
        info = export_service.get_export_info()
        
        # Should include cache-related fields
        assert "cache_available" in info
        assert "cache_age_minutes" in info  
        assert "cache_ttl_minutes" in info
        
        assert isinstance(info["cache_available"], bool)
        assert isinstance(info["cache_age_minutes"], int)
        assert isinstance(info["cache_ttl_minutes"], int)
        assert info["cache_ttl_minutes"] > 0
    
    def test_export_without_cache(self, export_service):
        """Test that export can be forced without cache."""
        # Generate export without cache
        zip_data, from_cache = export_service.export_to_zip(use_cache=False)
        
        # Should not be from cache
        assert not from_cache
        assert isinstance(zip_data, bytes)
        assert len(zip_data) > 0
        
        # Should still be valid ZIP
        zip_buffer = io.BytesIO(zip_data)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            files = zip_file.namelist()
            assert 'metadata.json' in files
            assert 'README.txt' in files
    
