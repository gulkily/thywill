"""
Simple test for statistics API - no test data
"""

import pytest
from datetime import datetime, date, timedelta


@pytest.mark.integration
def test_get_prayer_statistics_empty_db(client, mock_admin_user):
    """Test prayer statistics API with empty database"""
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
    
    # Empty database should have zero prayers but may have mock admin user
    assert data["summary"]["total_prayers"] == 0
    assert data["summary"]["total_users"] >= 0  # May have mock admin user


@pytest.mark.integration
def test_get_summary_statistics_empty_db(client, mock_admin_user):
    """Test summary statistics API with empty database"""
    response = client.get("/api/statistics/summary")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data["total_prayers"], int)
    assert data["total_prayers"] == 0