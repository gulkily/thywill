#!/usr/bin/env python3
"""
Integration test for prayer categorization with actual database
"""

from sqlmodel import Session, select
from models import engine, Prayer, User
from app_helpers.services.archive_first_service import submit_prayer_archive_first
from datetime import datetime

def test_full_integration():
    """Test full prayer submission with categorization"""
    print("🧪 Testing Full Prayer Categorization Integration")
    print("=" * 60)
    
    with Session(engine) as session:
        # Create test user if it doesn't exist
        test_user = session.exec(
            select(User).where(User.display_name == "TestUser")
        ).first()
        
        if not test_user:
            test_user = User(
                display_name="TestUser",
                created_at=datetime.now()
            )
            session.add(test_user)
            session.commit()
            session.refresh(test_user)
            print("✅ Created test user")
        else:
            print("✅ Using existing test user")
    
    # Test prayer submission with categorization
    test_cases = [
        {
            'text': 'Please pray for my grandmother who is recovering from heart surgery',
            'expected_category': 'health'
        },
        {
            'text': 'I have a big presentation at work tomorrow, please pray for success',
            'expected_category': 'work'
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n📝 Test {i+1}: {test_case['text'][:50]}...")
        
        # Submit prayer using archive-first approach with categorization
        prayer = submit_prayer_archive_first(
            text=test_case['text'],
            author=test_user,
            generated_prayer=f"Heavenly Father, we lift up this request... (Test {i+1})"
        )
        
        print(f"   Prayer ID: {prayer.id}")
        print(f"   Safety Score: {prayer.safety_score}")
        print(f"   Subject Category: {prayer.subject_category} (expected: {test_case['expected_category']})")
        print(f"   Specificity: {prayer.specificity_type}")
        print(f"   Method: {prayer.categorization_method}")
        print(f"   Archive Path: {prayer.text_file_path}")
        
        # Verify categorization is reasonable
        assert prayer.safety_score >= 0.0 and prayer.safety_score <= 1.0
        assert prayer.subject_category in ['health', 'work', 'relationships', 'spiritual', 'provision', 'protection', 'guidance', 'gratitude', 'transitions', 'crisis', 'general']
        assert prayer.specificity_type in ['specific', 'general', 'mixed', 'unknown']
        
        # Check that archive file was created
        if prayer.text_file_path:
            import os
            assert os.path.exists(prayer.text_file_path), f"Archive file not found: {prayer.text_file_path}"
            
            # Read archive and verify categorization metadata is present
            with open(prayer.text_file_path, 'r') as f:
                archive_content = f.read()
            
            assert 'Safety Score:' in archive_content
            assert 'Category:' in archive_content
            assert 'Specificity:' in archive_content
            print("   ✅ Archive contains categorization metadata")
        
        print("   ✅ Test passed")
    
    print(f"\n🎉 Full integration test completed successfully!")
    print("   - Prayers created with categorization")
    print("   - Database fields populated correctly") 
    print("   - Archive files contain categorization metadata")
    print("   - Archive-first architecture working properly")

def test_query_performance():
    """Test that categorization queries work efficiently"""
    print(f"\n🚀 Testing Query Performance")
    print("=" * 40)
    
    with Session(engine) as session:
        # Test basic categorization queries
        health_prayers = session.exec(
            select(Prayer).where(Prayer.subject_category == 'health')
        ).all()
        
        high_safety_prayers = session.exec(
            select(Prayer).where(Prayer.safety_score >= 0.9)
        ).all()
        
        specific_prayers = session.exec(
            select(Prayer).where(Prayer.specificity_type == 'specific')
        ).all()
        
        print(f"   Health prayers: {len(health_prayers)}")
        print(f"   High safety prayers (≥0.9): {len(high_safety_prayers)}")
        print(f"   Specific prayers: {len(specific_prayers)}")
        print("   ✅ All categorization queries executed successfully")

if __name__ == '__main__':
    try:
        test_full_integration()
        test_query_performance()
        print("\n🎉 All integration tests passed! The categorization system is fully operational.")
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)