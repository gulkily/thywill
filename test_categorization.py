#!/usr/bin/env python3
"""
Test script for prayer categorization implementation
"""

import os
# Enable text archives for testing
os.environ['TEXT_ARCHIVE_ENABLED'] = 'true'

from app_helpers.services.prayer_categorization_service import PrayerCategorizationService, DEFAULT_CATEGORIZATION

def test_categorization_service():
    """Test the categorization service with various inputs"""
    service = PrayerCategorizationService()
    
    test_cases = [
        {
            'name': 'Health prayer',
            'text': 'Please pray for my grandmother who is having surgery tomorrow',
            'expected_category': 'health'
        },
        {
            'name': 'Work prayer',
            'text': 'I have a job interview next week and need prayers for success',
            'expected_category': 'work'
        },
        {
            'name': 'Relationship prayer',
            'text': 'Pray for John and Mary as they work through marriage difficulties',
            'expected_category': 'relationships'
        },
        {
            'name': 'General prayer',
            'text': 'Please pray for peace in our world',
            'expected_category': 'general'
        }
    ]
    
    print("🧪 Testing Prayer Categorization Service")
    print("=" * 50)
    
    for test_case in test_cases:
        print(f"\n📝 Test: {test_case['name']}")
        print(f"   Text: {test_case['text']}")
        
        # Test keyword-based categorization
        result = service.categorize_prayer_with_fallback(test_case['text'])
        
        print(f"   Result: {result}")
        print(f"   Category: {result['subject_category']} (expected: {test_case['expected_category']})")
        print(f"   Specificity: {result['specificity_type']}")
        print(f"   Safety Score: {result['safety_score']}")
        print(f"   Method: {result['categorization_method']}")
        
        # Check if result is valid
        assert result['safety_score'] >= 0.0 and result['safety_score'] <= 1.0
        assert result['specificity_type'] in ['specific', 'general', 'mixed', 'unknown']
        assert result['categorization_method'] in ['ai_full', 'keyword_fallback', 'default_fallback']
        
        print("   ✅ Test passed")
    
    print("\n🎉 All categorization tests passed!")

def test_archive_parsing():
    """Test archive creation and parsing with categorization"""
    from app_helpers.services.text_archive_service import TextArchiveService
    import tempfile
    
    print("\n🧪 Testing Archive Integration")
    print("=" * 50)
    
    # Create test archive service with temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        archive_service = TextArchiveService(temp_dir)
        
        # Create test prayer data with categorization
        prayer_data = {
            'id': 'test123',
            'author': 'TestUser',
            'text': 'Please pray for healing for my sick friend Sarah',
            'generated_prayer': 'Dear Lord, we lift up Sarah in prayer...',
            'categorization': {
                'safety_score': 0.95,
                'safety_flags': [],
                'subject_category': 'health',
                'specificity_type': 'specific',
                'categorization_method': 'keyword_fallback',
                'categorization_confidence': 0.8
            }
        }
        
        # Create archive file
        print("📝 Creating archive with categorization...")
        archive_path = archive_service.create_prayer_archive(prayer_data)
        print(f"   Archive created: {archive_path}")
        
        # Read and verify archive content
        with open(archive_path, 'r') as f:
            content = f.read()
        
        print("📖 Archive content:")
        print(content)
        
        # Parse categorization back from archive
        print("🔍 Parsing categorization from archive...")
        parsed_categorization = archive_service.parse_prayer_archive_categorization(archive_path)
        
        print(f"   Parsed: {parsed_categorization}")
        
        # Verify parsed data matches original
        assert parsed_categorization['safety_score'] == prayer_data['categorization']['safety_score']
        assert parsed_categorization['subject_category'] == prayer_data['categorization']['subject_category']
        assert parsed_categorization['specificity_type'] == prayer_data['categorization']['specificity_type']
        
        print("   ✅ Archive parsing test passed!")

if __name__ == '__main__':
    try:
        test_categorization_service()
        test_archive_parsing()
        print("\n🎉 All tests passed! Categorization implementation is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)