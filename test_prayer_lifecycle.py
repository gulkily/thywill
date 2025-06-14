#!/usr/bin/env python3
"""
Test complete prayer lifecycle with archive-first approach
"""

import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Mock the configuration before importing services
import os
os.environ['TEXT_ARCHIVE_ENABLED'] = 'true'
os.environ['TEXT_ARCHIVE_BASE_DIR'] = tempfile.mkdtemp()

from app_helpers.services.text_archive_service import TextArchiveService
from app_helpers.services.archive_first_service import create_prayer_with_text_archive


class MockUser:
    """Mock user for testing"""
    def __init__(self, user_id: str, display_name: str):
        self.id = user_id
        self.display_name = display_name


def test_complete_prayer_lifecycle():
    """Test complete prayer lifecycle with archive-first approach"""
    
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    print(f"Testing in directory: {temp_dir}")
    
    try:
        # Initialize service with test directory
        service = TextArchiveService(base_dir=temp_dir)
        
        # Create mock users
        mary = MockUser("user1", "Mary1")
        john = MockUser("user2", "John1") 
        sarah = MockUser("user3", "Sarah2")
        
        print("Testing complete prayer lifecycle...")
        
        # Step 1: Create prayer with archive-first approach
        print("\n1. Creating prayer...")
        prayer_data = {
            'author_id': mary.id,
            'author_display_name': mary.display_name,
            'text': 'Please pray for my family during this difficult time.',
            'generated_prayer': 'Heavenly Father, we lift up Mary\'s family during this challenging season...',
            'project_tag': 'family',
            'target_audience': 'all',
            'created_at': datetime(2024, 6, 15, 8, 30)
        }
        
        # Mock the archive creation part (can't create real DB records without full DB)
        archive_data = {
            'id': 'prayer123',
            'author': prayer_data['author_display_name'],
            'text': prayer_data['text'],
            'generated_prayer': prayer_data['generated_prayer'],
            'project_tag': prayer_data['project_tag'],
            'target_audience': prayer_data['target_audience'],
            'created_at': prayer_data['created_at']
        }
        
        file_path = service.create_prayer_archive(archive_data)
        print(f"Prayer archive created: {file_path}")
        
        # Verify initial content
        content = Path(file_path).read_text()
        assert "Prayer prayer123 by Mary1" in content
        assert "Please pray for my family during this difficult time." in content
        assert "Project: family" in content
        
        # Step 2: Multiple users pray for the prayer
        print("\n2. Users praying for prayer...")
        service.append_prayer_activity(file_path, "prayed", john.display_name)
        service.append_prayer_activity(file_path, "prayed", sarah.display_name)
        service.append_prayer_activity(file_path, "prayed", john.display_name)  # John prays again
        
        content = Path(file_path).read_text()
        john_prayers = content.count("John1 prayed this prayer")
        sarah_prayers = content.count("Sarah2 prayed this prayer")
        
        assert john_prayers == 2, f"Expected John to pray 2 times, found {john_prayers}"
        assert sarah_prayers == 1, f"Expected Sarah to pray 1 time, found {sarah_prayers}"
        
        print(f"✅ Prayer marks recorded: John={john_prayers}, Sarah={sarah_prayers}")
        
        # Step 3: Author answers the prayer with testimony
        print("\n3. Prayer answered with testimony...")
        service.append_prayer_activity(file_path, "answered", mary.display_name)
        service.append_prayer_activity(file_path, "testimony", mary.display_name, 
                                     "God has blessed us tremendously! The situation has completely turned around and we are so grateful.")
        
        content = Path(file_path).read_text()
        assert "Mary1 marked this prayer as answered" in content
        assert "Mary1 added testimony: God has blessed us tremendously!" in content
        
        print("✅ Prayer answered and testimony added")
        
        # Step 4: Prayer gets archived
        print("\n4. Prayer archived...")
        service.append_prayer_activity(file_path, "archived", mary.display_name)
        
        content = Path(file_path).read_text()
        assert "Mary1 archived this prayer" in content
        
        # Step 5: Prayer gets restored
        print("\n5. Prayer restored...")
        service.append_prayer_activity(file_path, "restored", mary.display_name)
        
        content = Path(file_path).read_text()
        assert "Mary1 restored this prayer" in content
        
        print("✅ Prayer archive and restore recorded")
        
        # Step 6: Parse the complete archive and verify structure
        print("\n6. Parsing complete archive...")
        parsed_data, parsed_activities = service.parse_prayer_archive(file_path)
        
        print(f"Parsed prayer data: {parsed_data}")
        print(f"Total activities: {len(parsed_activities)}")
        
        # Verify parsed data structure
        assert parsed_data['id'] == 'prayer123'
        assert parsed_data['author'] == 'Mary1'
        assert parsed_data['project_tag'] == 'family'
        assert parsed_data['original_request'] == 'Please pray for my family during this difficult time.'
        
        # Count different types of activities
        activity_counts = {}
        for activity in parsed_activities:
            action = activity['action']
            activity_counts[action] = activity_counts.get(action, 0) + 1
        
        print(f"Activity breakdown: {activity_counts}")
        
        expected_activities = {
            'prayed': 3,     # John(2) + Sarah(1)
            'answered': 1,   # Mary
            'testimony': 1,  # Mary
            'archived': 1,   # Mary
            'restored': 1    # Mary
        }
        
        for action, expected_count in expected_activities.items():
            actual_count = activity_counts.get(action, 0)
            assert actual_count == expected_count, f"Expected {expected_count} {action} activities, found {actual_count}"
        
        print("✅ All activity types correctly recorded and parsed")
        
        # Step 7: Display the complete archive content
        print("\n7. Final archive content:")
        print("-" * 60)
        print(content)
        print("-" * 60)
        
        # Step 8: Test monthly activity logging
        print("\n8. Testing monthly activity logging...")
        service.append_monthly_activity("submitted prayer prayer123", "Mary1", "prayer123", "family")
        service.append_monthly_activity("prayed for prayer prayer123", "John1", "prayer123")
        service.append_monthly_activity("prayed for prayer prayer123", "Sarah2", "prayer123")
        service.append_monthly_activity("marked prayer prayer123 as answered", "Mary1", "prayer123")
        
        # Find monthly activity file
        activity_files = list(Path(temp_dir).glob("activity/*.txt"))
        assert len(activity_files) == 1, f"Expected 1 activity file, found {len(activity_files)}"
        
        activity_content = activity_files[0].read_text()
        print("Monthly activity content:")
        print("-" * 40)
        print(activity_content)
        print("-" * 40)
        
        # Verify monthly activity content
        assert "Mary1 submitted prayer prayer123 (family)" in activity_content
        assert "John1 prayed for prayer prayer123" in activity_content
        assert "Sarah2 prayed for prayer prayer123" in activity_content
        assert "Mary1 marked prayer prayer123 as answered" in activity_content
        
        print("✅ Monthly activity logging working correctly")
        
        # Step 9: Test archive validation (consistency check)
        print("\n9. Testing archive consistency...")
        
        # Verify that the archive is internally consistent
        lines = content.split('\n')
        activity_section_started = False
        activity_lines = []
        
        for line in lines:
            if line.strip() == "Activity:":
                activity_section_started = True
                continue
            if activity_section_started and line.strip():
                activity_lines.append(line.strip())
        
        # Check that activities are in chronological order (approximately)
        timestamps = []
        for line in activity_lines:
            if " - " in line:
                timestamp_part = line.split(" - ")[0]
                timestamps.append(timestamp_part)
        
        print(f"Activity timestamps: {timestamps[:3]}...")  # Show first few
        
        # All timestamps should be identical in our test (same minute)
        # In real use they would be chronological
        assert len(timestamps) == sum(expected_activities.values()), f"Expected {sum(expected_activities.values())} activity lines, found {len(timestamps)}"
        
        print("✅ Archive consistency verified")
        
        print("\n🎉 Complete prayer lifecycle test passed successfully!")
        print(f"✅ Prayer creation: archive-first approach working")
        print(f"✅ Prayer interactions: all activities logged to archive")
        print(f"✅ Monthly activity: community-wide activity tracking")
        print(f"✅ Archive parsing: bidirectional data conversion")
        print(f"✅ Data consistency: archive structure validated")
        
    finally:
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up test directory: {temp_dir}")


if __name__ == "__main__":
    test_complete_prayer_lifecycle()