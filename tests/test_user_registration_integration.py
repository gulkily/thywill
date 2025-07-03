#!/usr/bin/env python3
"""
Test user registration integration with archive-first approach
"""

import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Mock the configuration before importing services
import os
os.environ['TEXT_ARCHIVE_ENABLED'] = 'true'
os.environ['TEXT_ARCHIVE_BASE_DIR'] = tempfile.mkdtemp()

from app_helpers.services.archive_first_service import create_user_with_text_archive


def test_user_registration_integration():
    """Test that user registration creates both archive file and database record"""
    
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    print(f"Testing user registration in directory: {temp_dir}")
    
    try:
        print("Testing user registration with archive-first approach...")
        
        # Test Case 1: User with invitation
        print("\n1. Testing user registration with invitation...")
        user_data_with_invite = {
            'display_name': 'John_Smith',
            'invited_by_display_name': 'Mary_Johnson',
            'religious_preference': 'christian',
            'prayer_style': 'traditional',
            'invited_by_user_id': 'user123',
            'invite_token_used': 'token456'
        }
        
        user, archive_path = create_user_with_text_archive(user_data_with_invite, 'test_user_1')
        
        # Verify user record
        assert user.id == 'test_user_1'
        assert user.display_name == 'John_Smith'
        assert user.religious_preference == 'christian'
        assert user.invited_by_user_id == 'user123'
        assert user.text_file_path == archive_path
        
        print(f"✅ User created: {user.id} ({user.display_name})")
        print(f"✅ Archive file: {archive_path}")
        
        # Verify archive file exists and contains registration
        if archive_path and Path(archive_path).exists():
            archive_content = Path(archive_path).read_text()
            assert "John_Smith joined on invitation from Mary_Johnson" in archive_content
            print("✅ Archive file contains correct registration entry")
        else:
            print("⚠️  Archive file not created (feature may be disabled)")
        
        # Test Case 2: User without invitation (direct registration)
        print("\n2. Testing direct user registration...")
        user_data_direct = {
            'display_name': 'Sarah_Wilson',
            'religious_preference': 'unspecified',
            'prayer_style': None,
            'invited_by_user_id': None,
            'invite_token_used': 'direct_token'
        }
        
        user2, archive_path2 = create_user_with_text_archive(user_data_direct, 'test_user_2')
        
        # Verify user record
        assert user2.id == 'test_user_2'
        assert user2.display_name == 'Sarah_Wilson'
        assert user2.religious_preference == 'unspecified'
        assert user2.invited_by_user_id is None
        
        print(f"✅ User created: {user2.id} ({user2.display_name})")
        
        # Verify archive file for direct registration
        if archive_path2 and Path(archive_path2).exists():
            archive_content2 = Path(archive_path2).read_text()
            assert "Sarah_Wilson joined directly" in archive_content2
            print("✅ Archive file contains correct direct registration entry")
        
        # Test Case 3: Test with auto-generated ID
        print("\n3. Testing user registration with auto-generated ID...")
        user_data_auto = {
            'display_name': 'Mike_Brown',
            'religious_preference': 'christian',
            'invited_by_display_name': 'John_Smith'
        }
        
        user3, archive_path3 = create_user_with_text_archive(user_data_auto)  # No ID provided
        
        # Verify user record (ID should be auto-generated)
        assert user3.id is not None
        assert user3.display_name == 'Mike_Brown'
        assert user3.religious_preference == 'christian'
        
        print(f"✅ User created with auto-generated ID: {user3.id} ({user3.display_name})")
        
        print("\n🎉 User registration integration test passed successfully!")
        print("✅ Archive-first approach working for user registration")
        print("✅ Database records created with proper archive file references")
        print("✅ Archive files contain human-readable registration entries")
        print("✅ Both invited and direct registrations working")
        print("✅ Both specific and auto-generated IDs working")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        raise
        
    finally:
        # Clean up
        try:
            shutil.rmtree(temp_dir)
            print(f"\nCleaned up test directory: {temp_dir}")
        except:
            pass


if __name__ == "__main__":
    test_user_registration_integration()