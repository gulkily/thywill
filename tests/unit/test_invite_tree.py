"""Unit tests for Invite Tree feature"""
import pytest
import uuid
from datetime import datetime, timedelta
from sqlmodel import Session, select
from unittest.mock import Mock, patch

from models import User, InviteToken, engine
from tests.factories import UserFactory, InviteTokenFactory
from app import (
    get_invite_tree, 
    get_user_descendants, 
    get_user_invite_path, 
    get_invite_stats,
    _build_user_tree_node,
    _collect_descendants,
    _calculate_max_depth
)


@pytest.mark.unit
class TestInviteTreeDataModel:
    """Test the data model enhancements for invite tree tracking"""
    
    def test_user_model_has_invite_tree_fields(self, test_session):
        """Test that User model has invite tree tracking fields"""
        user = UserFactory.create(
            invited_by_username="inviter_123",
            invite_token_used="token_123"
        )
        test_session.add(user)
        test_session.commit()
        
        assert user.invited_by_username == "inviter_123"
        assert user.invite_token_used == "token_123"
    
    def test_user_model_allows_null_invite_fields(self, test_session):
        """Test that invite fields can be null for existing users"""
        user = UserFactory.create(
            invited_by_username=None,
            invite_token_used=None
        )
        test_session.add(user)
        test_session.commit()
        
        assert user.invited_by_username is None
        assert user.invite_token_used is None
    
    def test_invite_token_model_has_used_by_field(self, test_session):
        """Test that InviteToken model has used_by_user_id field"""
        token = InviteTokenFactory.create(used_by_user_id="user_123")
        test_session.add(token)
        test_session.commit()
        
        assert token.used_by_user_id == "user_123"
    
    def test_invite_token_allows_null_used_by_field(self, test_session):
        """Test that used_by_user_id can be null for unused tokens"""
        token = InviteTokenFactory.create(used_by_user_id=None)
        test_session.add(token)
        test_session.commit()
        
        assert token.used_by_user_id is None


