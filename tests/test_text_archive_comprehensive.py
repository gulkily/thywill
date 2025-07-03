#!/usr/bin/env python3
"""
Comprehensive test suite for text archive system

This test suite covers:
- TextArchiveService functionality
- Archive-first service functionality  
- Edge cases and error handling
- File parsing and validation
- Archive consistency validation
"""

import tempfile
import shutil
import os
from datetime import datetime, timedelta
from pathlib import Path
import pytest

# Mock the configuration before importing services
os.environ['TEXT_ARCHIVE_ENABLED'] = 'true'
os.environ['TEXT_ARCHIVE_BASE_DIR'] = tempfile.mkdtemp()

from app_helpers.services.text_archive_service import TextArchiveService
from app_helpers.services.archive_first_service import create_user_with_text_archive


class TestTextArchiveService:
    """Test TextArchiveService core functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.service = TextArchiveService(base_dir=self.temp_dir)
        
    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_service_initialization(self):
        """Test TextArchiveService initialization"""
        assert self.service.base_dir == Path(self.temp_dir)
        assert self.service.enabled == True
        
        # Verify directory structure was created
        assert (Path(self.temp_dir) / "prayers").exists()
        assert (Path(self.temp_dir) / "users").exists()
        assert (Path(self.temp_dir) / "activity").exists()
    
    def test_prayer_filename_generation(self):
        """Test prayer filename generation with conflict resolution"""
        created_at = datetime(2024, 6, 15, 14, 30)
        
        # First filename should be basic format
        filename1 = self.service.generate_prayer_filename(created_at, 123)
        expected_path = Path(self.temp_dir) / "prayers" / "2024" / "06" / "2024_06_15_prayer_at_1430.txt"
        assert filename1 == str(expected_path)
        
        # Create the file to test conflict resolution
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.touch()
        
        # Second filename should have conflict suffix
        filename2 = self.service.generate_prayer_filename(created_at, 124)
        expected_path2 = Path(self.temp_dir) / "prayers" / "2024" / "06" / "2024_06_15_prayer_at_1430_2.txt"
        assert filename2 == str(expected_path2)
    
    def test_prayer_archive_creation(self):
        """Test prayer archive file creation"""
        prayer_data = {
            'id': 'test123',
            'author': 'John_Doe',
            'text': 'Please pray for my health and recovery.',
            'generated_prayer': 'Heavenly Father, we ask for healing...',
            'project_tag': 'health',
            'target_audience': 'all',
            'created_at': datetime(2024, 6, 15, 14, 30)
        }
        
        file_path = self.service.create_prayer_archive(prayer_data)
        
        # Verify file was created
        assert os.path.exists(file_path)
        
        # Verify file content
        content = Path(file_path).read_text()
        assert "Prayer test123 by John_Doe" in content
        assert "Submitted June 15 2024 at 14:30" in content
        assert "Project: health" in content
        assert "Audience: all" in content
        assert "Please pray for my health and recovery." in content
        assert "Generated Prayer:" in content
        assert "Heavenly Father, we ask for healing..." in content
        assert "Activity:" in content
    
    def test_prayer_activity_logging(self):
        """Test prayer activity logging"""
        # Create a prayer archive first
        prayer_data = {
            'id': 'test456',
            'author': 'Mary_Smith',
            'text': 'Pray for my family.',
            'created_at': datetime(2024, 6, 15, 14, 30)
        }
        
        file_path = self.service.create_prayer_archive(prayer_data)
        
        # Add various activities
        self.service.append_prayer_activity(file_path, "prayed", "John_Doe")
        self.service.append_prayer_activity(file_path, "answered", "Mary_Smith")
        self.service.append_prayer_activity(file_path, "testimony", "Mary_Smith", "God answered wonderfully!")
        self.service.append_prayer_activity(file_path, "archived", "Mary_Smith")
        self.service.append_prayer_activity(file_path, "restored", "Mary_Smith")
        
        # Verify activities were logged
        content = Path(file_path).read_text()
        assert "John_Doe prayed this prayer" in content
        assert "Mary_Smith marked this prayer as answered" in content
        assert "Mary_Smith added testimony: God answered wonderfully!" in content
        assert "Mary_Smith archived this prayer" in content
        assert "Mary_Smith restored this prayer" in content
    
    def test_user_registration_logging(self):
        """Test user registration logging"""
        # Test invited user
        archive_path1 = self.service.append_user_registration("Alice_Johnson", "Bob_Wilson")
        
        # Test direct user
        archive_path2 = self.service.append_user_registration("Charlie_Brown", "")
        
        # Verify files were created
        assert os.path.exists(archive_path1)
        assert os.path.exists(archive_path2)
        assert archive_path1 == archive_path2  # Same monthly file
        
        # Verify content
        content = Path(archive_path1).read_text()
        assert "Alice_Johnson joined on invitation from Bob_Wilson" in content
        assert "Charlie_Brown joined directly" in content
    
    def test_monthly_activity_logging(self):
        """Test monthly activity logging with date headers"""
        # Add activities for today
        activity_path = self.service.append_monthly_activity("submitted prayer 123", "John_Doe", 123, "health")
        self.service.append_monthly_activity("prayed for prayer 123", "Mary_Smith", 123)
        self.service.append_monthly_activity("answered prayer 456", "Alice_Johnson", 456)
        
        # Verify file was created
        assert os.path.exists(activity_path)
        
        # Verify content
        content = Path(activity_path).read_text()
        today = datetime.now().strftime("%B %d %Y")
        assert f"Activity for {datetime.now().strftime('%B %Y')}" in content
        assert today in content
        assert "John_Doe submitted prayer 123 (health)" in content
        assert "Mary_Smith prayed for prayer 123" in content
        assert "Alice_Johnson answered prayer 456" in content
    
    def test_archive_parsing(self):
        """Test parsing of prayer archive files"""
        # Create a complex prayer archive
        prayer_data = {
            'id': 'parse_test',
            'author': 'Test_User',
            'text': 'Complex prayer request for testing.',
            'generated_prayer': 'Generated prayer text here.',
            'project_tag': 'testing',
            'target_audience': 'developers',
            'created_at': datetime(2024, 6, 15, 14, 30)
        }
        
        file_path = self.service.create_prayer_archive(prayer_data)
        
        # Add multiple activities
        self.service.append_prayer_activity(file_path, "prayed", "User1")
        self.service.append_prayer_activity(file_path, "prayed", "User2")
        self.service.append_prayer_activity(file_path, "answered", "Test_User")
        self.service.append_prayer_activity(file_path, "testimony", "Test_User", "Amazing answer!")
        self.service.append_prayer_activity(file_path, "archived", "Test_User")
        
        # Parse the archive
        parsed_data, parsed_activities = self.service.parse_prayer_archive(file_path)
        
        # Verify parsed data
        assert parsed_data['id'] == 'parse_test'
        assert parsed_data['author'] == 'Test_User'
        assert parsed_data['project_tag'] == 'testing'
        assert parsed_data['target_audience'] == 'developers'
        assert parsed_data['original_request'] == 'Complex prayer request for testing.'
        assert parsed_data['generated_prayer'] == 'Generated prayer text here.'
        
        # Verify parsed activities
        assert len(parsed_activities) == 5
        
        # Count activity types
        activity_counts = {}
        for activity in parsed_activities:
            action = activity['action']
            activity_counts[action] = activity_counts.get(action, 0) + 1
        
        assert activity_counts['prayed'] == 2
        assert activity_counts['answered'] == 1
        assert activity_counts['testimony'] == 1
        assert activity_counts['archived'] == 1
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Test disabled service
        disabled_service = TextArchiveService(base_dir=self.temp_dir)
        disabled_service.enabled = False
        
        # Should return empty strings when disabled
        assert disabled_service.create_prayer_archive({}) == ""
        assert disabled_service.append_user_registration("test", "test") == ""
        assert disabled_service.append_monthly_activity("test", "test") == ""
        
        # Test invalid file operations
        try:
            self.service.read_archive_file("/nonexistent/file.txt")
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass
        
        # Test malformed archive parsing
        malformed_file = Path(self.temp_dir) / "malformed.txt"
        malformed_file.write_text("This is not a valid prayer archive")
        
        # Should handle malformed files gracefully
        parsed_data, parsed_activities = self.service.parse_prayer_archive(str(malformed_file))
        assert isinstance(parsed_data, dict)
        assert isinstance(parsed_activities, list)
    
    def test_file_atomic_operations(self):
        """Test atomic file operations"""
        test_file = Path(self.temp_dir) / "atomic_test.txt"
        test_content = "Atomic test content"
        
        # Test atomic write
        self.service._write_file_atomic(str(test_file), test_content)
        assert test_file.exists()
        assert test_file.read_text() == test_content
        
        # Test atomic append
        self.service._append_to_file(str(test_file), "Appended line")
        content = test_file.read_text()
        assert "Atomic test content" in content
        assert "Appended line" in content


class TestArchiveFirstService:
    """Test archive-first service functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        os.environ['TEXT_ARCHIVE_BASE_DIR'] = self.temp_dir
        
    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_user_creation_with_specific_id(self):
        """Test user creation with specific ID"""
        user_data = {
            'display_name': 'TestUser123',
            'invited_by_display_name': 'InviterUser',
            'religious_preference': 'christian',
            'prayer_style': 'contemporary',
            'invited_by_user_id': 'inviter123',
            'invite_token_used': 'token789'
        }
        
        user, archive_path = create_user_with_text_archive(user_data, 'specific_id_123')
        
        # Verify user was created with specific ID
        assert user.id == 'specific_id_123'
        assert user.display_name == 'TestUser123'
        assert user.religious_preference == 'christian'
        assert user.text_file_path == archive_path
        
        # Verify archive file exists and contains entry
        if archive_path and Path(archive_path).exists():
            content = Path(archive_path).read_text()
            assert "TestUser123 joined on invitation from InviterUser" in content
    
    def test_user_creation_with_auto_id(self):
        """Test user creation with auto-generated ID"""
        user_data = {
            'display_name': 'AutoIdUser',
            'religious_preference': 'unspecified'
        }
        
        user, archive_path = create_user_with_text_archive(user_data)
        
        # Verify user was created with auto-generated ID
        assert user.id is not None
        assert len(user.id) > 10  # Should be a hex string
        assert user.display_name == 'AutoIdUser'
        assert user.religious_preference == 'unspecified'
        assert user.text_file_path == archive_path


