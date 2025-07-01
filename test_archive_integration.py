#!/usr/bin/env python3
"""
Test Archive Integration

Quick test to verify that the archive writers are properly integrated
and working with sample operations.
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import Session, create_engine, SQLModel
from models import User, AuthenticationRequest, InviteToken, Role, UserRole
from app_helpers.services.archive_writers import (
    AuthArchiveWriter, RoleArchiveWriter, SystemArchiveWriter,
    auth_archive_writer, role_archive_writer, system_archive_writer
)


def test_auth_archive_integration():
    """Test authentication archiving integration"""
    print("Testing authentication archiving...")
    
    # Create temporary directory for test archives
    temp_dir = tempfile.mkdtemp()
    temp_base = Path(temp_dir)
    
    try:
        # Initialize archive writer with temp directory
        auth_writer = AuthArchiveWriter(temp_dir)
        
        # Test auth request logging
        auth_request_data = {
            'id': 'test-auth-123',
            'user_id': 'testuser',
            'device_info': 'Test Browser/1.0',
            'ip_address': '127.0.0.1',
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=1),
            'verification_code': None
        }
        
        archive_file = auth_writer.log_auth_request(auth_request_data)
        assert os.path.exists(archive_file), f"Auth request archive file not created: {archive_file}"
        print(f"✓ Auth request archived to: {archive_file}")
        
        # Test approval logging
        approval_data = {
            'auth_request_id': 'test-auth-123',
            'approver_user_id': 'approver',
            'action': 'approved',
            'created_at': datetime.utcnow(),
            'details': 'Test approval'
        }
        
        archive_file = auth_writer.log_auth_approval(approval_data)
        assert os.path.exists(archive_file), f"Auth approval archive file not created: {archive_file}"
        print(f"✓ Auth approval archived to: {archive_file}")
        
        # Test security event logging
        security_event = {
            'event_type': 'session_created',
            'user_id': 'testuser',
            'ip_address': '127.0.0.1',
            'user_agent': 'Test Browser/1.0',
            'created_at': datetime.utcnow(),
            'details': 'Test session creation'
        }
        
        archive_file = auth_writer.log_security_event(security_event)
        assert os.path.exists(archive_file), f"Security event archive file not created: {archive_file}"
        print(f"✓ Security event archived to: {archive_file}")
        
        print("Authentication archiving tests passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_role_archive_integration():
    """Test role archiving integration"""
    print("Testing role archiving...")
    
    # Create temporary directory for test archives
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Initialize archive writer with temp directory
        role_writer = RoleArchiveWriter(temp_dir)
        
        # Test role assignment logging
        role_assignment = {
            'user_id': 'testuser',
            'role_name': 'admin',
            'action': 'assigned',
            'granted_by': 'system',
            'granted_at': datetime.utcnow(),
            'expires_at': None,
            'details': 'Test role assignment'
        }
        
        archive_file = role_writer.log_role_assignment(role_assignment)
        assert os.path.exists(archive_file), f"Role assignment archive file not created: {archive_file}"
        print(f"✓ Role assignment archived to: {archive_file}")
        
        # Test role change logging
        role_change = {
            'timestamp': datetime.utcnow(),
            'change_type': 'created',
            'role_name': 'admin',
            'changed_by': 'system',
            'old_value': '',
            'new_value': 'admin role created',
            'details': 'Test role creation'
        }
        
        archive_file = role_writer.log_role_change(role_change)
        assert os.path.exists(archive_file), f"Role change archive file not created: {archive_file}"
        print(f"✓ Role change archived to: {archive_file}")
        
        print("Role archiving tests passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_system_archive_integration():
    """Test system archiving integration"""
    print("Testing system archiving...")
    
    # Create temporary directory for test archives
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Initialize archive writer with temp directory
        system_writer = SystemArchiveWriter(temp_dir)
        
        # Test invite token usage logging
        archive_file = system_writer.log_invite_usage(
            token='test-token-123',
            used_by='testuser',
            created_by='inviter'
        )
        assert os.path.exists(archive_file), f"Invite usage archive file not created: {archive_file}"
        print(f"✓ Invite usage archived to: {archive_file}")
        
        # Test feature flag change logging
        archive_file = system_writer.log_feature_flag_change(
            flag='TEST_FEATURE',
            value=True,
            changed_by='admin'
        )
        assert os.path.exists(archive_file), f"Feature flag archive file not created: {archive_file}"
        print(f"✓ Feature flag change archived to: {archive_file}")
        
        # Test system config snapshot
        config = {
            'MULTI_DEVICE_AUTH_ENABLED': 'true',
            'PEER_APPROVAL_COUNT': '2',
            'REQUIRE_VERIFICATION_CODE': 'false',
            'SECRET_KEY': 'test-secret'  # Should be redacted
        }
        
        archive_file = system_writer.snapshot_system_config(config)
        assert os.path.exists(archive_file), f"System config archive file not created: {archive_file}"
        print(f"✓ System config archived to: {archive_file}")
        
        # Verify sensitive data is redacted
        with open(archive_file, 'r') as f:
            content = f.read()
            assert 'SECRET_KEY=[REDACTED]' in content, "Sensitive data not properly redacted"
            print("✓ Sensitive data properly redacted")
        
        print("System archiving tests passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_global_archive_writers():
    """Test that global archive writer instances are available"""
    print("Testing global archive writer instances...")
    
    # Check that global instances exist
    assert auth_archive_writer is not None, "Global auth_archive_writer not available"
    assert role_archive_writer is not None, "Global role_archive_writer not available"
    assert system_archive_writer is not None, "Global system_archive_writer not available"
    
    print("✓ Global archive writer instances are available")
    print("Global archive writer tests passed!")


def test_archive_file_structure():
    """Test that archive files are created with correct structure"""
    print("Testing archive file structure...")
    
    # Create temporary directory for test archives
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Test auth archive structure
        auth_writer = AuthArchiveWriter(temp_dir)
        auth_writer.log_security_event({
            'event_type': 'test_event',
            'user_id': 'testuser',
            'ip_address': '127.0.0.1',
            'user_agent': 'Test/1.0',
            'created_at': datetime.utcnow(),
            'details': 'test details'
        })
        
        # Check that auth directory exists
        auth_dir = Path(temp_dir) / "auth"
        assert auth_dir.exists(), "Auth directory not created"
        
        # Check that monthly files are created
        now = datetime.now()
        expected_file = auth_dir / f"{now.year}_{now.month:02d}_security_events.txt"
        assert expected_file.exists(), f"Monthly security events file not created: {expected_file}"
        
        # Check file contents
        with open(expected_file, 'r') as f:
            content = f.read()
            assert 'Security Events for' in content, "File header not found"
            assert 'testuser' in content, "Test data not found in file"
        
        print("✓ Archive file structure is correct")
        print("Archive file structure tests passed!")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def main():
    """Run all archive integration tests"""
    print("Starting archive integration tests...\n")
    
    try:
        test_auth_archive_integration()
        print()
        
        test_role_archive_integration()
        print()
        
        test_system_archive_integration()
        print()
        
        test_global_archive_writers()
        print()
        
        test_archive_file_structure()
        print()
        
        print("🎉 All archive integration tests passed!")
        print("\nThe archive writers are properly integrated and ready for migration!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)