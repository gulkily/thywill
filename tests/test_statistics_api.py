"""
Tests for statistics API endpoints
"""

import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from models import Prayer, User, PrayerMark, Role, UserRole


@pytest.mark.integration
def test_statistics_api_requires_admin(client):
    """Test that statistics API requires admin access"""
    response = client.get("/api/statistics/summary")
    assert response.status_code in [401, 403]


@pytest.mark.integration
def test_get_prayer_statistics_invalid_period(client, mock_admin_user, test_session):
    """Test prayer statistics API with invalid period"""
    response = client.get("/api/statistics/prayers?period=invalid")
    assert response.status_code == 422  # Validation error


@pytest.mark.integration
def test_get_prayer_statistics_invalid_date_format(client, mock_admin_user, test_session):
    """Test prayer statistics API with invalid date format"""
    response = client.get("/api/statistics/prayers?period=daily&start_date=invalid&end_date=2025-01-01")
    assert response.status_code == 400
    assert "Invalid date format" in response.json()["detail"]


@pytest.mark.integration
def test_get_prayer_statistics_invalid_date_range(client, mock_admin_user, test_session):
    """Test prayer statistics API with invalid date range"""
    response = client.get("/api/statistics/prayers?period=daily&start_date=2025-01-31&end_date=2025-01-01")
    assert response.status_code == 400
    assert "Start date must be before end date" in response.json()["detail"]


@pytest.mark.integration  
def test_get_prayer_statistics_valid_request(client, mock_admin_user, test_session):
    """Test prayer statistics API with valid request"""
    # Add test data
    user = User(display_name="testuser")
    prayer1 = Prayer(author_username="testuser", text="Test prayer 1")
    prayer2 = Prayer(author_username="testuser", text="Test prayer 2")
    
    test_session.add(user)
    test_session.add(prayer1)
    test_session.add(prayer2)
    test_session.commit()
    
    response = client.get("/api/statistics/prayers?period=daily&start_date=2025-01-01&end_date=2025-01-31")
    if response.status_code != 200:
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
    assert response.status_code == 200
    
    data = response.json()
    assert "period" in data
    assert "start_date" in data
    assert "end_date" in data
    assert "prayer_counts" in data
    assert "user_counts" in data
    assert "summary" in data
    
    assert data["period"] == "daily"
    assert data["start_date"] == "2025-01-01"
    assert data["end_date"] == "2025-01-31"


@pytest.mark.integration
def test_get_prayer_statistics_default_dates(client, mock_admin_user, test_session):
    """Test prayer statistics API with default date range"""
    response = client.get("/api/statistics/prayers?period=monthly")
    assert response.status_code == 200
    
    data = response.json()
    assert "start_date" in data
    assert "end_date" in data
    # Should have default 1-year range for monthly period
    start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
    end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
    assert (end_date - start_date).days >= 360  # Approximately 1 year


@pytest.mark.integration
def test_get_summary_statistics(client, mock_admin_user, test_session):
    """Test summary statistics API"""
    # Add test data
    user = User(display_name="testuser")
    prayer = Prayer(author_username="testuser", text="Test prayer")
    mark = PrayerMark(username="testuser", prayer_id="test-prayer-id")
    
    test_session.add(user)
    test_session.add(prayer)
    test_session.add(mark)
    test_session.commit()
    
    response = client.get("/api/statistics/summary")
    assert response.status_code == 200
    
    data = response.json()
    assert "total_prayers" in data
    assert "active_prayers" in data
    assert "answered_prayers" in data
    assert "total_users" in data
    assert "total_prayer_marks" in data
    
    # Check data types
    assert isinstance(data["total_prayers"], int)
    assert isinstance(data["active_prayers"], int)
    assert isinstance(data["answered_prayers"], int)
    assert isinstance(data["total_users"], int)
    assert isinstance(data["total_prayer_marks"], int)