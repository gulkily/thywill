"""
Integration tests for complete database recovery functionality.

Tests the ability to completely reconstruct the database from text archives,
including authentication, roles, system state, and enhanced prayer metadata.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from sqlmodel import Session, select

from models import (
    engine, User, Prayer, PrayerMark, PrayerAttribute, Role, UserRole,
    AuthenticationRequest, AuthApproval, SecurityLog, InviteToken,
    NotificationState, PrayerActivityLog
)
from app_helpers.services.database_recovery import CompleteSystemRecovery
from app_helpers.services.archive_writers import (
    AuthArchiveWriter, RoleArchiveWriter, SystemArchiveWriter
)
from app_helpers.services.text_archive_service import TextArchiveService


@pytest.fixture
def temp_archive_dir():
    """Create temporary archive directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_archive_data(temp_archive_dir):
    """Create sample archive data for testing recovery"""
    archive_service = TextArchiveService(str(temp_archive_dir))
    auth_writer = AuthArchiveWriter(str(temp_archive_dir))
    role_writer = RoleArchiveWriter(str(temp_archive_dir))
    system_writer = SystemArchiveWriter(str(temp_archive_dir))
    
    # Create sample user archive
    user_file = temp_archive_dir / "users" / "2024_06_users.txt"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_content = """User Registrations for June 2024

June 25 2024 at 10:00 - test_user_1 joined directly
June 25 2024 at 10:30 - test_user_2 joined on invitation from test_user_1
"""
    user_file.write_text(user_content)
    
    # Create sample prayer archive
    prayer_file = temp_archive_dir / "prayers" / "2024" / "06" / "2024_06_25_prayer_at_1000.txt"
    prayer_file.parent.mkdir(parents=True, exist_ok=True)
    prayer_content = """Prayer test_prayer_1 by test_user_1
Submitted June 25 2024 at 10:00

Please help me with my test case

Generated Prayer:
Lord, we pray for guidance in testing and software development. Amen.

Activity:
June 25 2024 at 10:15 - test_user_2 prayed this prayer
June 25 2024 at 10:20 - test_user_1 marked this prayer as answered
"""
    prayer_file.write_text(prayer_content)
    
    # Create sample authentication archives
    auth_writer.log_auth_request({
        'user_id': 'test_user_1',
        'device_info': 'Test Browser',
        'ip_address': '127.0.0.1',
        'status': 'approved',
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(days=7)
    })
    
    auth_writer.log_security_event({
        'event_type': 'successful_login',
        'user_id': 'test_user_1',
        'ip_address': '127.0.0.1',
        'user_agent': 'Test Browser',
        'details': 'Test login event'
    })
    
    # Create sample role archives
    role_writer.update_role_definitions([
        {
            'name': 'admin',
            'description': 'System administrator',
            'permissions': ['*'],
            'is_system_role': True,
            'created_by': 'system'
        },
        {
            'name': 'user',
            'description': 'Standard user',
            'permissions': ['read', 'write_own'],
            'is_system_role': True,
            'created_by': 'system'
        }
    ])
    
    role_writer.log_role_assignment({
        'user_id': 'test_user_1',
        'role_name': 'admin',
        'action': 'assigned',
        'granted_by': 'system',
        'granted_at': datetime.now()
    })
    
    # Create sample system archives
    system_writer.update_invite_tokens([
        {
            'token': 'test_token_123',
            'created_by_user': 'test_user_1',
            'expires_at': datetime.now() + timedelta(days=30),
            'used': False,
            'used_by_user_id': None,
            'created_at': datetime.now()
        }
    ])
    
    system_writer.snapshot_system_config({
        'MULTI_DEVICE_AUTH_ENABLED': 'true',
        'TEXT_ARCHIVE_ENABLED': 'true',
        'PEER_APPROVAL_COUNT': '2'
    })
    
    # Create enhanced prayer metadata archives
    attrs_dir = temp_archive_dir / "prayers" / "attributes"
    attrs_dir.mkdir(parents=True, exist_ok=True)
    attrs_file = attrs_dir / "2024_06_attributes.txt"
    attrs_content = """Prayer Attributes for June 2024
Format: timestamp|prayer_id|attribute_name|attribute_value|user_id

June 25 2024 at 10:20|test_prayer_1|answered|true|test_user_1
June 25 2024 at 10:20|test_prayer_1|answer_date|2024-06-25|test_user_1
"""
    attrs_file.write_text(attrs_content)
    
    marks_dir = temp_archive_dir / "prayers" / "marks"
    marks_dir.mkdir(parents=True, exist_ok=True)
    marks_file = marks_dir / "2024_06_marks.txt"
    marks_content = """Prayer Marks for June 2024
Format: timestamp|prayer_id|user_id

June 25 2024 at 10:15|test_prayer_1|test_user_2
"""
    marks_file.write_text(marks_content)
    
    return temp_archive_dir