@pytest.mark.unit
class TestInviteTreeLogic:
    """Test the core invite tree logic functions"""
    
    def test_get_invite_stats_empty_database(self, test_session):
        """Test invite stats with empty database"""
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            stats = get_invite_stats()
        
        assert stats['total_users'] == 0
        assert stats['total_invites_sent'] == 0
        assert stats['used_invites'] == 0
        assert stats['unused_invites'] == 0
        assert stats['users_with_inviters'] == 0
        assert stats['max_depth'] == 0
        assert stats['top_inviters'] == []
        assert stats['recent_growth'] == 0
        assert stats['invite_success_rate'] == 0
    
    def test_get_invite_stats_with_data(self, test_session):
        """Test invite stats with sample data"""
        # Create admin user
        admin = UserFactory.create_admin()
        test_session.add(admin)
        
        # Create invited users
        user1 = UserFactory.create(
            display_name="User1",
            invited_by_username="admin",
            invite_token_used="token1"
        )
        user2 = UserFactory.create(
            display_name="User2",
            invited_by_username="User1",
            invite_token_used="token2"
        )
        test_session.add_all([user1, user2])
        
        # Create invite tokens
        token1 = InviteTokenFactory.create(
            token="token1",
            created_by_user="admin",
            used=True,
            used_by_user_id="User1"
        )
        token2 = InviteTokenFactory.create(
            token="token2",
            created_by_user="User1", 
            used=True,
            used_by_user_id="User2"
        )
        token3 = InviteTokenFactory.create(
            token="token3",
            created_by_user="User1",
            used=False
        )
        test_session.add_all([token1, token2, token3])
        test_session.commit()
        
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            stats = get_invite_stats()
        
        assert stats['total_users'] == 3  # admin + user1 + user2
        assert stats['total_invites_sent'] == 3
        assert stats['used_invites'] == 2
        assert stats['unused_invites'] == 1
        assert stats['users_with_inviters'] == 2  # user1 and user2
        assert stats['max_depth'] == 2  # admin -> user1 -> user2
        assert stats['invite_success_rate'] == 67  # 2/3 = 66.67% rounded to 67
        
        # Check top inviters
        assert len(stats['top_inviters']) == 2
        assert stats['top_inviters'][0]['display_name'] == "User1"
        assert stats['top_inviters'][0]['invite_count'] == 1
        assert stats['top_inviters'][1]['display_name'] == "admin"
        assert stats['top_inviters'][1]['invite_count'] == 1

    def test_get_invite_stats_with_multi_root_depth(self, test_session):
        """Depth calculation should include chains from every root node."""
        root_a = UserFactory.create(display_name="RootA", invited_by_username=None)
        root_b = UserFactory.create(display_name="RootB", invited_by_username=None)
        level_1 = UserFactory.create(display_name="Child1", invited_by_username="RootA")
        level_2 = UserFactory.create(display_name="Child2", invited_by_username="Child1")
        level_3 = UserFactory.create(display_name="Child3", invited_by_username="Child2")
        lateral_child = UserFactory.create(display_name="Sibling", invited_by_username="RootB")

        test_session.add_all([root_a, root_b, level_1, level_2, level_3, lateral_child])
        test_session.commit()

        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            stats = get_invite_stats()

        assert stats['max_depth'] == 3
    
    def test_get_user_descendants_empty(self, test_session):
        """Test getting descendants for user with no descendants"""
        admin = UserFactory.create_admin()
        test_session.add(admin)
        test_session.commit()
        
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            descendants = get_user_descendants("admin")
        assert descendants == []
    
    def test_get_user_descendants_with_children(self, test_session):
        """Test getting descendants for user with children"""
        # Create user hierarchy: admin -> user1 -> user2, admin -> user3
        admin = UserFactory.create_admin()
        user1 = UserFactory.create(
            display_name="User1", 
            invited_by_username="admin"
        )
        user2 = UserFactory.create(
            display_name="User2",
            invited_by_username="User1"
        )
        user3 = UserFactory.create(
            display_name="User3",
            invited_by_username="admin"
        )
        test_session.add_all([admin, user1, user2, user3])
        test_session.commit()
        
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            descendants = get_user_descendants("admin")
        
        assert len(descendants) == 3  # user1, user2, user3
        descendant_ids = [d['user']['display_name'] for d in descendants]
        assert "User1" in descendant_ids
        assert "User2" in descendant_ids  
        assert "User3" in descendant_ids
    
    def test_get_user_invite_path_admin(self, test_session):
        """Test getting invite path for admin user"""
        admin = UserFactory.create_admin()
        test_session.add(admin)
        test_session.commit()
        
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            path = get_user_invite_path("admin")
        
        assert len(path) == 1
        assert path[0]['user']['display_name'] == "admin"
        assert path[0]['user']['is_admin'] is True
        assert path[0]['invited_by_username'] is None
    
    def test_get_user_invite_path_nested(self, test_session):
        """Test getting invite path for nested user"""
        # Create chain: admin -> user1 -> user2
        admin = UserFactory.create_admin()
        user1 = UserFactory.create(
            display_name="User1",
            invited_by_username="admin",
            invite_token_used="token1"
        )
        user2 = UserFactory.create(
            display_name="User2", 
            invited_by_username="User1",
            invite_token_used="token2"
        )
        test_session.add_all([admin, user1, user2])
        
        # Add tokens for path tracing
        token1 = InviteTokenFactory.create(token="token1")
        token2 = InviteTokenFactory.create(token="token2")
        test_session.add_all([token1, token2])
        test_session.commit()
        
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            path = get_user_invite_path("User2")
        
        assert len(path) == 3
        assert path[0]['user']['display_name'] == "admin"
        assert path[1]['user']['display_name'] == "User1"
        assert path[2]['user']['display_name'] == "User2"
    
    def test_get_invite_tree_empty(self, test_session):
        """Test getting invite tree with no admin user"""
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            result = get_invite_tree()
        
        assert result['tree'] is None
        assert result['stats']['total_users'] == 0
    
    def test_get_invite_tree_with_admin_only(self, test_session):
        """Test getting invite tree with admin only"""
        admin = UserFactory.create_admin()
        test_session.add(admin)
        test_session.commit()
        
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            result = get_invite_tree()
        
        assert result['tree'] is not None
        assert result['tree']['user']['display_name'] == "admin"
        assert result['tree']['children'] == []
        assert result['tree']['total_descendants'] == 0
    
    def test_get_invite_tree_with_hierarchy(self, test_session):
        """Test getting complete invite tree with hierarchy"""
        # Create hierarchy: admin -> user1 (2 children) -> user2, user3
        admin = UserFactory.create_admin()
        user1 = UserFactory.create(
            display_name="User1",
            invited_by_username="admin"
        )
        user2 = UserFactory.create(
            display_name="User2",
            invited_by_username="User1"
        )
        user3 = UserFactory.create(
            display_name="User3",
            invited_by_username="User1"
        )
        test_session.add_all([admin, user1, user2, user3])
        test_session.commit()
        
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            result = get_invite_tree()
        
        tree = result['tree']
        assert tree['user']['display_name'] == "admin"
        assert len(tree['children']) == 1
        assert tree['total_descendants'] == 3
        
        user1_node = tree['children'][0]
        assert user1_node['user']['display_name'] == "User1"
        assert len(user1_node['children']) == 2
        assert user1_node['total_descendants'] == 2
    
    def test_build_user_tree_node(self, test_session):
        """Test building individual tree node"""
        admin = UserFactory.create_admin()
        user1 = UserFactory.create(display_name="User1", invited_by_username="admin")
        test_session.add_all([admin, user1])
        
        # Add invite token
        token = InviteTokenFactory.create(created_by_user="admin")
        test_session.add(token)
        test_session.commit()
        
        node = _build_user_tree_node(admin, test_session, depth=0)
        
        assert node['user']['display_name'] == "admin"
        assert node['depth'] == 0
        assert node['invites_sent'] == 1
        assert node['successful_invites'] == 1
        assert node['total_descendants'] == 1
        assert len(node['children']) == 1
    
    def test_collect_descendants_prevents_infinite_loop(self, test_session):
        """Test that _collect_descendants prevents infinite loops"""
        # This tests the visited set functionality
        admin = UserFactory.create_admin()
        test_session.add(admin)
        test_session.commit()
        
        descendants = []
        visited = {"admin"}  # Pre-populate to simulate cycle
        _collect_descendants("admin", test_session, descendants, visited)
        
        assert descendants == []  # Should not add anything due to visited check
    
    def test_calculate_max_depth_no_admin(self, test_session):
        """Test max depth calculation with no admin user"""
        depth = _calculate_max_depth(test_session)
        assert depth == 0
    
    def test_calculate_max_depth_with_hierarchy(self, test_session):
        """Test max depth calculation with user hierarchy"""
        # Create chain of depth 3: admin -> user1 -> user2 -> user3
        admin = UserFactory.create_admin()
        user1 = UserFactory.create(display_name="User1", invited_by_username="admin")
        user2 = UserFactory.create(display_name="User2", invited_by_username="User1")
        user3 = UserFactory.create(display_name="User3", invited_by_username="User2")
        test_session.add_all([admin, user1, user2, user3])
        test_session.commit()
        
        depth = _calculate_max_depth(test_session)
        assert depth == 3


