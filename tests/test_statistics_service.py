"""
Tests for statistics service
"""

import pytest
from datetime import datetime, date, timedelta
from sqlmodel import Session
from app_helpers.services.statistics_service import StatisticsService
from models import Prayer, User, PrayerMark, PrayerAttribute


@pytest.mark.unit
def test_statistics_service_initialization(test_session):
    """Test that StatisticsService initializes correctly"""
    service = StatisticsService(test_session)
    assert service.session == test_session


@pytest.mark.unit 
def test_get_total_prayers_empty(test_session):
    """Test getting total prayers count when database is empty"""
    service = StatisticsService(test_session)
    total = service.get_total_prayers()
    assert total == 0


@pytest.mark.unit
def test_get_total_prayers_with_data(test_session):
    """Test getting total prayers count with sample data"""
    service = StatisticsService(test_session)
    
    # Add test prayers
    prayer1 = Prayer(author_username="testuser1", text="Test prayer 1")
    prayer2 = Prayer(author_username="testuser2", text="Test prayer 2")
    
    test_session.add(prayer1)
    test_session.add(prayer2)
    test_session.commit()
    
    total = service.get_total_prayers()
    assert total == 2


@pytest.mark.unit
def test_get_active_prayers_count(test_session):
    """Test getting active prayers count (non-archived)"""
    service = StatisticsService(test_session)
    
    # Add test prayers
    prayer1 = Prayer(author_username="testuser1", text="Active prayer")
    prayer2 = Prayer(author_username="testuser2", text="Archived prayer")
    
    test_session.add(prayer1)
    test_session.add(prayer2)
    test_session.commit()
    
    # Archive one prayer
    archive_attr = PrayerAttribute(
        prayer_id=prayer2.id,
        attribute_name="archived",
        attribute_value="true"
    )
    test_session.add(archive_attr)
    test_session.commit()
    
    active_count = service.get_active_prayers_count()
    assert active_count == 1


@pytest.mark.unit
def test_get_answered_prayers_count(test_session):
    """Test getting answered prayers count"""
    service = StatisticsService(test_session)
    
    # Add test prayers
    prayer1 = Prayer(author_username="testuser1", text="Answered prayer")
    prayer2 = Prayer(author_username="testuser2", text="Regular prayer")
    
    test_session.add(prayer1)
    test_session.add(prayer2)
    test_session.commit()
    
    # Mark one prayer as answered
    answered_attr = PrayerAttribute(
        prayer_id=prayer1.id,
        attribute_name="answered",
        attribute_value="true"
    )
    test_session.add(answered_attr)
    test_session.commit()
    
    answered_count = service.get_answered_prayers_count()
    assert answered_count == 1


@pytest.mark.unit
def test_get_total_users(test_session):
    """Test getting total users count"""
    service = StatisticsService(test_session)
    
    # Add test users
    user1 = User(display_name="testuser1")
    user2 = User(display_name="testuser2")
    
    test_session.add(user1)
    test_session.add(user2)
    test_session.commit()
    
    total_users = service.get_total_users()
    assert total_users == 2


@pytest.mark.unit
def test_get_prayer_counts_by_period_invalid_period(test_session):
    """Test error handling for invalid period"""
    service = StatisticsService(test_session)
    
    with pytest.raises(ValueError, match="Unsupported period: invalid"):
        service.get_prayer_counts_by_period(
            "invalid", 
            date(2025, 1, 1), 
            date(2025, 1, 31)
        )


@pytest.mark.unit
def test_get_prayer_marks_counts_by_period(test_session):
    """Test getting prayer marks counts by time period"""
    service = StatisticsService(test_session)
    
    # Add test data
    user = User(display_name="testuser")
    prayer = Prayer(author_username="testuser", text="Test prayer")
    
    test_session.add(user)
    test_session.add(prayer)
    test_session.commit()
    
    # Add prayer marks with different dates (within test period)
    mark1 = PrayerMark(username="testuser", prayer_id=prayer.id, created_at=datetime(2025, 1, 15))
    mark2 = PrayerMark(username="testuser", prayer_id=prayer.id, created_at=datetime(2025, 1, 16))
    
    test_session.add(mark1)
    test_session.add(mark2)
    test_session.commit()
    
    # Test daily aggregation
    counts = service.get_prayer_marks_counts_by_period(
        "daily", 
        date(2025, 1, 1), 
        date(2025, 1, 31)
    )
    
    # Should have counts for the days we added marks
    assert len(counts) == 2
    assert counts.get("2025-01-15") == 1
    assert counts.get("2025-01-16") == 1


@pytest.mark.unit
def test_get_summary_statistics(test_session):
    """Test getting summary statistics"""
    service = StatisticsService(test_session)
    
    # Add sample data
    user = User(display_name="testuser")
    prayer = Prayer(author_username="testuser", text="Test prayer")
    
    test_session.add(user)
    test_session.add(prayer)
    test_session.commit()
    
    # Add prayer mark
    mark = PrayerMark(username="testuser", prayer_id=prayer.id)
    test_session.add(mark)
    test_session.commit()
    
    summary = service.get_summary_statistics()
    
    assert summary["total_prayers"] == 1
    assert summary["total_users"] == 1
    assert summary["total_prayer_marks"] == 1
    assert summary["active_prayers"] == 1
    assert summary["answered_prayers"] == 0