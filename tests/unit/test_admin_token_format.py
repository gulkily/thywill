"""
Unit tests for admin token format standardization.

Tests that admin tokens use the same 16-character hexadecimal format
as regular invite links for consistency.
"""

import pytest
import re
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from sqlmodel import Session

from models import engine, InviteToken


@pytest.mark.unit
class TestAdminTokenFormat:
    """Test admin token format consistency"""
    
    def test_admin_token_format_consistency(self):
        """Test that admin tokens use 16-character hex format like regular invites"""
        # Import the create_admin_token function
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from create_admin_token import create_admin_token
        
        with patch('create_admin_token.Session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance
            
            # Create token
            token = create_admin_token(hours=1)
            
            # Verify token format: 16 characters, hexadecimal
            assert len(token) == 16
            assert re.match(r'^[0-9a-f]{16}$', token), f"Token {token} is not 16-char hex format"
            
            # Verify database record creation
            mock_session_instance.add.assert_called_once()
            mock_session_instance.commit.assert_called_once()
            
            # Verify the token object has correct properties
            call_args = mock_session_instance.add.call_args[0][0]
            assert isinstance(call_args, InviteToken)
            assert call_args.token == token
            assert call_args.created_by_user == "system"
            assert call_args.used == False
    
    def test_regular_invite_token_format_for_comparison(self):
        """Test regular invite token format to ensure consistency"""
        import secrets
        
        # Generate regular invite token using same method
        regular_token = secrets.token_hex(8)
        
        # Should be same format as admin tokens
        assert len(regular_token) == 16
        assert re.match(r'^[0-9a-f]{16}$', regular_token)
    
    def test_admin_token_uniqueness(self):
        """Test that multiple admin tokens are unique"""
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from create_admin_token import create_admin_token
        
        tokens = []
        
        with patch('create_admin_token.Session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance
            
            # Generate multiple tokens
            for _ in range(10):
                token = create_admin_token(hours=1)
                tokens.append(token)
                
                # Each should be valid format
                assert len(token) == 16
                assert re.match(r'^[0-9a-f]{16}$', token)
            
            # All should be unique
            assert len(set(tokens)) == len(tokens), "Generated tokens are not unique"
    
    def test_admin_token_expiration_setting(self):
        """Test that admin token expiration is properly set"""
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from create_admin_token import create_admin_token
        
        test_hours = 24
        
        with patch('create_admin_token.Session') as mock_session, \
             patch('create_admin_token.datetime') as mock_datetime:
            
            # Mock current time
            mock_now = datetime(2025, 6, 25, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            mock_datetime.timedelta = timedelta  # Use real timedelta
            
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance
            
            # Create token
            token = create_admin_token(hours=test_hours)
            
            # Verify expiration time
            call_args = mock_session_instance.add.call_args[0][0]
            expected_expiration = mock_now + timedelta(hours=test_hours)
            assert call_args.expires_at == expected_expiration
    
    def test_token_format_not_uuid(self):
        """Test that tokens are no longer UUID format (old format)"""
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from create_admin_token import create_admin_token
        
        with patch('create_admin_token.Session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance
            
            token = create_admin_token(hours=1)
            
            # Should NOT be UUID format (36 characters with dashes)
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            assert not re.match(uuid_pattern, token), \
                f"Token {token} is still using old UUID format"
    
    def test_token_database_properties(self):
        """Test that token is saved with correct database properties"""
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from create_admin_token import create_admin_token
        
        with patch('create_admin_token.Session') as mock_session:
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance
            
            create_admin_token(hours=12)
            
            # Verify InviteToken properties
            call_args = mock_session_instance.add.call_args[0][0]
            assert isinstance(call_args, InviteToken)
            assert call_args.created_by_user == "system"
            assert call_args.used == False
            assert call_args.expires_at is not None
            assert len(call_args.token) == 16