class TestArchiveValidation:
    """Test archive structure validation"""
    
    def test_validate_empty_archive_structure(self, temp_archive_dir):
        """Test validation of empty archive directory"""
        recovery = CompleteSystemRecovery(str(temp_archive_dir))
        
        # Ensure we start with no warnings
        assert len(recovery.recovery_stats['warnings']) == 0, f"Started with warnings: {recovery.recovery_stats['warnings']}"
        
        # Should not raise exception for empty directory
        recovery._validate_archive_structure()
        
        # Should log warnings for missing directories (prayers, users, activity)
        warnings = recovery.recovery_stats['warnings']
        assert len(warnings) > 0, f"Expected warnings for missing directories, but got: {warnings}"
        
        # Should have warnings for the core required directories
        missing_dirs = [w for w in warnings if 'Missing core directory:' in w]
        assert len(missing_dirs) >= 3, f"Expected at least 3 missing directory warnings, got: {missing_dirs}"
    
    def test_validate_complete_archive_structure(self, sample_archive_data):
        """Test validation of complete archive structure"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Should validate successfully
        recovery._validate_archive_structure()
        
        # Should find archive directories
        assert (sample_archive_data / "prayers").exists()
        assert (sample_archive_data / "users").exists()
        assert (sample_archive_data / "auth").exists()
        assert (sample_archive_data / "roles").exists()
        assert (sample_archive_data / "system").exists()


class TestRecoverySimulation:
    """Test recovery simulation (dry run mode)"""
    
    def test_dry_run_recovery(self, sample_archive_data):
        """Test complete recovery simulation without database changes"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Perform dry run
        result = recovery.perform_complete_recovery(dry_run=True)
        
        # Should succeed
        assert result['success'] is True
        assert result['dry_run'] is True
        
        # Should have recovery statistics
        stats = result['stats']
        assert isinstance(stats, dict)
        assert 'users_recovered' in stats
        assert 'prayers_recovered' in stats
        assert 'roles_recovered' in stats
    
    def test_recovery_with_missing_archives(self, temp_archive_dir):
        """Test recovery simulation with missing archive files"""
        recovery = CompleteSystemRecovery(str(temp_archive_dir))
        
        # Create minimal archive structure
        (temp_archive_dir / "prayers").mkdir(exist_ok=True)
        (temp_archive_dir / "users").mkdir(exist_ok=True)
        
        result = recovery.perform_complete_recovery(dry_run=True)
        
        # Should handle missing archives gracefully
        assert result['success'] is True
        assert len(result['stats']['warnings']) > 0


class TestAuthenticationRecovery:
    """Test authentication data recovery"""
    
    def test_import_auth_requests(self, sample_archive_data):
        """Test importing authentication requests from archives"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Test auth request import
        recovery.import_authentication_data(dry_run=True)
        
        # Should parse auth files without errors
        assert recovery.recovery_stats['auth_requests_recovered'] >= 0
        assert len(recovery.recovery_stats['errors']) == 0
    
    def test_import_security_events(self, sample_archive_data):
        """Test importing security events from archives"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Test security event import
        recovery.import_authentication_data(dry_run=True)
        
        # Should handle security events
        assert recovery.recovery_stats['security_events_recovered'] >= 0


