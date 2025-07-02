"""Unit tests for religious preference filtering logic"""
import pytest
from sqlmodel import Session

from models import User, Prayer, PrayerMark
from tests.factories import UserFactory, PrayerFactory
from app import get_filtered_prayers_for_user, find_compatible_prayer_partner


@pytest.mark.unit
class TestReligiousPreferenceFiltering:
    """Test religious preference-based prayer filtering"""
    
    def test_christian_user_sees_all_and_christian_only_prayers(self, test_session):
        """Christian users should see 'all' and 'christians_only' prayers"""
        christian_user = UserFactory.create(religious_preference="christian")
        
        all_prayer = PrayerFactory.create(target_audience="all")
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        
        test_session.add_all([christian_user, all_prayer, christian_prayer])
        test_session.commit()
        
        filtered_prayers = get_filtered_prayers_for_user(christian_user, test_session)
        prayer_ids = [p.id for p in filtered_prayers]
        
        assert all_prayer.id in prayer_ids
        assert christian_prayer.id in prayer_ids
    
    def test_unspecified_user_sees_only_all_prayers_when_christian_prayers_exist(self, test_session):
        """Users with unspecified (all faiths) preference should see only 'all' prayers even when Christian-only prayers exist"""
        unspecified_user = UserFactory.create(religious_preference="unspecified")
        
        all_prayer = PrayerFactory.create(target_audience="all")
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        
        test_session.add_all([unspecified_user, all_prayer, christian_prayer])
        test_session.commit()
        
        filtered_prayers = get_filtered_prayers_for_user(unspecified_user, test_session)
        prayer_ids = [p.id for p in filtered_prayers]
        
        assert all_prayer.id in prayer_ids
        assert christian_prayer.id not in prayer_ids
    
    def test_unspecified_user_sees_only_all_prayers(self, test_session):
        """Users with unspecified preference should see only 'all' prayers"""
        unspecified_user = UserFactory.create(religious_preference="unspecified")
        
        all_prayer = PrayerFactory.create(target_audience="all")
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        
        test_session.add_all([unspecified_user, all_prayer, christian_prayer])
        test_session.commit()
        
        filtered_prayers = get_filtered_prayers_for_user(unspecified_user, test_session)
        prayer_ids = [p.id for p in filtered_prayers]
        
        assert all_prayer.id in prayer_ids
        assert christian_prayer.id not in prayer_ids
    
    def test_find_compatible_christian_prayer_partner(self, test_session):
        """Christian-only prayers should be assigned to Christian users"""
        christian_user = UserFactory.create(religious_preference="christian")
        unspecified_user = UserFactory.create(religious_preference="unspecified")
        
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        
        test_session.add_all([christian_user, unspecified_user, christian_prayer])
        test_session.commit()
        
        compatible_user = find_compatible_prayer_partner(christian_prayer, test_session)
        
        assert compatible_user is not None
        assert compatible_user.religious_preference == "christian"
        assert compatible_user.display_name == christian_user.display_name
    
    def test_all_prayer_assigned_to_any_user(self, test_session):
        """'All' audience prayers can be assigned to any user regardless of preference"""
        christian_user = UserFactory.create(religious_preference="christian")
        unspecified_user = UserFactory.create(religious_preference="unspecified")
        
        all_prayer = PrayerFactory.create(target_audience="all")
        
        test_session.add_all([christian_user, unspecified_user, all_prayer])
        test_session.commit()
        
        compatible_user = find_compatible_prayer_partner(all_prayer, test_session)
        
        assert compatible_user is not None
        assert compatible_user.display_name in [christian_user.display_name, unspecified_user.display_name]
    
    def test_all_audience_prayer_matches_any_user_type(self, test_session):
        """'All' audience prayers can be assigned to any user type"""
        christian_user = UserFactory.create(religious_preference="christian")
        unspecified_user = UserFactory.create(religious_preference="unspecified")
        
        all_prayer = PrayerFactory.create(target_audience="all")
        
        test_session.add_all([christian_user, unspecified_user, all_prayer])
        test_session.commit()
        
        compatible_user = find_compatible_prayer_partner(all_prayer, test_session)
        
        assert compatible_user is not None
        assert compatible_user.display_name in [christian_user.display_name, unspecified_user.display_name]
    
    def test_excludes_users_who_already_have_prayer(self, test_session):
        """Prayer partner matching should exclude users who already have the prayer"""
        christian_user1 = UserFactory.create(religious_preference="christian")
        christian_user2 = UserFactory.create(religious_preference="christian")
        
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        
        # User1 already has this prayer
        existing_mark = PrayerMark(username=christian_user1.display_name, prayer_id=christian_prayer.id)
        
        test_session.add_all([christian_user1, christian_user2, christian_prayer, existing_mark])
        test_session.commit()
        
        compatible_user = find_compatible_prayer_partner(christian_prayer, test_session)
        
        assert compatible_user is not None
        assert compatible_user.display_name == christian_user2.display_name
    
    def test_filtering_respects_archived_prayers(self, test_session):
        """Religious filtering should still respect archived prayer exclusion"""
        christian_user = UserFactory.create(religious_preference="christian")
        
        active_prayer = PrayerFactory.create(target_audience="christians_only")
        archived_prayer = PrayerFactory.create(target_audience="christians_only")
        
        test_session.add_all([christian_user, active_prayer, archived_prayer])
        test_session.commit()
        
        # Archive one prayer
        archived_prayer.set_attribute('archived', 'true', christian_user.display_name, test_session)
        test_session.commit()
        
        # Should only see active prayer, not archived
        filtered_prayers = get_filtered_prayers_for_user(christian_user, test_session, include_archived=False)
        prayer_ids = [p.id for p in filtered_prayers]
        
        assert active_prayer.id in prayer_ids
        assert archived_prayer.id not in prayer_ids
        
        # When including archived, should see both
        filtered_prayers_with_archived = get_filtered_prayers_for_user(christian_user, test_session, include_archived=True)
        prayer_ids_with_archived = [p.id for p in filtered_prayers_with_archived]
        
        assert active_prayer.id in prayer_ids_with_archived
        assert archived_prayer.id in prayer_ids_with_archived
    
    def test_filtering_respects_answered_prayers(self, test_session):
        """Religious filtering should still respect answered prayer exclusion"""
        christian_user = UserFactory.create(religious_preference="christian")
        
        active_prayer = PrayerFactory.create(target_audience="christians_only")
        answered_prayer = PrayerFactory.create(target_audience="christians_only")
        
        test_session.add_all([christian_user, active_prayer, answered_prayer])
        test_session.commit()
        
        # Mark one prayer as answered
        answered_prayer.set_attribute('answered', 'true', christian_user.display_name, test_session)
        test_session.commit()
        
        # Should only see active prayer, not answered
        filtered_prayers = get_filtered_prayers_for_user(christian_user, test_session, include_answered=False)
        prayer_ids = [p.id for p in filtered_prayers]
        
        assert active_prayer.id in prayer_ids
        assert answered_prayer.id not in prayer_ids
        
        # When including answered, should see both
        filtered_prayers_with_answered = get_filtered_prayers_for_user(christian_user, test_session, include_answered=True)
        prayer_ids_with_answered = [p.id for p in filtered_prayers_with_answered]
        
        assert active_prayer.id in prayer_ids_with_answered
        assert answered_prayer.id in prayer_ids_with_answered