"""
Tests for statistics dashboard UI
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_admin_statistics_page_requires_admin(client):
    """Test that statistics page requires admin access"""
    response = client.get("/admin/statistics")
    assert response.status_code in [401, 403]


@pytest.mark.integration
def test_admin_statistics_page_loads(client, mock_admin_user):
    """Test that statistics page loads for admin users"""
    response = client.get("/admin/statistics")
    assert response.status_code == 200
    assert "Statistics Dashboard" in response.text
    assert "Total Prayers" in response.text
    assert "Active Prayers" in response.text
    assert "Praise Reports" in response.text
    assert "Total Users" in response.text


@pytest.mark.integration
def test_admin_page_has_statistics_link(client, mock_admin_user):
    """Test that main admin page has link to statistics dashboard"""
    response = client.get("/admin")
    assert response.status_code == 200
    assert "/admin/statistics" in response.text
    assert "Statistics" in response.text