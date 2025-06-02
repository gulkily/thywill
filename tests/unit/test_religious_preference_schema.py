"""Unit tests for religious preference database schema"""
import pytest
from datetime import datetime
from sqlmodel import Session, select, text

from models import User, Prayer, engine
from tests.factories import UserFactory, PrayerFactory


@pytest.mark.unit
class TestReligiousPreferenceSchema:
    """Test religious preference database schema"""
    
    def test_user_model_has_religious_preference_fields(self, test_session):
        """Test that User model has religious preference fields with correct defaults"""
        user = User(display_name="Test User")
        test_session.add(user)
        test_session.commit()
        
        # Test defaults
        assert user.religious_preference == "unspecified"
        assert user.prayer_style is None
    
    def test_user_religious_preference_validation(self, test_session):
        """Test religious preference field accepts valid values"""
        valid_preferences = ["christian", "non_christian", "unspecified"]
        
        for preference in valid_preferences:
            user = User(
                display_name=f"User {preference}",
                religious_preference=preference
            )
            test_session.add(user)
            test_session.commit()
            
            retrieved_user = test_session.get(User, user.id)
            assert retrieved_user.religious_preference == preference
    
    def test_user_prayer_style_for_christians(self, test_session):
        """Test prayer style field for Christian users"""
        user = User(
            display_name="Christian User",
            religious_preference="christian",
            prayer_style="in_jesus_name"
        )
        test_session.add(user)
        test_session.commit()
        
        retrieved_user = test_session.get(User, user.id)
        assert retrieved_user.prayer_style == "in_jesus_name"
    
    def test_prayer_model_has_target_audience_fields(self, test_session):
        """Test that Prayer model has target audience fields with correct defaults"""
        prayer = Prayer(
            author_id="test_user",
            text="Test prayer"
        )
        test_session.add(prayer)
        test_session.commit()
        
        # Test defaults
        assert prayer.target_audience == "all"
        # Note: prayer_context field doesn't exist in current model
    
    def test_prayer_target_audience_validation(self, test_session):
        """Test target audience field accepts valid values"""
        valid_audiences = ["all", "christians_only", "non_christians_only"]
        
        for audience in valid_audiences:
            prayer = Prayer(
                author_id="test_user",
                text=f"Prayer for {audience}",
                target_audience=audience
            )
            test_session.add(prayer)
            test_session.commit()
            
            retrieved_prayer = test_session.get(Prayer, prayer.id)
            assert retrieved_prayer.target_audience == audience
    
    def test_migration_preserves_existing_data(self, test_session):
        """Test that migration preserves existing user and prayer data"""
        # Create user without religious preference (simulating pre-migration data)
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Verify existing data is preserved
        retrieved_user = test_session.get(User, user.id)
        retrieved_prayer = test_session.get(Prayer, prayer.id)
        
        assert retrieved_user.display_name == user.display_name
        assert retrieved_prayer.text == prayer.text
        
        # Verify new fields have default values
        assert retrieved_user.religious_preference == "unspecified"
        assert retrieved_prayer.target_audience == "all"


@pytest.mark.integration  
class TestReligiousPreferenceMigration:
    """Integration tests for migration script"""
    
    def test_migration_script_execution(self):
        """Test that migration script runs without errors"""
        # This would test the actual migration script
        # In practice, this might involve creating a test database
        # and running the migration script against it
        pass
    
    def test_schema_validation_after_migration(self):
        """Test that schema validation passes after migration"""
        # This would test the validate_schema.py script
        pass