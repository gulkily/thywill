"""
Integration tests for admin invite authentication flow.

Tests the fixed behavior where admin invites authenticate existing users
instead of recreating accounts, and proper admin role assignment.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import app
from models import engine, User, InviteToken, Role, UserRole, Session as UserSession, SQLModel
from app_helpers.routes.auth.login_routes import grant_admin_role_for_system_token


@pytest.mark.integration
class TestAdminInviteAuthentication:
    """Test admin invite authentication flow changes"""
    
    def setup_method(self):
        """Set up test environment"""
        # Use the test engine directly
        # Ensure tables exist
        SQLModel.metadata.create_all(engine)
        
        # Clean up any existing test data
        with Session(engine) as session:
            for item in session.exec(select(UserSession)).all():
                session.delete(item)
            for item in session.exec(select(UserRole)).all():
                session.delete(item)
            for item in session.exec(select(Role)).all():
                session.delete(item)
            for item in session.exec(select(InviteToken)).all():
                session.delete(item)
            for item in session.exec(select(User)).all():
                session.delete(item)
            session.commit()
    
    def teardown_method(self):
        """Clean up test environment"""
        with Session(engine) as session:
            for item in session.exec(select(UserSession)).all():
                session.delete(item)
            for item in session.exec(select(UserRole)).all():
                session.delete(item)
            for item in session.exec(select(Role)).all():
                session.delete(item)
            for item in session.exec(select(InviteToken)).all():
                session.delete(item)
            for item in session.exec(select(User)).all():
                session.delete(item)
            session.commit()
    
    def test_admin_invite_authenticates_existing_user(self):
        """Test that admin invite authenticates existing user instead of recreating"""
        with Session(engine) as session:
            # Create existing user
            existing_user = User(
                display_name="Existing Admin"
            )
            session.add(existing_user)
            
            # Create admin invite token
            admin_token = InviteToken(
                token="admin123456789abc",
                created_by_user="system",
                expires_at=datetime.utcnow() + timedelta(hours=12),
                used=False
            )
            session.add(admin_token)
            session.commit()
            existing_user_id = existing_user.id
        
        # Test the function directly without web client
        from app_helpers.routes.auth.login_routes import grant_admin_role_for_system_token
        
        with Session(engine) as session:
            # Test the grant_admin_role_for_system_token function
            grant_admin_role_for_system_token(existing_user_id, "admin123456789abc", session)
            session.commit()
            
            # Verify user was not recreated (same ID)
            user = session.exec(select(User).where(User.display_name == "Existing Admin")).first()
            assert user is not None
            assert user.id == existing_user_id
            
            # Verify user count (should still be 1)
            user_count = len(session.exec(select(User)).all())
            assert user_count == 1
    
    def test_admin_role_assignment_for_system_token(self):
        """Test that admin role is properly assigned when using system tokens"""
        with Session(engine) as session:
            # Create user
            user = User(
                username="new_admin",
                display_name="New Admin",
                email="newadmin@example.com"
            )
            session.add(user)
            session.commit()
            user_id = user.id
        
        # Test the grant_admin_role_for_system_token function
        with Session(engine) as session:
            user = session.get(User, user_id)
            grant_admin_role_for_system_token(user, "admin123456789abc", session)
            session.commit()
        
        # Verify admin role was assigned
        with Session(engine) as session:
            user_roles = session.exec(
                select(UserRole).where(UserRole.user_id == user_id)
            ).all()
            
            assert len(user_roles) > 0
            
            # Check if admin role exists
            admin_role_assigned = False
            for user_role in user_roles:
                role = session.get(Role, user_role.role_id)
                if role and role.name == "admin":
                    admin_role_assigned = True
                    break
            
            assert admin_role_assigned, "Admin role was not assigned to user"
    
    def test_no_account_deletion_for_existing_users(self):
        """Test that existing accounts are not deleted when using admin invites"""
        with Session(engine) as session:
            # Create existing user with data
            existing_user = User(
                username="admin_with_data",
                display_name="Admin With Data",
                email="admin@example.com"
            )
            session.add(existing_user)
            session.commit()
            original_user_id = existing_user.id
            
            # Create admin token
            admin_token = InviteToken(
                token="admin987654321def",
                created_by_user="system",
                expires_at=datetime.utcnow() + timedelta(hours=12),
                used=False
            )
            session.add(admin_token)
            session.commit()
        
        # Use admin invite
        response = self.client.post("/login", data={
            "username": "admin_with_data",
            "invite_token": "admin987654321def"
        })
        
        # Should not delete and recreate account
        with Session(engine) as session:
            user = session.exec(select(User).where(User.username == "admin_with_data")).first()
            assert user is not None
            assert user.id == original_user_id  # Same ID = not recreated
            assert user.display_name == "Admin With Data"  # Data preserved
            assert user.email == "admin@example.com"  # Data preserved
    
    def test_admin_invite_creates_new_user_if_not_exists(self):
        """Test that admin invite creates new user if username doesn't exist"""
        with Session(engine) as session:
            # Create admin token
            admin_token = InviteToken(
                token="admin111222333444",
                created_by_user="system",
                expires_at=datetime.utcnow() + timedelta(hours=12),
                used=False
            )
            session.add(admin_token)
            session.commit()
        
        # Use admin invite with new username
        response = self.client.post("/login", data={
            "username": "brand_new_admin",
            "invite_token": "admin111222333444"
        })
        
        # Should create new user and authenticate
        assert response.status_code == 302
        
        # Verify new user was created
        with Session(engine) as session:
            user = session.exec(select(User).where(User.username == "brand_new_admin")).first()
            assert user is not None
            assert user.display_name == "brand_new_admin"  # Default display name
    
    def test_admin_token_marked_as_used(self):
        """Test that admin token is marked as used after authentication"""
        with Session(engine) as session:
            # Create admin token
            admin_token = InviteToken(
                token="admin555666777888",
                created_by_user="system",
                expires_at=datetime.utcnow() + timedelta(hours=12),
                used=False
            )
            session.add(admin_token)
            session.commit()
        
        # Use admin invite
        response = self.client.post("/login", data={
            "username": "test_admin",
            "invite_token": "admin555666777888"
        })
        
        # Verify token is marked as used
        with Session(engine) as session:
            token = session.exec(
                select(InviteToken).where(InviteToken.token == "admin555666777888")
            ).first()
            assert token is not None
            assert token.used == True
    
    def test_session_creation_for_admin_login(self):
        """Test that proper session is created during admin login"""
        with Session(engine) as session:
            # Create admin token
            admin_token = InviteToken(
                token="admin999888777666",
                created_by_user="system",
                expires_at=datetime.utcnow() + timedelta(hours=12),
                used=False
            )
            session.add(admin_token)
            session.commit()
        
        # Use admin invite
        response = self.client.post("/login", data={
            "username": "session_test_admin",
            "invite_token": "admin999888777666"
        })
        
        # Should have session cookie
        assert "session_id" in response.cookies
        
        # Verify session exists in database
        with Session(engine) as session:
            user = session.exec(select(User).where(User.username == "session_test_admin")).first()
            assert user is not None
            
            user_session = session.exec(
                select(UserSession).where(UserSession.user_id == user.id)
            ).first()
            assert user_session is not None
            assert user_session.is_fully_authenticated == True