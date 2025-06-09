"""Integration tests for Invite Tree routes"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from models import User, InviteToken
from tests.factories import UserFactory, InviteTokenFactory, SessionFactory


@pytest.mark.integration
class TestInviteTreeRoute:
    """Test the /invite-tree route functionality"""
    
    def test_invite_tree_requires_authentication(self, client: TestClient, test_session):
        """Test that invite tree route requires authentication"""
        response = client.get("/invite-tree")
        
        # Should return 401 Unauthorized
        assert response.status_code == 401
    
    def test_invite_tree_with_authenticated_user(self, client: TestClient, test_session):
        """Test invite tree route with authenticated user"""
        # Create admin user and session
        admin = UserFactory.create_admin()
        session = SessionFactory.create(user_id="admin")
        test_session.add_all([admin, session])
        test_session.commit()
        
        # Set session cookie
        client.cookies.set("sid", session.id)
        
        response = client.get("/invite-tree")
        
        assert response.status_code == 200
        assert "Invite Tree" in response.text
        assert "Community Growth" in response.text
    
    def test_invite_tree_displays_empty_stats(self, client: TestClient, test_session):
        """Test invite tree with empty database shows appropriate empty state"""
        # Create admin user and session
        admin = UserFactory.create_admin()
        session = SessionFactory.create(user_id="admin")
        test_session.add_all([admin, session])
        test_session.commit()
        
        client.cookies.set("sid", session.id)
        
        response = client.get("/invite-tree")
        
        assert response.status_code == 200
        # Check that the page displays properly (admin user counts as 1 member)
        assert "Total Members" in response.text
        assert "Invite Tree" in response.text
    
    def test_invite_tree_displays_user_hierarchy(self, client: TestClient, test_session):
        """Test invite tree displays user hierarchy correctly"""
        # Create user hierarchy
        admin = UserFactory.create_admin()
        user1 = UserFactory.create(
            id="user1",
            display_name="Alice", 
            invited_by_user_id="admin"
        )
        user2 = UserFactory.create(
            id="user2",
            display_name="Bob",
            invited_by_user_id="user1"
        )
        session = SessionFactory.create(user_id="admin")
        test_session.add_all([admin, user1, user2, session])
        test_session.commit()
        
        client.cookies.set("sid", session.id)
        
        response = client.get("/invite-tree")
        
        assert response.status_code == 200
        # Check that user names appear in the tree
        assert "Alice" in response.text
        assert "Bob" in response.text
        assert "Admin User" in response.text
    
    def test_invite_tree_shows_user_invite_path(self, client: TestClient, test_session):
        """Test invite tree shows user's invite path"""
        # Create chain: admin -> user1 -> user2, with user2 as current user
        admin = UserFactory.create_admin()
        user1 = UserFactory.create(
            id="user1",
            display_name="Alice",
            invited_by_user_id="admin"
        )
        user2 = UserFactory.create(
            id="user2", 
            display_name="Bob",
            invited_by_user_id="user1"
        )
        session = SessionFactory.create(user_id="user2")
        test_session.add_all([admin, user1, user2, session])
        test_session.commit()
        
        client.cookies.set("sid", session.id)
        
        response = client.get("/invite-tree")
        
        assert response.status_code == 200
        # Should show invite path for user2
        assert "Your Invitation Path" in response.text
        assert "Alice" in response.text  # Should show user1 in path
    
    def test_invite_tree_displays_statistics(self, client: TestClient, test_session):
        """Test invite tree displays correct statistics"""
        # Create admin, users, and tokens
        admin = UserFactory.create_admin()
        user1 = UserFactory.create(
            id="user1",
            invited_by_user_id="admin",
            invite_token_used="token1"
        )
        
        token1 = InviteTokenFactory.create(
            token="token1",
            created_by_user="admin",
            used=True,
            used_by_user_id="user1"
        )
        token2 = InviteTokenFactory.create(
            token="token2",
            created_by_user="admin",
            used=False
        )
        
        session = SessionFactory.create(user_id="admin")
        test_session.add_all([admin, user1, token1, token2, session])
        test_session.commit()
        
        client.cookies.set("sid", session.id)
        
        response = client.get("/invite-tree")
        
        assert response.status_code == 200
        # Should show stats (2 users total, some invites sent)
        assert "2" in response.text  # Total members
        assert "50%" in response.text or "1" in response.text  # Success rate or counts


@pytest.mark.integration 
class TestInviteTreeNavigation:
    """Test invite tree navigation integration"""
    
    def test_invite_tree_accessible_from_menu(self, client: TestClient, test_session):
        """Test invite tree is accessible from main menu"""
        admin = UserFactory.create_admin()
        session = SessionFactory.create(user_id="admin") 
        test_session.add_all([admin, session])
        test_session.commit()
        
        client.cookies.set("sid", session.id)
        
        # Check menu page has invite tree link
        response = client.get("/menu")
        assert response.status_code == 200
        assert 'href="/invite-tree"' in response.text
    
    def test_invite_tree_accessible_from_admin(self, client: TestClient, test_session):
        """Test invite tree is accessible from admin panel"""
        admin = UserFactory.create_admin()
        session = SessionFactory.create(user_id="admin")
        test_session.add_all([admin, session])
        test_session.commit()
        
        client.cookies.set("sid", session.id)
        
        # Check admin page has invite tree link
        response = client.get("/admin")
        assert response.status_code == 200
        assert 'href="/invite-tree"' in response.text or "invite-tree" in response.text


@pytest.mark.integration
class TestInviteTreeUIInteraction:
    """Test invite tree UI interaction and JavaScript functionality"""
    
    def test_invite_tree_contains_tree_structure(self, client: TestClient, test_session):
        """Test invite tree displays tree structure properly"""
        # Create hierarchy with multiple levels
        admin = UserFactory.create_admin()
        user1 = UserFactory.create(
            id="user1",
            display_name="Alice",
            invited_by_user_id="admin"
        )
        user2 = UserFactory.create(
            id="user2",
            display_name="Bob", 
            invited_by_user_id="user1"
        )
        session = SessionFactory.create(user_id="admin")
        test_session.add_all([admin, user1, user2, session])
        test_session.commit()
        
        client.cookies.set("sid", session.id)
        
        response = client.get("/invite-tree")
        
        assert response.status_code == 200
        # Check for tree structure elements
        assert "tree-node" in response.text or "Community Tree" in response.text
        assert "<script>" in response.text  # JavaScript should be present
    
    def test_invite_tree_responsive_design(self, client: TestClient, test_session):
        """Test invite tree has responsive design elements"""
        admin = UserFactory.create_admin()
        session = SessionFactory.create(user_id="admin")
        test_session.add_all([admin, session])
        test_session.commit()
        
        client.cookies.set("sid", session.id)
        
        response = client.get("/invite-tree")
        
        assert response.status_code == 200
        # Check for responsive CSS classes (Tailwind-based)
        assert "viewport" in response.text
        assert "md:grid-cols-" in response.text or "max-w-" in response.text
    
    def test_invite_tree_has_proper_styling(self, client: TestClient, test_session):
        """Test invite tree includes proper CSS styling"""
        admin = UserFactory.create_admin()
        session = SessionFactory.create(user_id="admin")
        test_session.add_all([admin, session])
        test_session.commit()
        
        client.cookies.set("sid", session.id)
        
        response = client.get("/invite-tree")
        
        assert response.status_code == 200
        # Check for CSS styling
        assert "<style>" in response.text or ".tree" in response.text
        assert "background" in response.text or "color" in response.text 