class TestArchiveIntegration:
    """Test integration scenarios and data consistency"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.service = TextArchiveService(base_dir=self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_bidirectional_data_consistency(self):
        """Test that data can be written and read back consistently"""
        # Create prayer archive
        original_data = {
            'id': 'consistency_test',
            'author': 'ConsistencyUser',
            'text': 'Test prayer for consistency check.',
            'generated_prayer': 'Generated prayer for testing.',
            'project_tag': 'testing',
            'target_audience': 'developers',
            'created_at': datetime(2024, 6, 15, 14, 30)
        }
        
        file_path = self.service.create_prayer_archive(original_data)
        
        # Parse it back
        parsed_data, _ = self.service.parse_prayer_archive(file_path)
        
        # Verify data consistency
        assert parsed_data['id'] == original_data['id']
        assert parsed_data['author'] == original_data['author']
        assert parsed_data['original_request'] == original_data['text']
        assert parsed_data['generated_prayer'] == original_data['generated_prayer']
        assert parsed_data['project_tag'] == original_data['project_tag']
        assert parsed_data['target_audience'] == original_data['target_audience']
    
    def test_concurrent_activity_logging(self):
        """Test multiple activities logged to same prayer"""
        # Create prayer
        prayer_data = {
            'id': 'concurrent_test',
            'author': 'AuthorUser',
            'text': 'Test prayer for concurrent activities.',
            'created_at': datetime(2024, 6, 15, 14, 30)
        }
        
        file_path = self.service.create_prayer_archive(prayer_data)
        
        # Add multiple activities rapidly
        activities = [
            ("prayed", "User1"),
            ("prayed", "User2"),
            ("prayed", "User3"),
            ("answered", "AuthorUser"),
            ("testimony", "AuthorUser", "Great testimony!"),
            ("archived", "AuthorUser"),
            ("restored", "AuthorUser")
        ]
        
        for activity in activities:
            if len(activity) == 3:
                self.service.append_prayer_activity(file_path, activity[0], activity[1], activity[2])
            else:
                self.service.append_prayer_activity(file_path, activity[0], activity[1])
        
        # Verify all activities were logged
        _, parsed_activities = self.service.parse_prayer_archive(file_path)
        assert len(parsed_activities) == 7
        
        # Verify activity types
        activity_types = [a['action'] for a in parsed_activities]
        assert activity_types.count('prayed') == 3
        assert activity_types.count('answered') == 1
        assert activity_types.count('testimony') == 1
        assert activity_types.count('archived') == 1
        assert activity_types.count('restored') == 1
    
    def test_monthly_file_organization(self):
        """Test that files are organized by month correctly"""
        # Create activities across different months
        now = datetime.now()
        
        # Current month
        self.service.append_monthly_activity("current month activity", "User1")
        
        # Verify monthly file structure
        current_month_file = Path(self.temp_dir) / "activity" / f"activity_{now.year}_{now.month:02d}.txt"
        assert current_month_file.exists()
        
        content = current_month_file.read_text()
        assert "current month activity" in content
        assert f"Activity for {now.strftime('%B %Y')}" in content


def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("🚀 Running comprehensive text archive system tests...")
    
    # Test classes
    test_classes = [
        TestTextArchiveService,
        TestArchiveFirstService, 
        TestArchiveIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}...")
        test_instance = test_class()
        
        # Get all test methods
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            try:
                # Setup
                if hasattr(test_instance, 'setup_method'):
                    test_instance.setup_method()
                
                # Run test
                getattr(test_instance, test_method)()
                
                print(f"  ✅ {test_method}")
                passed_tests += 1
                
            except Exception as e:
                print(f"  ❌ {test_method}: {e}")
                failed_tests += 1
                
            finally:
                # Teardown
                if hasattr(test_instance, 'teardown_method'):
                    try:
                        test_instance.teardown_method()
                    except:
                        pass
    
    print(f"\n📊 Test Results:")
    print(f"  Total tests: {total_tests}")
    print(f"  Passed: {passed_tests}")
    print(f"  Failed: {failed_tests}")
    print(f"  Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 All tests passed! Text archive system is working correctly.")
        return True
    else:
        print(f"\n⚠️  {failed_tests} tests failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)