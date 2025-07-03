#!/usr/bin/env python3
"""
Basic test for TextArchiveService functionality
"""

import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from app_helpers.services.text_archive_service import TextArchiveService


def test_basic_prayer_archive():
    """Test basic prayer archive creation and activity appending"""
    
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    print(f"Testing in directory: {temp_dir}")
    
    try:
        # Initialize service with test directory
        service = TextArchiveService(base_dir=temp_dir)
        
        # Test prayer data
        prayer_data = {
            'id': 12345,
            'author': 'Mary1',
            'text': 'Please pray for my family during this difficult time.',
            'generated_prayer': 'Heavenly Father, we lift up Mary\'s family...',
            'project_tag': 'family',
            'target_audience': 'general',
            'created_at': datetime(2024, 6, 15, 6, 55)
        }
        
        # Create prayer archive
        print("Creating prayer archive...")
        file_path = service.create_prayer_archive(prayer_data)
        print(f"Archive created at: {file_path}")
        
        # Verify file exists
        assert Path(file_path).exists(), "Archive file was not created"
        
        # Read and verify content
        content = Path(file_path).read_text()
        print("Archive content:")
        print("-" * 50)
        print(content)
        print("-" * 50)
        
        # Verify content format
        assert "Prayer 12345 by Mary1" in content
        assert "Submitted June 15 2024 at 06:55" in content
        assert "Please pray for my family during this difficult time." in content
        assert "Project: family" in content
        assert "Activity:" in content
        
        # Test appending activity
        print("\nAppending prayer activity...")
        service.append_prayer_activity(file_path, "prayed", "John1")
        service.append_prayer_activity(file_path, "prayed", "Sarah2")
        service.append_prayer_activity(file_path, "answered", "Mary1")
        service.append_prayer_activity(file_path, "testimony", "Mary1", "Thank you all! The situation has improved greatly.")
        
        # Read updated content
        updated_content = Path(file_path).read_text()
        print("Updated archive content:")
        print("-" * 50)
        print(updated_content)
        print("-" * 50)
        
        # Verify activities were added
        assert "John1 prayed this prayer" in updated_content
        assert "Sarah2 prayed this prayer" in updated_content
        assert "Mary1 marked this prayer as answered" in updated_content
        assert "Mary1 added testimony: Thank you all!" in updated_content
        
        print("✅ Prayer archive test passed!")
        
        # Test user registration
        print("\nTesting user registration archive...")
        user_file = service.append_user_registration("TestUser1", "Mary1")
        user_file = service.append_user_registration("TestUser2", "John1")
        user_file = service.append_user_registration("TestUser3", "")  # Direct signup
        
        user_content = Path(user_file).read_text()
        print("User registration content:")
        print("-" * 50)
        print(user_content)
        print("-" * 50)
        
        assert "TestUser1 joined on invitation from Mary1" in user_content
        assert "TestUser3 joined directly" in user_content
        
        print("✅ User registration test passed!")
        
        # Test monthly activity
        print("\nTesting monthly activity archive...")
        activity_file = service.append_monthly_activity("submitted prayer 12345", "Mary1", 12345, "family")
        activity_file = service.append_monthly_activity("prayed for prayer 12345", "John1", 12345)
        activity_file = service.append_monthly_activity("registered via invitation", "TestUser1")
        
        activity_content = Path(activity_file).read_text()
        print("Monthly activity content:")
        print("-" * 50)
        print(activity_content)
        print("-" * 50)
        
        # Check that date header was added only once
        today = datetime.now().strftime("%B %d %Y")
        date_count = activity_content.count(today)
        assert date_count == 1, f"Expected 1 date header, found {date_count}"
        
        assert "Mary1 submitted prayer 12345 (family)" in activity_content
        assert "John1 prayed for prayer 12345" in activity_content
        assert "TestUser1 registered via invitation" in activity_content
        
        print("✅ Monthly activity test passed!")
        
        print("\n🎉 All basic tests passed successfully!")
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"Cleaned up test directory: {temp_dir}")


if __name__ == "__main__":
    test_basic_prayer_archive()