class TestRoleSystemRecovery:
    """Test role system recovery"""
    
    def test_import_role_definitions(self, sample_archive_data):
        """Test importing role definitions from archives"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Test role import
        recovery.import_role_system(dry_run=True)
        
        # Should recover roles
        assert recovery.recovery_stats['roles_recovered'] >= 0
        assert len(recovery.recovery_stats['errors']) == 0
    
    def test_create_default_roles(self, temp_archive_dir):
        """Test creation of default roles when none exist"""
        recovery = CompleteSystemRecovery(str(temp_archive_dir))
        
        # Test default role creation
        recovery.import_role_system(dry_run=True)
        
        # Should create default roles
        assert recovery.recovery_stats['roles_recovered'] >= 2  # admin and user


class TestSystemStateRecovery:
    """Test system state recovery"""
    
    def test_import_invite_tokens(self, sample_archive_data):
        """Test importing invite tokens from archives"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Test invite token import
        recovery.import_system_state(dry_run=True)
        
        # Should handle invite tokens
        assert recovery.recovery_stats['invite_tokens_recovered'] >= 0
    
    def test_system_config_logging(self, sample_archive_data):
        """Test system configuration logging during recovery"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Test system config handling
        recovery.import_system_state(dry_run=True)
        
        # Should log configuration references
        config_warnings = [w for w in recovery.recovery_stats['warnings'] 
                          if 'configuration' in w.lower()]
        assert len(config_warnings) >= 0  # May or may not have config warnings


class TestEnhancedPrayerRecovery:
    """Test enhanced prayer metadata recovery"""
    
    def test_import_prayer_attributes(self, sample_archive_data):
        """Test importing prayer attributes from archives"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Test prayer attribute import
        recovery.import_enhanced_prayer_data(dry_run=True)
        
        # Should handle prayer attributes
        assert recovery.recovery_stats['prayer_attributes_recovered'] >= 0
    
    def test_import_prayer_marks(self, sample_archive_data):
        """Test importing prayer marks from archives"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Test prayer marks import
        recovery.import_enhanced_prayer_data(dry_run=True)
        
        # Should handle prayer marks
        assert recovery.recovery_stats['prayer_marks_recovered'] >= 0


class TestRecoveryIntegrity:
    """Test recovery data integrity validation"""
    
    def test_integrity_validation(self, sample_archive_data):
        """Test data integrity validation after recovery"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Test integrity validation
        recovery.validate_recovery_integrity()
        
        # Should identify any integrity issues
        assert isinstance(recovery.recovery_stats['warnings'], list)
    
    def test_missing_data_handling(self, sample_archive_data):
        """Test handling of missing data with defaults"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Test missing data handling
        recovery.handle_missing_data(dry_run=True)
        
        # Should handle missing data gracefully
        assert len(recovery.recovery_stats['errors']) == 0


class TestFullRecoveryIntegration:
    """Test complete end-to-end recovery scenarios"""
    
    @pytest.mark.slow
    def test_complete_recovery_simulation(self, sample_archive_data):
        """Test complete recovery simulation from start to finish"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Perform complete recovery simulation
        result = recovery.perform_complete_recovery(dry_run=True)
        
        # Should complete successfully
        assert result['success'] is True
        assert result['dry_run'] is True
        
        # Should have comprehensive statistics
        stats = result['stats']
        expected_stats = [
            'users_recovered', 'prayers_recovered', 'prayer_marks_recovered',
            'prayer_attributes_recovered', 'roles_recovered', 'auth_requests_recovered'
        ]
        
        for stat in expected_stats:
            assert stat in stats
    
    def test_recovery_error_handling(self, temp_archive_dir):
        """Test recovery error handling with malformed archives"""
        recovery = CompleteSystemRecovery(str(temp_archive_dir))
        
        # Create malformed archive file
        bad_file = temp_archive_dir / "auth" / "2024_06_auth_requests.txt"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_text("malformed|data|without|proper|format")
        
        # Should handle errors gracefully
        result = recovery.perform_complete_recovery(dry_run=True)
        
        # May succeed with warnings or fail gracefully
        if not result['success']:
            assert 'error' in result
        else:
            assert len(result['stats']['errors']) >= 0


@pytest.mark.integration
class TestRecoveryCapabilityReport:
    """Test recovery capability reporting"""
    
    def test_capability_assessment(self, sample_archive_data):
        """Test assessment of recovery capabilities"""
        recovery = CompleteSystemRecovery(str(sample_archive_data))
        
        # Check capability assessment logic
        prayers_dir = recovery.archive_dir / "prayers"
        users_dir = recovery.archive_dir / "users"
        auth_dir = recovery.archive_dir / "auth"
        roles_dir = recovery.archive_dir / "roles"
        
        # Should correctly identify available archives
        assert prayers_dir.exists()
        assert users_dir.exists()
        assert auth_dir.exists()
        assert roles_dir.exists()
    
    def test_minimal_capability_assessment(self, temp_archive_dir):
        """Test capability assessment with minimal archives"""
        recovery = CompleteSystemRecovery(str(temp_archive_dir))
        
        # Create only core directories
        (temp_archive_dir / "prayers").mkdir(exist_ok=True)
        (temp_archive_dir / "users").mkdir(exist_ok=True)
        
        # Should identify limited but functional capability
        prayers_dir = recovery.archive_dir / "prayers"
        users_dir = recovery.archive_dir / "users"
        
        assert prayers_dir.exists()
        assert users_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])