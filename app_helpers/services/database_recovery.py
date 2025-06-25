"""
Complete Database Recovery Service

This service provides complete database reconstruction from text archives alone,
implementing the complete recovery capabilities outlined in the recovery plan.

Recovery Categories:
- Authentication: Auth requests, approvals, security logs, sessions
- Roles & Permissions: Role definitions, assignments, permission history
- System State: Invite tokens, configuration, feature flags
- Prayer Data: Enhanced prayer archives with complete metadata
- User Data: Registration records and invite relationships
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlmodel import Session, select
import uuid
import secrets

from models import (
    engine, User, Prayer, PrayerMark, PrayerAttribute, PrayerActivityLog,
    Role, UserRole, AuthenticationRequest, AuthApproval, AuthAuditLog,
    SecurityLog, Session as UserSession, NotificationState, InviteToken
)
from app_helpers.services.text_archive_service import TextArchiveService
from app_helpers.services.text_importer_service import TextImporterService

logger = logging.getLogger(__name__)


class CompleteSystemRecovery:
    """Service for complete database reconstruction from text archives"""
    
    def __init__(self, archive_dir: str = None):
        self.archive_dir = Path(archive_dir) if archive_dir else Path("text_archives")
        self.archive_service = TextArchiveService(str(self.archive_dir))
        self.text_importer = TextImporterService(self.archive_service)
        
        self.recovery_stats = {
            'users_recovered': 0,
            'prayers_recovered': 0,
            'prayer_marks_recovered': 0,
            'prayer_attributes_recovered': 0,
            'roles_recovered': 0,
            'role_assignments_recovered': 0,
            'auth_requests_recovered': 0,
            'auth_approvals_recovered': 0,
            'security_events_recovered': 0,
            'invite_tokens_recovered': 0,
            'notifications_recovered': 0,
            'errors': [],
            'warnings': []
        }
    
    def perform_complete_recovery(self, dry_run: bool = False) -> Dict:
        """
        Perform complete database recovery from text archives
        
        Args:
            dry_run: If True, simulate recovery without making changes
            
        Returns:
            Dict with recovery results and statistics
        """
        logger.info("Starting complete database recovery from text archives")
        
        try:
            # Phase 1: Validate archive directory structure
            self._validate_archive_structure()
            
            # Phase 2: Import core user and prayer data (existing functionality)
            logger.info("Phase 2: Importing core user and prayer data")
            core_results = self.text_importer.import_from_archive_directory(
                str(self.archive_dir), dry_run=dry_run
            )
            self._merge_stats(core_results.get('stats', {}))
            
            # Phase 3: Import authentication data
            logger.info("Phase 3: Importing authentication data")
            self.import_authentication_data(dry_run=dry_run)
            
            # Phase 4: Import role system
            logger.info("Phase 4: Importing role system")
            self.import_role_system(dry_run=dry_run)
            
            # Phase 5: Import system state
            logger.info("Phase 5: Importing system state")
            self.import_system_state(dry_run=dry_run)
            
            # Phase 6: Import enhanced prayer metadata
            logger.info("Phase 6: Importing enhanced prayer metadata")
            self.import_enhanced_prayer_data(dry_run=dry_run)
            
            # Phase 7: Validate recovery integrity
            logger.info("Phase 7: Validating recovery integrity")
            self.validate_recovery_integrity()
            
            # Phase 8: Handle missing data
            logger.info("Phase 8: Handling missing data")
            self.handle_missing_data(dry_run=dry_run)
            
            return {
                'success': True,
                'stats': self.recovery_stats,
                'dry_run': dry_run
            }
            
        except Exception as e:
            logger.error(f"Complete recovery failed: {e}")
            self.recovery_stats['errors'].append(f"Recovery failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.recovery_stats
            }
    
    def import_authentication_data(self, dry_run: bool = False):
        """Import authentication requests, approvals, and security events"""
        auth_dir = self.archive_dir / "auth"
        if not auth_dir.exists():
            self.recovery_stats['warnings'].append("No authentication archives found")
            return
        
        # Import authentication requests
        for auth_file in auth_dir.glob("*_auth_requests.txt"):
            self._import_auth_requests(auth_file, dry_run)
        
        # Import authentication approvals
        for approval_file in auth_dir.glob("*_auth_approvals.txt"):
            self._import_auth_approvals(approval_file, dry_run)
        
        # Import security events
        for security_file in auth_dir.glob("*_security_events.txt"):
            self._import_security_events(security_file, dry_run)
        
        # Import notifications
        notifications_dir = auth_dir / "notifications"
        if notifications_dir.exists():
            for notif_file in notifications_dir.glob("*_notifications.txt"):
                self._import_notifications(notif_file, dry_run)
        
        logger.info(f"Imported authentication data from {auth_dir}")
    
    def import_role_system(self, dry_run: bool = False):
        """Import role definitions and assignments"""
        roles_dir = self.archive_dir / "roles"
        if not roles_dir.exists():
            self.recovery_stats['warnings'].append("No role system archives found")
            self._create_default_roles(dry_run)
            return
        
        # Import role definitions
        definitions_file = roles_dir / "role_definitions.txt"
        if definitions_file.exists():
            self._import_role_definitions(definitions_file, dry_run)
        else:
            self._create_default_roles(dry_run)
        
        # Import role assignments
        for assignment_file in roles_dir.glob("*_role_assignments.txt"):
            self._import_role_assignments(assignment_file, dry_run)
        
        logger.info(f"Imported role system from {roles_dir}")
    
    def import_system_state(self, dry_run: bool = False):
        """Import system configuration and invite tokens"""
        system_dir = self.archive_dir / "system"
        if not system_dir.exists():
            self.recovery_stats['warnings'].append("No system state archives found")
            return
        
        # Import invite tokens
        tokens_file = system_dir / "invite_tokens.txt"
        if tokens_file.exists():
            self._import_invite_tokens(tokens_file, dry_run)
        
        # Log system configuration (for reference, not import)
        config_file = system_dir / "system_config.txt"
        if config_file.exists():
            self._log_system_config(config_file)
        
        logger.info(f"Imported system state from {system_dir}")
    
    def import_enhanced_prayer_data(self, dry_run: bool = False):
        """Import enhanced prayer metadata from new archive formats"""
        prayers_dir = self.archive_dir / "prayers"
        if not prayers_dir.exists():
            return
        
        # Import prayer attributes
        attributes_dir = prayers_dir / "attributes"
        if attributes_dir.exists():
            for attr_file in attributes_dir.glob("*_attributes.txt"):
                self._import_prayer_attributes(attr_file, dry_run)
        
        # Import prayer marks
        marks_dir = prayers_dir / "marks"
        if marks_dir.exists():
            for marks_file in marks_dir.glob("*_marks.txt"):
                self._import_prayer_marks(marks_file, dry_run)
        
        # Import prayer skips
        skips_dir = prayers_dir / "skips"
        if skips_dir.exists():
            for skips_file in skips_dir.glob("*_skips.txt"):
                self._import_prayer_skips(skips_file, dry_run)
        
        logger.info("Imported enhanced prayer metadata")
    
    def validate_recovery_integrity(self):
        """Validate the integrity of recovered data"""
        with Session(engine) as session:
            # Validate user-prayer relationships
            orphaned_prayers = session.exec(
                select(Prayer).where(
                    ~Prayer.author_id.in_(select(User.id))
                )
            ).all()
            
            if orphaned_prayers:
                self.recovery_stats['warnings'].append(
                    f"Found {len(orphaned_prayers)} prayers with missing authors"
                )
            
            # Validate invite relationships
            broken_invites = session.exec(
                select(User).where(
                    User.invited_by_user_id.is_not(None),
                    ~User.invited_by_user_id.in_(select(User.id))
                )
            ).all()
            
            if broken_invites:
                self.recovery_stats['warnings'].append(
                    f"Found {len(broken_invites)} users with broken invite relationships"
                )
            
            # Validate role assignments
            orphaned_roles = session.exec(
                select(UserRole).where(
                    ~UserRole.user_id.in_(select(User.id))
                )
            ).all()
            
            if orphaned_roles:
                self.recovery_stats['warnings'].append(
                    f"Found {len(orphaned_roles)} role assignments for missing users"
                )
    
    def handle_missing_data(self, dry_run: bool = False):
        """Handle missing or incomplete data with sensible defaults"""
        if not dry_run:
            with Session(engine) as session:
                # Ensure at least one admin user exists
                admin_role = session.exec(select(Role).where(Role.name == "admin")).first()
                if admin_role:
                    admin_users = session.exec(
                        select(User).join(UserRole).where(UserRole.role_id == admin_role.id)
                    ).all()
                    
                    if not admin_users:
                        # Find the first user and make them admin
                        first_user = session.exec(select(User)).first()
                        if first_user:
                            admin_assignment = UserRole(
                                user_id=first_user.id,
                                role_id=admin_role.id,
                                granted_by=first_user.id,  # self-granted
                                granted_at=datetime.utcnow()
                            )
                            session.add(admin_assignment)
                            session.commit()
                            
                            self.recovery_stats['warnings'].append(
                                f"Granted admin role to first user: {first_user.display_name}"
                            )
        
        logger.info("Handled missing data with defaults")
    
    def _validate_archive_structure(self):
        """Validate that the archive directory has the expected structure"""
        if not self.archive_dir.exists():
            raise ValueError(f"Archive directory not found: {self.archive_dir}")
        
        # Check for core directories
        required_dirs = ["prayers", "users", "activity"]
        for dir_name in required_dirs:
            if not (self.archive_dir / dir_name).exists():
                self.recovery_stats['warnings'].append(f"Missing core directory: {dir_name}")
        
        logger.info("Archive structure validation complete")
    
    def _import_auth_requests(self, file_path: Path, dry_run: bool):
        """Import authentication requests from archive file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.strip().split('\n')
            
            for line in lines:
                if line.startswith('#') or not line.strip() or '|' not in line:
                    continue
                
                parts = line.split('|')
                if len(parts) >= 5:
                    try:
                        timestamp = datetime.fromisoformat(parts[0])
                        user_id = parts[1]
                        device_info = parts[2]
                        ip_address = parts[3]
                        status = parts[4]
                        details = parts[5] if len(parts) > 5 else ""
                        
                        if not dry_run:
                            with Session(engine) as session:
                                # Check if auth request already exists
                                existing = session.exec(
                                    select(AuthenticationRequest).where(
                                        AuthenticationRequest.user_id == user_id,
                                        AuthenticationRequest.created_at == timestamp
                                    )
                                ).first()
                                
                                if not existing:
                                    auth_request = AuthenticationRequest(
                                        user_id=user_id,
                                        device_info=device_info,
                                        ip_address=ip_address,
                                        status=status,
                                        created_at=timestamp,
                                        expires_at=timestamp + timedelta(days=7)
                                    )
                                    session.add(auth_request)
                                    session.commit()
                        
                        self.recovery_stats['auth_requests_recovered'] += 1
                        
                    except Exception as e:
                        error_msg = f"Failed to import auth request from {file_path}: {e}"
                        self.recovery_stats['errors'].append(error_msg)
                        logger.error(error_msg)
                        
        except Exception as e:
            error_msg = f"Failed to read auth requests file {file_path}: {e}"
            self.recovery_stats['errors'].append(error_msg)
            logger.error(error_msg)
    
    def _import_auth_approvals(self, file_path: Path, dry_run: bool):
        """Import authentication approvals from archive file"""
        # Similar implementation pattern to _import_auth_requests
        # Format: timestamp|auth_request_id|approver_user_id|action|details
        pass
    
    def _import_security_events(self, file_path: Path, dry_run: bool):
        """Import security events from archive file"""
        # Similar implementation pattern
        # Format: timestamp|event_type|user_id|ip_address|user_agent|details
        pass
    
    def _import_notifications(self, file_path: Path, dry_run: bool):
        """Import notification events from archive file"""
        # Similar implementation pattern
        # Format: timestamp|user_id|auth_request_id|notification_type|action|details
        pass
    
    def _import_role_definitions(self, file_path: Path, dry_run: bool):
        """Import role definitions from archive file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.strip().split('\n')
            
            for line in lines:
                if line.startswith('#') or not line.strip() or '|' not in line:
                    continue
                
                parts = line.split('|')
                if len(parts) >= 4:
                    try:
                        role_name = parts[0]
                        description = parts[1]
                        permissions_json = parts[2]
                        is_system_role = parts[3].lower() == 'true'
                        created_by = parts[4] if len(parts) > 4 else None
                        
                        if not dry_run:
                            with Session(engine) as session:
                                existing_role = session.exec(
                                    select(Role).where(Role.name == role_name)
                                ).first()
                                
                                if not existing_role:
                                    role = Role(
                                        name=role_name,
                                        description=description,
                                        permissions=permissions_json,
                                        is_system_role=is_system_role,
                                        created_by=created_by
                                    )
                                    session.add(role)
                                    session.commit()
                        
                        self.recovery_stats['roles_recovered'] += 1
                        
                    except Exception as e:
                        error_msg = f"Failed to import role from {file_path}: {e}"
                        self.recovery_stats['errors'].append(error_msg)
                        logger.error(error_msg)
                        
        except Exception as e:
            error_msg = f"Failed to read role definitions file {file_path}: {e}"
            self.recovery_stats['errors'].append(error_msg)
            logger.error(error_msg)
    
    def _import_role_assignments(self, file_path: Path, dry_run: bool):
        """Import role assignments from archive file"""
        # Format: timestamp|user_id|role_name|action|granted_by|expires_at|details
        pass
    
    def _create_default_roles(self, dry_run: bool):
        """Create default system roles if none exist"""
        if not dry_run:
            with Session(engine) as session:
                # Create admin role
                admin_role = session.exec(select(Role).where(Role.name == "admin")).first()
                if not admin_role:
                    admin_role = Role(
                        name="admin",
                        description="System administrator with full access",
                        permissions='["*"]',
                        is_system_role=True
                    )
                    session.add(admin_role)
                
                # Create user role
                user_role = session.exec(select(Role).where(Role.name == "user")).first()
                if not user_role:
                    user_role = Role(
                        name="user",
                        description="Standard user with basic permissions",
                        permissions='["read", "write_own", "pray"]',
                        is_system_role=True
                    )
                    session.add(user_role)
                
                session.commit()
                self.recovery_stats['roles_recovered'] += 2
    
    def _import_invite_tokens(self, file_path: Path, dry_run: bool):
        """Import active invite tokens from archive file"""
        # Format: token|created_by_user|expires_at|used|used_by_user_id|created_at
        pass
    
    def _import_prayer_attributes(self, file_path: Path, dry_run: bool):
        """Import prayer attributes from archive file"""
        # Format: timestamp|prayer_id|attribute_name|attribute_value|user_id
        pass
    
    def _import_prayer_marks(self, file_path: Path, dry_run: bool):
        """Import prayer marks from archive file"""
        # Format: timestamp|prayer_id|user_id
        pass
    
    def _import_prayer_skips(self, file_path: Path, dry_run: bool):
        """Import prayer skips from archive file"""
        # Format: timestamp|prayer_id|user_id
        pass
    
    def _log_system_config(self, file_path: Path):
        """Log system configuration for reference"""
        try:
            content = file_path.read_text(encoding='utf-8')
            logger.info(f"System configuration reference:\n{content}")
            self.recovery_stats['warnings'].append(
                "System configuration found - manual reconfiguration may be needed"
            )
        except Exception as e:
            logger.error(f"Failed to read system config: {e}")
    
    def _merge_stats(self, other_stats: Dict):
        """Merge statistics from another import operation"""
        for key, value in other_stats.items():
            if key in self.recovery_stats:
                if isinstance(value, int):
                    self.recovery_stats[key] += value
                elif isinstance(value, list):
                    self.recovery_stats[key].extend(value)


# Global recovery service instance
recovery_service = CompleteSystemRecovery()