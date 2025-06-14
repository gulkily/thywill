#!/usr/bin/env python3
"""
Test archive-first prayer submission functionality
"""

import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Mock the configuration before importing services
import os
os.environ['TEXT_ARCHIVE_ENABLED'] = 'true'
os.environ['TEXT_ARCHIVE_BASE_DIR'] = tempfile.mkdtemp()

from app_helpers.services.archive_first_service import create_prayer_with_text_archive
from app_helpers.services.text_archive_service import TextArchiveService


def test_archive_first_prayer_creation():
    """Test creating prayer with archive-first approach"""
    
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    print(f"Testing in directory: {temp_dir}")
    
    try:
        # Initialize service with test directory
        service = TextArchiveService(base_dir=temp_dir)
        
        # Mock prayer data
        prayer_data = {
            'author_id': 'user123',
            'author_display_name': 'TestUser1',
            'text': 'Please pray for my test request',
            'generated_prayer': 'Dear Lord, we ask for your blessing on this test...',
            'project_tag': 'testing',
            'target_audience': 'all',
            'created_at': datetime(2024, 6, 15, 10, 30)
        }
        
        print("Testing archive-first prayer creation...")
        
        # We can't actually create database records without a full database setup,
        # but we can test the archive creation part
        print("Creating prayer archive...")
        
        # Test just the archive creation part
        archive_data = {
            'id': 'test123',
            'author': prayer_data['author_display_name'],
            'text': prayer_data['text'],
            'generated_prayer': prayer_data['generated_prayer'],
            'project_tag': prayer_data['project_tag'],
            'target_audience': prayer_data['target_audience'],
            'created_at': prayer_data['created_at']
        }
        
        file_path = service.create_prayer_archive(archive_data)
        print(f"Archive created at: {file_path}")
        
        # Verify file exists and has correct content
        assert Path(file_path).exists(), "Archive file was not created"
        
        content = Path(file_path).read_text()
        print("Archive content:")
        print("-" * 50)
        print(content)
        print("-" * 50)
        
        # Verify archive content format
        assert "Prayer test123 by TestUser1" in content
        assert "Submitted June 15 2024 at 10:30" in content
        assert "Please pray for my test request" in content
        assert "Project: testing" in content
        assert "Activity:" in content
        
        # Test appending activity
        print("\nTesting activity appending...")
        service.append_prayer_activity(file_path, "prayed", "AnotherUser")
        service.append_prayer_activity(file_path, "answered", "TestUser1")
        service.append_prayer_activity(file_path, "testimony", "TestUser1", "Prayer was answered!")
        
        updated_content = Path(file_path).read_text()
        print("Updated archive content:")
        print("-" * 50)
        print(updated_content)
        print("-" * 50)
        
        # Verify activities were added
        assert "AnotherUser prayed this prayer" in updated_content
        assert "TestUser1 marked this prayer as answered" in updated_content
        assert "TestUser1 added testimony: Prayer was answered!" in updated_content
        
        # Test parsing the archive back to structured data
        print("\nTesting archive parsing...")
        parsed_data, parsed_activities = service.parse_prayer_archive(file_path)
        
        print("Parsed prayer data:", parsed_data)
        print("Parsed activities:", parsed_activities)
        
        # Verify parsed data
        assert parsed_data['id'] == 'test123'
        assert parsed_data['author'] == 'TestUser1'
        assert parsed_data['original_request'] == 'Please pray for my test request'
        assert parsed_data['project_tag'] == 'testing'
        
        # Verify parsed activities
        assert len(parsed_activities) == 3
        prayed_activities = [a for a in parsed_activities if a['action'] == 'prayed']
        assert len(prayed_activities) == 1
        assert prayed_activities[0]['user'] == 'AnotherUser'
        
        answered_activities = [a for a in parsed_activities if a['action'] == 'answered']
        assert len(answered_activities) == 1
        assert answered_activities[0]['user'] == 'TestUser1'
        
        testimony_activities = [a for a in parsed_activities if a['action'] == 'testimony']
        assert len(testimony_activities) == 1
        assert testimony_activities[0]['user'] == 'TestUser1'
        
        print("✅ Archive-first prayer creation test passed!")
        
        # Test monthly activity logging
        print("\nTesting monthly activity logging...")
        activity_file = service.append_monthly_activity(
            "submitted prayer test123", "TestUser1", "test123", "testing"
        )
        activity_file = service.append_monthly_activity(
            "prayed for prayer test123", "AnotherUser", "test123"
        )
        
        activity_content = Path(activity_file).read_text()
        print("Monthly activity content:")
        print("-" * 50)
        print(activity_content)
        print("-" * 50)
        
        assert "TestUser1 submitted prayer test123 (testing)" in activity_content
        assert "AnotherUser prayed for prayer test123" in activity_content
        
        print("✅ Monthly activity logging test passed!")
        
        print("\n🎉 All archive-first tests passed successfully!")
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"Cleaned up test directory: {temp_dir}")


if __name__ == "__main__":
    test_archive_first_prayer_creation()