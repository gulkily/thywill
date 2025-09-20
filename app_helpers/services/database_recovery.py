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
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Iterable
from sqlmodel import Session, select
from sqlalchemy import text
import uuid
import secrets

from sqlmodel import SQLModel
from models import (
    engine, User, Prayer, PrayerMark, PrayerAttribute, PrayerActivityLog,
    Role, UserRole, AuthenticationRequest, AuthApproval, AuthAuditLog,
    SecurityLog, Session as UserSession, NotificationState, InviteToken,
    PrayerSkip,
    InviteTokenUsage, MembershipApplication
)
from app_helpers.services.text_archive_service import TextArchiveService
from app_helpers.services.text_importer_service import TextImporterService

logger = logging.getLogger(__name__)


class CompleteSystemRecovery:
    """Service for complete database reconstruction from text archives"""
    
    def __init__(self, archive_dir: str = None):
        self.archive_dir = Path(archive_dir) if archive_dir else Path("text_archives")
        # Note: Don't create TextArchiveService until needed to avoid auto-creating directories
        self._archive_service = None
        self._text_importer = None
        
        self.recovery_stats = {
            'users_recovered': 0,
            'prayers_recovered': 0,
            'prayer_marks_recovered': 0,
            'prayer_attributes_recovered': 0,
            'prayer_skips_recovered': 0,
            'roles_recovered': 0,
            'role_assignments_recovered': 0,
            'auth_requests_recovered': 0,
            'auth_approvals_recovered': 0,
            'auth_audit_logs_recovered': 0,
            'security_events_recovered': 0,
            'invite_tokens_recovered': 0,
            'invite_token_usage_recovered': 0,
            'sessions_recovered': 0,
            'membership_applications_recovered': 0,
            'notifications_recovered': 0,
            'errors': [],
            'warnings': []
        }
    
    @property
    def archive_service(self):
        """Lazy-load archive service to avoid auto-creating directories"""
        if self._archive_service is None:
            self._archive_service = TextArchiveService(str(self.archive_dir))
        return self._archive_service
    
    @property
    def text_importer(self):
        """Lazy-load text importer to avoid auto-creating directories"""
        if self._text_importer is None:
            self._text_importer = TextImporterService(self.archive_service)
        return self._text_importer

    # ── Helper utilities ──────────────────────────────────────────────────

    def _parse_timestamp(self, value: str) -> Optional[datetime]:
        """Parse timestamps from archive files supporting multiple formats."""
        if value is None:
            return None

        text = value.strip()
        if not text or text.lower() in {"none", "never", "n/a"}:
            return None

        # ISO 8601 support
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass

        # Human readable format: July 06 2025 at 12:07
        for fmt in ["%B %d %Y at %H:%M", "%B %d %Y at %H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

        # Fallback: try parsing without "at"
        if " at " in text:
            return self._parse_timestamp(text.replace(" at ", " "))

        raise ValueError(f"Unsupported timestamp format: {text}")

    def _parse_bool(self, value: str) -> bool:
        return str(value).strip().lower() in {"true", "yes", "1"}

    def _iter_data_lines(self, file_path: Path) -> Iterable[str]:
        """Yield meaningful data lines from an archive file."""
        if not file_path.exists():
            return []

        content = file_path.read_text(encoding='utf-8')
        # Normalise cases where entries run together (e.g., "|yesJuly 16 ...")
        content = re.sub(
            r"(\|(?:yes|no))(\s*[A-Z][a-z]+ \d{2} \d{4} at \d{2}:\d{2})",
            r"\1\n\2",
            content
        )
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if (not line or line.startswith('#') or line.lower().startswith('format')
                    or line.lower().startswith('invite tokens')
                    or line.lower().startswith('sessions for ')
                    or line.lower().startswith('prayer marks')
                    or line.lower().startswith('prayer attributes')
                    or line.lower().startswith('prayer activity logs')
                    or line.lower().startswith('role assignments')
                    or line.lower().startswith('user role assignments')
                    or line.lower().startswith('system roles')
                    or '=' in line):
                continue
            yield line

    def _ensure_user(self, session: Session, display_name: str, created_at: Optional[datetime] = None) -> User:
        """Ensure a user record exists and return it."""
        user = session.exec(select(User).where(User.display_name == display_name)).first()
        if user:
            return user

        user = User(
            display_name=display_name,
            created_at=created_at or datetime.utcnow(),
            religious_preference='unspecified'
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        self.recovery_stats['users_recovered'] += 1
        return user

    def _get_or_create_role_by_identifier(self, identifier: str, dry_run: bool) -> Optional[Role]:
        """Fetch role by ID or name; create placeholder if needed."""
        if identifier is None:
            return None

        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            role = session.exec(select(Role).where(Role.id == identifier)).first()
            if not role:
                role = session.exec(select(Role).where(Role.name == identifier)).first()

            if role or dry_run:
                return role

            role = Role(
                name=identifier,
                description=f"Recovered role {identifier}",
                permissions='[]',
                is_system_role=False
            )
            session.add(role)
            session.commit()
            session.refresh(role)
            self.recovery_stats['roles_recovered'] += 1
            return role

    def _parse_membership_application(self, file_path: Path) -> Optional[Dict[str, Any]]:
        content = file_path.read_text(encoding='utf-8')
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        data: Dict[str, Any] = {
            'text_file_path': str(file_path)
        }

        for line in lines:
            if line.startswith('Application ID:'):
                data['id'] = line.split(':', 1)[1].strip()
            elif line.startswith('Submitted:'):
                try:
                    data['created_at'] = datetime.fromisoformat(line.split(':', 1)[1].strip())
                except ValueError:
                    data['created_at'] = datetime.utcnow()
            elif line.startswith('IP Address:'):
                data['ip_address'] = line.split(':', 1)[1].strip()
            elif line.startswith('USERNAME:'):
                data['username'] = line.split(':', 1)[1].strip()
            elif line.startswith('CONTACT INFO:'):
                value = line.split(':', 1)[1].strip()
                data['contact_info'] = value if value.lower() != 'none' else None
            elif line.startswith('STATUS:'):
                data['status'] = line.split(':', 1)[1].strip()
            elif line.startswith('APPROVED by'):
                parts = line.replace('APPROVED by', '').split('at')
                if len(parts) == 2:
                    data['processed_by_user_id'] = parts[0].strip()
                    try:
                        data['processed_at'] = datetime.fromisoformat(parts[1].strip())
                    except ValueError:
                        data['processed_at'] = datetime.utcnow()
                    data['status'] = 'approved'
            elif line.startswith('Invite token:'):
                token_value = line.split(':', 1)[1].strip()
                data['invite_token'] = token_value if token_value else None

        # Extract essay section
        essay_marker = 'ESSAY/MOTIVATION:'
        if essay_marker in content:
            essay_text = content.split(essay_marker, 1)[1]
            if 'CONTACT INFO:' in essay_text:
                essay_text = essay_text.split('CONTACT INFO:', 1)[0]
            data['essay'] = essay_text.strip()

        if 'id' not in data:
            return None

        # Ensure default values
        data.setdefault('status', 'pending')
        data.setdefault('essay', '')
        return data
    
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
            
            # Ensure database tables exist for all operations
            if not dry_run:
                SQLModel.metadata.create_all(engine)
            
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

            # Phase 5b: Import membership applications
            logger.info("Phase 5b: Importing membership applications")
            self.import_membership_applications(dry_run=dry_run)
            
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
        request_files = list(auth_dir.glob("*_auth_requests.txt"))
        if not request_files:
            legacy_requests = self.archive_dir / "authentication" / "auth_requests.txt"
            if legacy_requests.exists():
                request_files.append(legacy_requests)
        for auth_file in request_files:
            self._import_auth_requests(auth_file, dry_run)
        
        # Import authentication approvals
        approval_files = list(auth_dir.glob("*_auth_approvals.txt"))
        if not approval_files:
            legacy_approvals = self.archive_dir / "authentication" / "auth_approvals.txt"
            if legacy_approvals.exists():
                approval_files.append(legacy_approvals)
        for approval_file in approval_files:
            self._import_auth_approvals(approval_file, dry_run)

        # Import authentication audit logs
        audit_files = list(auth_dir.glob("*_auth_audit_logs.txt"))
        legacy_audit = self.archive_dir / "authentication" / "auth_audit_logs.txt"
        if legacy_audit.exists():
            audit_files.append(legacy_audit)
        for audit_file in audit_files:
            self._import_auth_audit_logs(audit_file, dry_run)

        # Import security events
        security_files = list(auth_dir.glob("*_security_events.txt"))
        if not security_files:
            legacy_security = self.archive_dir / "authentication" / "auth_audit_logs.txt"
            if legacy_security.exists():
                security_files.append(legacy_security)
        for security_file in security_files:
            self._import_security_events(security_file, dry_run)
        
        # Import notifications
        notifications_dir = auth_dir / "notifications"
        if notifications_dir.exists():
            for notif_file in notifications_dir.glob("*_notifications.txt"):
                self._import_notifications(notif_file, dry_run)
        else:
            legacy_notifications = self.archive_dir / "authentication" / "auth_notifications.txt"
            if legacy_notifications.exists():
                self._import_notifications(legacy_notifications, dry_run)
        
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
        else:
            # Import invite tokens
            tokens_file = system_dir / "invite_tokens.txt"
            if tokens_file.exists():
                self._import_invite_tokens(tokens_file, dry_run)
            else:
                alt_tokens = self.archive_dir / "invites" / "invite_tokens.txt"
                if alt_tokens.exists():
                    self._import_invite_tokens(alt_tokens, dry_run)

            # Import invite token usage history (system-level export)
            usage_file = system_dir / "invite_token_usage.txt"
            if usage_file.exists():
                self._import_invite_token_usage(usage_file, dry_run)

            # Log system configuration (for reference, not import)
            config_file = system_dir / "system_config.txt"
            if config_file.exists():
                self._log_system_config(config_file)

        # Fallback: invite archives stored under invites/
        alt_usage = self.archive_dir / "invites" / "invite_token_usage.txt"
        if alt_usage.exists():
            self._import_invite_token_usage(alt_usage, dry_run)
        alt_tokens = self.archive_dir / "invites" / "invite_tokens.txt"
        if alt_tokens.exists():
            self._import_invite_tokens(alt_tokens, dry_run)

        # Import active sessions snapshots and monthly archives
        self.import_sessions(dry_run=dry_run)

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
        # Ensure database tables exist before validation
        SQLModel.metadata.create_all(engine)
        
        with Session(engine) as session:
            # Validate user-prayer relationships
            orphaned_prayers = session.exec(
                select(Prayer).where(
                    ~Prayer.author_username.in_(select(User.display_name))
                )
            ).all()
            
            if orphaned_prayers:
                self.recovery_stats['warnings'].append(
                    f"Found {len(orphaned_prayers)} prayers with missing authors"
                )
            
            # Validate invite relationships
            broken_invites = session.exec(
                select(User).where(
                    User.invited_by_username.is_not(None),
                    ~User.invited_by_username.in_(select(User.display_name))
                )
            ).all()
            
            if broken_invites:
                self.recovery_stats['warnings'].append(
                    f"Found {len(broken_invites)} users with broken invite relationships"
                )
            
            # Validate role assignments
            orphaned_roles = session.exec(
                select(UserRole).where(
                    ~UserRole.user_id.in_(select(User.display_name))
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
                        select(User).join(UserRole, User.display_name == UserRole.user_id).where(UserRole.role_id == admin_role.id)
                    ).all()
                    
                    if not admin_users:
                        # Find the first user and make them admin
                        first_user = session.exec(select(User)).first()
                        if first_user:
                            admin_assignment = UserRole(
                                user_id=first_user.display_name,
                                role_id=admin_role.id,
                                granted_by=first_user.display_name,  # self-granted
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
            for line in self._iter_data_lines(file_path):
                parts = [part.strip() for part in line.split('|')]
                if len(parts) < 6:
                    continue

                # Legacy exports may include ID as first column
                if len(parts) == 7:
                    request_id, created_str, user_id, device_info, ip_address, status, detail_field = parts
                else:
                    request_id = uuid.uuid4().hex
                    created_str, user_id, device_info, ip_address, status, detail_field = parts[:6]

                expires_str = None
                extra_flags: List[str] = []
                if detail_field:
                    for segment in detail_field.split(','):
                        segment = segment.strip()
                        if segment.startswith('expires_'):
                            expires_str = segment.replace('expires_', '')
                        elif segment:
                            extra_flags.append(segment)

                try:
                    created_at = self._parse_timestamp(created_str)
                except Exception as exc:
                    error_msg = f"Failed to parse auth request timestamps '{line}': {exc}"
                    self.recovery_stats['errors'].append(error_msg)
                    logger.error(error_msg)
                    continue

                try:
                    expires_at = self._parse_timestamp(expires_str) if expires_str else (created_at + timedelta(days=7))
                except Exception:
                    expires_at = created_at + timedelta(days=7)

                if dry_run:
                    self.recovery_stats['auth_requests_recovered'] += 1
                    continue

                SQLModel.metadata.create_all(engine)
                with Session(engine) as session:
                    existing = session.exec(
                        select(AuthenticationRequest).where(AuthenticationRequest.id == request_id)
                    ).first()

                    if not existing:
                        auth_request = AuthenticationRequest(
                            id=request_id,
                            user_id=user_id,
                            device_info=device_info or None,
                            ip_address=ip_address or None,
                            status=status or 'pending',
                            created_at=created_at,
                            expires_at=expires_at
                        )
                        session.add(auth_request)
                        session.commit()

                self.recovery_stats['auth_requests_recovered'] += 1

        except Exception as e:
            error_msg = f"Failed to read auth requests file {file_path}: {e}"
            self.recovery_stats['errors'].append(error_msg)
            logger.error(error_msg)
    
    def _import_auth_approvals(self, file_path: Path, dry_run: bool):
        """Import authentication approvals from archive file"""
        for line in self._iter_data_lines(file_path):
            parts = [part.strip() for part in line.split('|')]
            if len(parts) < 3:
                continue

            created_str, request_id, approver_id = parts[:3]
            try:
                created_at = self._parse_timestamp(created_str)
            except Exception as exc:
                error_msg = f"Failed to parse auth approval timestamp '{line}': {exc}"
                self.recovery_stats['errors'].append(error_msg)
                logger.error(error_msg)
                continue

            if dry_run:
                self.recovery_stats['auth_approvals_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                # Ensure associated auth request exists
                auth_request = session.exec(
                    select(AuthenticationRequest).where(AuthenticationRequest.id == request_id)
                ).first()
                if not auth_request:
                    auth_request = AuthenticationRequest(
                        id=request_id,
                        user_id=approver_id,
                        status='approved',
                        created_at=created_at,
                        expires_at=created_at + timedelta(days=7)
                    )
                    session.add(auth_request)
                    session.commit()

                existing = session.exec(
                    select(AuthApproval).where(
                        AuthApproval.auth_request_id == request_id,
                        AuthApproval.approver_user_id == approver_id,
                        AuthApproval.created_at == created_at
                    )
                ).first()

                if not existing:
                    approval = AuthApproval(
                        auth_request_id=request_id,
                        approver_user_id=approver_id,
                        created_at=created_at
                    )
                    session.add(approval)
                    session.commit()

            self.recovery_stats['auth_approvals_recovered'] += 1

    def _import_auth_audit_logs(self, file_path: Path, dry_run: bool):
        """Import authentication audit logs from archive file"""
        for line in self._iter_data_lines(file_path):
            parts = [part.strip() for part in line.split('|')]
            if len(parts) < 4:
                continue

            created_str, request_id, action, actor_user_id = parts[:4]
            actor_type = parts[4] if len(parts) > 4 else None
            details = parts[5] if len(parts) > 5 else None
            ip_address = parts[6] if len(parts) > 6 else None
            user_agent = parts[7] if len(parts) > 7 else None

            try:
                created_at = self._parse_timestamp(created_str)
            except Exception as exc:
                error_msg = f"Failed to parse auth audit log timestamp '{line}': {exc}"
                self.recovery_stats['errors'].append(error_msg)
                logger.error(error_msg)
                continue

            if dry_run:
                self.recovery_stats['auth_audit_logs_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                existing = session.exec(
                    select(AuthAuditLog).where(
                        AuthAuditLog.auth_request_id == request_id,
                        AuthAuditLog.created_at == created_at,
                        AuthAuditLog.action == action
                    )
                ).first()

                if not existing:
                    audit_log = AuthAuditLog(
                        auth_request_id=request_id,
                        action=action,
                        actor_user_id=actor_user_id if actor_user_id and actor_user_id.lower() != 'unknown' else None,
                        actor_type=actor_type,
                        details=details,
                        ip_address=ip_address if ip_address and ip_address.lower() != 'unknown' else None,
                        user_agent=user_agent if user_agent and user_agent.lower() != 'unknown' else None,
                        created_at=created_at
                    )
                    session.add(audit_log)
                    session.commit()

            self.recovery_stats['auth_audit_logs_recovered'] += 1

    def _import_security_events(self, file_path: Path, dry_run: bool):
        """Import security events from archive file"""
        for line in self._iter_data_lines(file_path):
            parts = [part.strip() for part in line.split('|')]
            if len(parts) < 4:
                continue

            timestamp_str, event_type, user_id, ip_address = parts[:4]
            user_agent = parts[4] if len(parts) > 4 else None
            details = parts[5] if len(parts) > 5 else None

            try:
                created_at = self._parse_timestamp(timestamp_str)
            except Exception as exc:
                error_msg = f"Failed to parse security log timestamp '{line}': {exc}"
                self.recovery_stats['errors'].append(error_msg)
                logger.error(error_msg)
                continue

            if dry_run:
                self.recovery_stats['security_events_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                if user_id and user_id.lower() not in {'none', 'unknown'}:
                    try:
                        self._ensure_user(session, user_id, created_at)
                    except Exception:
                        pass
                existing = session.exec(
                    select(SecurityLog).where(
                        SecurityLog.event_type == event_type,
                        SecurityLog.user_id == user_id or SecurityLog.user_id.is_(None),
                        SecurityLog.created_at == created_at,
                        SecurityLog.details == (details or None)
                    )
                ).first()

                if not existing:
                    log_entry = SecurityLog(
                        event_type=event_type,
                        user_id=user_id if user_id and user_id.lower() != 'none' else None,
                        ip_address=ip_address if ip_address and ip_address.lower() != 'unknown' else None,
                        user_agent=user_agent if user_agent and user_agent.lower() != 'unknown' else None,
                        details=details,
                        created_at=created_at
                    )
                    session.add(log_entry)
                    session.commit()

            self.recovery_stats['security_events_recovered'] += 1

    def _import_notifications(self, file_path: Path, dry_run: bool):
        """Import notification events from archive file"""
        for line in self._iter_data_lines(file_path):
            parts = [part.strip() for part in line.split('|')]
            if len(parts) < 4:
                continue

            timestamp_str, user_id, auth_request_id, notification_type = parts[:4]
            action = parts[4] if len(parts) > 4 else None
            details = parts[5] if len(parts) > 5 else None

            try:
                created_at = self._parse_timestamp(timestamp_str)
            except Exception as exc:
                error_msg = f"Failed to parse notification timestamp '{line}': {exc}"
                self.recovery_stats['errors'].append(error_msg)
                logger.error(error_msg)
                continue

            if dry_run:
                self.recovery_stats['notifications_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                if user_id:
                    try:
                        self._ensure_user(session, user_id, created_at)
                    except Exception:
                        pass
                existing = session.exec(
                    select(NotificationState).where(
                        NotificationState.user_id == user_id,
                        NotificationState.auth_request_id == auth_request_id,
                        NotificationState.notification_type == notification_type,
                        NotificationState.created_at == created_at
                    )
                ).first()

                if not existing:
                    notification = NotificationState(
                        user_id=user_id,
                        auth_request_id=auth_request_id,
                        notification_type=notification_type,
                        is_read=(action or '').lower() == 'read',
                        created_at=created_at,
                        read_at=self._parse_timestamp(details) if details and 'read_at=' in details else None
                    )
                    session.add(notification)
                    session.commit()

            self.recovery_stats['notifications_recovered'] += 1

    # ── Sessions & Membership Applications ─────────────────────────────────

    def import_sessions(self, dry_run: bool = False):
        sessions_dir = self.archive_dir / "sessions"
        if sessions_dir.exists():
            for sessions_file in sessions_dir.glob("*.txt"):
                self._import_sessions_file(sessions_file, dry_run)

        snapshot_file = self.archive_dir / "system" / "current_state" / "active_sessions.txt"
        if snapshot_file.exists():
            self._import_active_sessions_snapshot(snapshot_file, dry_run)

    def _import_sessions_file(self, file_path: Path, dry_run: bool):
        for line in self._iter_data_lines(file_path):
            parts = [part.strip() for part in line.split('|')]
            if len(parts) < 7:
                continue

            created_str, session_id, username, expires_str, device_info, ip_address, auth_str = parts[:7]

            # auth_str may be like "yes" or "no"
            auth_lower = auth_str.lower()
            is_auth = auth_lower.startswith('y') or auth_lower.startswith('t')
            remainder = auth_str[len('yes'):] if auth_str.lower().startswith('yes') else (
                auth_str[len('no'):] if auth_str.lower().startswith('no') else ''
            )
            if remainder.strip():
                # leftover text belongs to next line; requeue
                parts_tail = remainder.strip()
                if parts_tail:
                    # Prepend to generator by logging warning
                    logger.debug(f"Recovered remainder while parsing sessions file {file_path}: {parts_tail}")

            try:
                created_at = self._parse_timestamp(created_str)
                expires_at = self._parse_timestamp(expires_str)
            except Exception as exc:
                error_msg = f"Failed to parse session timestamps '{line}': {exc}"
                self.recovery_stats['errors'].append(error_msg)
                logger.error(error_msg)
                continue

            if dry_run:
                self.recovery_stats['sessions_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                self._ensure_user(session, username, created_at)
                existing = session.get(UserSession, session_id)
                if not existing:
                    sess = UserSession(
                        id=session_id,
                        username=username,
                        created_at=created_at,
                        expires_at=expires_at,
                        device_info=device_info if device_info and device_info.lower() != 'unknown' else None,
                        ip_address=ip_address if ip_address and ip_address.lower() != 'unknown' else None,
                        is_fully_authenticated=is_auth
                    )
                    session.add(sess)
                    session.commit()
                else:
                    existing.username = username
                    existing.created_at = created_at
                    existing.expires_at = expires_at
                    existing.device_info = device_info if device_info and device_info.lower() != 'unknown' else None
                    existing.ip_address = ip_address if ip_address and ip_address.lower() != 'unknown' else None
                    existing.is_fully_authenticated = is_auth
                    session.add(existing)
                    session.commit()

            self.recovery_stats['sessions_recovered'] += 1

    def _import_active_sessions_snapshot(self, file_path: Path, dry_run: bool):
        content = file_path.read_text(encoding='utf-8')
        blocks = content.split("Session ")
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.splitlines()
            header = lines[0] if lines else ""
            session_id = header.split(':')[0] if ':' in header else header

            data = {}
            for line in lines[1:]:
                if ':' not in line:
                    continue
                key, value = line.split(':', 1)
                data[key.strip().lower()] = value.strip()

            try:
                created_at = self._parse_timestamp(data.get('created')) if 'created' in data else datetime.utcnow()
                expires_at = self._parse_timestamp(data.get('expires')) if 'expires' in data else created_at + timedelta(days=14)
            except Exception:
                created_at = datetime.utcnow()
                expires_at = created_at + timedelta(days=14)

            username = data.get('user', '').split('(')[0].strip()
            ip_address = data.get('ip')
            device_info = data.get('device')
            is_fully_authenticated = data.get('fully authenticated', 'true').lower().startswith('true')

            if dry_run:
                self.recovery_stats['sessions_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                self._ensure_user(session, username, created_at)
                existing = session.get(UserSession, session_id)
                if not existing:
                    session_obj = UserSession(
                        id=session_id,
                        username=username,
                        created_at=created_at,
                        expires_at=expires_at,
                        device_info=device_info,
                        ip_address=ip_address,
                        is_fully_authenticated=is_fully_authenticated
                    )
                    session.add(session_obj)
                    session.commit()
                else:
                    existing.username = username
                    existing.created_at = created_at
                    existing.expires_at = expires_at
                    existing.device_info = device_info
                    existing.ip_address = ip_address
                    existing.is_fully_authenticated = is_fully_authenticated
                    session.add(existing)
                    session.commit()

            self.recovery_stats['sessions_recovered'] += 1

    def import_membership_applications(self, dry_run: bool = False):
        apps_dir = self.archive_dir / "membership_applications"
        if not apps_dir.exists():
            return

        for app_file in apps_dir.glob("*.txt"):
            try:
                data = self._parse_membership_application(app_file)
            except Exception as exc:
                error_msg = f"Failed to parse membership application {app_file}: {exc}"
                self.recovery_stats['errors'].append(error_msg)
                logger.error(error_msg)
                continue

            if not data:
                continue

            if dry_run:
                self.recovery_stats['membership_applications_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                if data.get('username'):
                    try:
                        self._ensure_user(session, data['username'], data.get('created_at'))
                    except Exception:
                        pass
                if data.get('processed_by_user_id'):
                    try:
                        self._ensure_user(session, data['processed_by_user_id'], data.get('processed_at'))
                    except Exception:
                        pass
                existing = session.exec(
                    select(MembershipApplication).where(MembershipApplication.id == data['id'])
                ).first()

                if not existing:
                    application = MembershipApplication(**data)
                    session.add(application)
                else:
                    for key, value in data.items():
                        setattr(existing, key, value)
                    session.add(existing)
                session.commit()

            self.recovery_stats['membership_applications_recovered'] += 1
    
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
                            # Ensure database tables exist before insert
                            SQLModel.metadata.create_all(engine)
                            
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
        for line in self._iter_data_lines(file_path):
            parts = [part.strip() for part in line.split('|')]

            # Handle exports with ID column (user_roles.txt)
            if len(parts) >= 6 and parts[1].endswith('at'):
                # Format: id|granted_at|user_id|role_id|granted_by|expires_at
                assignment_id, granted_str, user_id, role_identifier, granted_by, expires_str = parts[:6]
                role = self._get_or_create_role_by_identifier(role_identifier, dry_run)
                action = 'assigned'
                details = None
            elif len(parts) >= 6:
                # Format: timestamp|user_id|role_name|action|granted_by|expires_at|details
                granted_str, user_id, role_name, action, granted_by, expires_str = parts[:6]
                details = parts[6] if len(parts) > 6 else None
                assignment_id = uuid.uuid4().hex
                role = self._get_or_create_role_by_identifier(role_name, dry_run)
            else:
                continue

            try:
                granted_at = self._parse_timestamp(granted_str)
            except Exception as exc:
                error_msg = f"Failed to parse role assignment timestamp '{line}': {exc}"
                self.recovery_stats['errors'].append(error_msg)
                logger.error(error_msg)
                continue

            expires_at = None
            if expires_str and expires_str.lower() not in {'none', 'never'}:
                try:
                    expires_at = self._parse_timestamp(expires_str)
                except Exception:
                    expires_at = None

            if dry_run:
                if action == 'assigned':
                    self.recovery_stats['role_assignments_recovered'] += 1
                continue

            if role is None:
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                self._ensure_user(session, user_id, granted_at)
                if granted_by and granted_by.lower() not in {'system', 'none'}:
                    try:
                        self._ensure_user(session, granted_by, granted_at)
                    except Exception:
                        pass

                if action.lower() == 'assigned':
                    existing = session.exec(
                        select(UserRole).where(
                            UserRole.user_id == user_id,
                            UserRole.role_id == role.id,
                            UserRole.granted_at == granted_at
                        )
                    ).first()

                    if not existing:
                        assignment = UserRole(
                            id=assignment_id,
                            user_id=user_id,
                            role_id=role.id,
                            granted_by=granted_by if granted_by and granted_by.lower() != 'system' else None,
                            granted_at=granted_at,
                            expires_at=expires_at
                        )
                        session.add(assignment)
                        session.commit()
                        self.recovery_stats['role_assignments_recovered'] += 1
                elif action.lower() in {'revoked', 'removed'}:
                    session.exec(
                        text("DELETE FROM user_roles WHERE user_id = :user AND role_id = :role"),
                        {"user": user_id, "role": role.id}
                    )
                    session.commit()

    
    def _create_default_roles(self, dry_run: bool):
        """Create default system roles if none exist"""
        if dry_run:
            # In dry run mode, still count the roles that would be created
            self.recovery_stats['roles_recovered'] += 2
            logger.info("Would create 2 default roles (admin, user)")
        else:
            # Ensure database tables exist before creation
            SQLModel.metadata.create_all(engine)
            
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
                    self.recovery_stats['roles_recovered'] += 1
                
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
                    self.recovery_stats['roles_recovered'] += 1
                
                session.commit()
    
    def _import_invite_tokens(self, file_path: Path, dry_run: bool):
        """Import active invite tokens from archive file"""
        for line in self._iter_data_lines(file_path):
            parts = [part.strip() for part in line.split('|')]
            if len(parts) < 5:
                continue

            token = parts[0]
            created_by = parts[1]

            if parts[2].isdigit():  # Format with usage_count
                usage_count = int(parts[2])
                max_uses_str = parts[3] if len(parts) > 3 else None
                expires_str = parts[4] if len(parts) > 4 else None
                used_by = parts[5] if len(parts) > 5 else None
            else:  # Format with expires_at|used|used_by|created_at
                usage_count = 0
                max_uses_str = None
                expires_str = parts[2]
                used_flag = parts[3] if len(parts) > 3 else 'false'
                used_by = parts[4] if len(parts) > 4 else None
                if used_flag.lower() in {'true', 'yes'} and used_by and used_by.lower() not in {'none', 'null'}:
                    usage_count = 1

            created_at_str = parts[5] if len(parts) > 5 else None
            if len(parts) > 6:
                created_at_str = parts[6]

            max_uses = None
            if max_uses_str and max_uses_str.lower() not in {'none', 'unlimited'}:
                try:
                    max_uses = int(max_uses_str)
                except ValueError:
                    max_uses = None

            try:
                expires_at = self._parse_timestamp(expires_str) if expires_str else datetime.utcnow() + timedelta(days=30)
            except Exception:
                expires_at = datetime.utcnow() + timedelta(days=30)

            used_by_user = used_by if used_by and used_by.lower() not in {'none', 'null'} else None
            try:
                created_timestamp = self._parse_timestamp(created_at_str) if created_at_str else None
            except Exception:
                created_timestamp = None

            if dry_run:
                self.recovery_stats['invite_tokens_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                existing = session.get(InviteToken, token)

                if not existing:
                    invite = InviteToken(
                        token=token,
                        created_by_user=created_by,
                        usage_count=usage_count,
                        max_uses=max_uses,
                        expires_at=expires_at,
                        used_by_user_id=used_by_user
                    )
                    session.add(invite)
                else:
                    existing.created_by_user = created_by
                    existing.usage_count = usage_count
                    existing.max_uses = max_uses
                    existing.expires_at = expires_at
                    existing.used_by_user_id = used_by_user
                    session.add(existing)

                if created_timestamp:
                    # backfill created_at if column exists (legacy compatibility)
                    try:
                        session.exec(
                            text("UPDATE invitetoken SET created_at = :created_at WHERE token = :token"),
                            {"created_at": created_timestamp.isoformat(), "token": token}
                        )
                        session.commit()
                    except Exception:
                        session.rollback()
                        # Column may not exist; ignore

                session.commit()

            self.recovery_stats['invite_tokens_recovered'] += 1

    def _import_invite_token_usage(self, file_path: Path, dry_run: bool):
        """Import invite token usage history"""
        for line in self._iter_data_lines(file_path):
            parts = [part.strip() for part in line.split('|')]
            if len(parts) < 3:
                continue

            timestamp_str, token_id, user_id = parts[:3]
            ip_address = parts[3] if len(parts) > 3 else None

            try:
                claimed_at = self._parse_timestamp(timestamp_str)
            except Exception as exc:
                error_msg = f"Failed to parse invite usage timestamp '{line}': {exc}"
                self.recovery_stats['errors'].append(error_msg)
                logger.error(error_msg)
                continue

            if dry_run:
                self.recovery_stats['invite_token_usage_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                existing = session.exec(
                    select(InviteTokenUsage).where(
                        InviteTokenUsage.invite_token_id == token_id,
                        InviteTokenUsage.user_id == user_id,
                        InviteTokenUsage.claimed_at == claimed_at
                    )
                ).first()

                if not existing:
                    usage = InviteTokenUsage(
                        invite_token_id=token_id,
                        user_id=user_id,
                        claimed_at=claimed_at,
                        ip_address=ip_address if ip_address and ip_address.lower() != 'none' else None
                    )
                    session.add(usage)
                    session.commit()

            self.recovery_stats['invite_token_usage_recovered'] += 1
    
    def _import_prayer_attributes(self, file_path: Path, dry_run: bool):
        """Import prayer attributes from archive file"""
        for line in self._iter_data_lines(file_path):
            parts = [part.strip() for part in line.split('|')]

            if len(parts) >= 6:
                attribute_id, timestamp_str, prayer_id, name, value, user_id = parts[:6]
            elif len(parts) >= 5:
                attribute_id = uuid.uuid4().hex
                timestamp_str, prayer_id, name, value, user_id = parts[:5]
            else:
                continue

            try:
                created_at = self._parse_timestamp(timestamp_str)
            except Exception as exc:
                error_msg = f"Failed to parse prayer attribute timestamp '{line}': {exc}"
                self.recovery_stats['errors'].append(error_msg)
                logger.error(error_msg)
                continue

            if dry_run:
                self.recovery_stats['prayer_attributes_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                prayer = session.exec(select(Prayer).where(Prayer.id == prayer_id)).first()
                if not prayer:
                    logger.warning(f"Skipping attribute for missing prayer {prayer_id}")
                    continue

                self._ensure_user(session, user_id, created_at)

                existing = session.exec(
                    select(PrayerAttribute).where(
                        PrayerAttribute.id == attribute_id
                    )
                ).first()

                if not existing:
                    attr = PrayerAttribute(
                        id=attribute_id,
                        prayer_id=prayer_id,
                        attribute_name=name,
                        attribute_value=value or 'true',
                        created_by=user_id,
                        created_at=created_at,
                        text_file_path=prayer.text_file_path
                    )
                    session.add(attr)
                    session.commit()

            self.recovery_stats['prayer_attributes_recovered'] += 1

    def _import_prayer_marks(self, file_path: Path, dry_run: bool):
        """Import prayer marks from archive file"""
        for line in self._iter_data_lines(file_path):
            parts = [part.strip() for part in line.split('|')]

            if len(parts) >= 4:
                mark_id, timestamp_str, prayer_id, username = parts[:4]
            elif len(parts) >= 3:
                mark_id = uuid.uuid4().hex
                timestamp_str, prayer_id, username = parts[:3]
            else:
                continue

            try:
                created_at = self._parse_timestamp(timestamp_str)
            except Exception as exc:
                error_msg = f"Failed to parse prayer mark timestamp '{line}': {exc}"
                self.recovery_stats['errors'].append(error_msg)
                logger.error(error_msg)
                continue

            if dry_run:
                self.recovery_stats['prayer_marks_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                prayer = session.exec(select(Prayer).where(Prayer.id == prayer_id)).first()
                if not prayer:
                    logger.warning(f"Skipping mark for missing prayer {prayer_id}")
                    continue

                self._ensure_user(session, username, created_at)

                existing = session.exec(
                    select(PrayerMark).where(PrayerMark.id == mark_id)
                ).first()

                if not existing:
                    mark = PrayerMark(
                        id=mark_id,
                        prayer_id=prayer_id,
                        username=username,
                        created_at=created_at,
                        text_file_path=prayer.text_file_path
                    )
                    session.add(mark)
                    session.commit()

            self.recovery_stats['prayer_marks_recovered'] += 1

    def _import_prayer_skips(self, file_path: Path, dry_run: bool):
        """Import prayer skips from archive file"""
        for line in self._iter_data_lines(file_path):
            parts = [part.strip() for part in line.split('|')]
            if len(parts) < 3:
                continue

            timestamp_str, prayer_id, username = parts[:3]

            try:
                created_at = self._parse_timestamp(timestamp_str)
            except Exception as exc:
                error_msg = f"Failed to parse prayer skip timestamp '{line}': {exc}"
                self.recovery_stats['errors'].append(error_msg)
                logger.error(error_msg)
                continue

            if dry_run:
                self.recovery_stats['prayer_skips_recovered'] += 1
                continue

            SQLModel.metadata.create_all(engine)
            with Session(engine) as session:
                prayer = session.exec(select(Prayer).where(Prayer.id == prayer_id)).first()
                if not prayer:
                    continue

                self._ensure_user(session, username, created_at)

                existing = session.exec(
                    select(PrayerSkip).where(
                        PrayerSkip.prayer_id == prayer_id,
                        PrayerSkip.user_id == username,
                        PrayerSkip.created_at == created_at
                    )
                ).first()

                if not existing:
                    skip = PrayerSkip(
                        prayer_id=prayer_id,
                        user_id=username,
                        created_at=created_at
                    )
                    session.add(skip)
                    session.commit()

            self.recovery_stats['prayer_skips_recovered'] += 1
    
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
    
    def _recover_authentication_requests(self, session: Session) -> Dict:
        """Test-friendly method to recover authentication requests and return stats"""
        auth_file = self.archive_dir / "authentication_requests.txt"
        if auth_file.exists():
            self._import_auth_requests(auth_file, dry_run=False)
        return self.recovery_stats


# Global recovery service instance
recovery_service = CompleteSystemRecovery()