@pytest.mark.unit 
class TestInviteTreeEdgeCases:
    """Test edge cases and error handling for invite tree"""
    
    def test_get_user_descendants_nonexistent_user(self, test_session):
        """Test getting descendants for non-existent user"""
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            descendants = get_user_descendants("nonexistent")
        assert descendants == []
    
    def test_get_user_invite_path_nonexistent_user(self, test_session):
        """Test getting invite path for non-existent user"""
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            path = get_user_invite_path("nonexistent")
        assert path == []
    
    def test_invite_tree_with_orphaned_users(self, test_session):
        """Test invite tree with users whose inviters don't exist"""
        admin = UserFactory.create_admin()
        orphaned_user = UserFactory.create(
            display_name="Orphaned",
            invited_by_username="nonexistent_inviter"
        )
        test_session.add_all([admin, orphaned_user])
        test_session.commit()
        
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            result = get_invite_tree()
        
        # Should still work, orphaned user just won't appear in tree
        assert result['tree']['user']['display_name'] == "admin"
        assert len(result['tree']['children']) == 0
    
    def test_invite_tree_with_broken_token_references(self, test_session):
        """Test invite tree with users referencing non-existent tokens"""
        admin = UserFactory.create_admin()
        user = UserFactory.create(
            display_name="User1",
            invited_by_username="admin",
            invite_token_used="nonexistent_token"
        )
        test_session.add_all([admin, user])
        test_session.commit()
        
        # Mock Session to use test_session instead of real database
        with patch('app_helpers.services.invite_helpers.Session') as mock_session:
            mock_session.return_value.__enter__.return_value = test_session
            path = get_user_invite_path("User1")
        
        # Should still work, token_info will be None
        assert len(path) == 2
        assert path[1]['token_info'] is None


@pytest.mark.unit
class TestInviteTreeFactoryExtension:
    """Test factory extensions for invite tree testing"""
    
    def test_user_factory_with_invite_fields(self, test_session):
        """Test that UserFactory can create users with invite fields"""
        user = UserFactory.create(
            invited_by_username="inviter123",
            invite_token_used="token123"
        )
        
        assert hasattr(user, 'invited_by_username')
        assert hasattr(user, 'invite_token_used')
        assert user.invited_by_username == "inviter123"
        assert user.invite_token_used == "token123"
    
    def test_invite_token_factory_with_used_by_field(self, test_session):
        """Test that InviteTokenFactory can create tokens with used_by field"""
        token = InviteTokenFactory.create(used_by_user_id="user123")
        
        assert hasattr(token, 'used_by_user_id')
        assert token.used_by_user_id == "user123" 
