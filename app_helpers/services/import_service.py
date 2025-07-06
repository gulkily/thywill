#!/usr/bin/env python3
"""
Import Service for ThyWill

Handles complete database import from unified text archive structure.
Replaces separate import scripts with clean, maintainable code.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add current directory to path for imports
sys.path.append('.')

from models import *
from sqlmodel import Session as DBSession, select


class ImportService:
    """Service for importing all database data from text archives."""
    
    def __init__(self, archives_dir: str = "text_archives"):
        self.archives_dir = Path(archives_dir)
        self.imported_counts = {}
        
    def import_all(self, dry_run: bool = False) -> bool:
        """Import all database data from unified text archive structure."""
        print("📥 Importing Complete Database from Text Archives")
        print("=" * 50)
        
        if not os.environ.get('PRODUCTION_MODE'):
            print("❌ PRODUCTION_MODE not set - cannot access database")
            return False
        
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            print()
        
        try:
            self._ensure_database_initialized(dry_run)
            
            from models import engine
            with DBSession(engine) as session:
                success = True
                
                # Import all data categories
                import_functions = [
                    self._import_prayer_data,
                    self._import_user_data,
                    self._import_session_data,
                    self._import_authentication_data,
                    self._import_invite_data,
                    self._import_role_data,
                    self._import_security_data,
                    self._import_system_data
                ]
                
                for import_func in import_functions:
                    try:
                        if not import_func(session, dry_run):
                            success = False
                    except Exception as e:
                        print(f"❌ Error in {import_func.__name__}: {e}")
                        success = False
                        # Rollback and create a new session to continue
                        if not dry_run:
                            session.rollback()
                            session.close()
                            session = DBSession(engine)
                
                if success:
                    print("\n✅ Complete database import completed successfully!")
                    self._print_import_summary(dry_run)
                    return True
                else:
                    print("\n❌ Database import completed with errors")
                    return False
                    
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            return False
    
    def _ensure_database_initialized(self, dry_run: bool):
        """Ensure database is initialized before import."""
        from models import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        # Check if core tables exist
        required_tables = ['user', 'prayer', 'session', 'invitetoken', 'role']
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            if dry_run:
                print(f"⚠️  Database not initialized (missing tables: {', '.join(missing_tables)})")
                print("💡 Would initialize database before import")
            else:
                print(f"⚠️  Database not initialized (missing tables: {', '.join(missing_tables)})")
                print("🔧 Initializing database first...")
                
                # Initialize database tables
                from models import SQLModel
                SQLModel.metadata.create_all(engine)
                print("✅ Database tables created")
        
        print()
    
    def _import_prayer_data(self, session: DBSession, dry_run: bool) -> bool:
        """Import prayer-related data from text_archives/prayers/"""
        print("  📄 Importing prayer data...")
        
        prayer_dir = self.archives_dir / "prayers"
        if not prayer_dir.exists():
            print("    ⚠️  No prayer directory found")
            return True
        
        total_imported = 0
        
        # Import prayer attributes
        attributes_file = prayer_dir / "prayer_attributes.txt"
        if attributes_file.exists():
            imported = self._import_data_file(
                attributes_file, 
                lambda parts: self._import_prayer_attribute(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        # Import prayer marks
        marks_file = prayer_dir / "prayer_marks.txt"
        if marks_file.exists():
            imported = self._import_data_file(
                marks_file,
                lambda parts: self._import_prayer_mark(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        # Import prayer skips
        skips_file = prayer_dir / "prayer_skips.txt"
        if skips_file.exists():
            imported = self._import_data_file(
                skips_file,
                lambda parts: self._import_prayer_skip(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        # Import prayer activity logs
        activity_file = prayer_dir / "prayer_activity_logs.txt"
        if activity_file.exists():
            imported = self._import_data_file(
                activity_file,
                lambda parts: self._import_prayer_activity_log(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        if not dry_run and total_imported > 0:
            session.commit()
        
        self.imported_counts['prayer_data'] = total_imported
        action = "Would import" if dry_run else "Imported"
        print(f"    ✅ {action} {total_imported} prayer-related records")
        return True
    
    def _import_user_data(self, session: DBSession, dry_run: bool) -> bool:
        """Import user-related data from text_archives/users/"""
        print("  📄 Importing user data...")
        
        users_dir = self.archives_dir / "users"
        if not users_dir.exists():
            print("    ⚠️  No users directory found")
            return True
        
        total_imported = 0
        
        # Import notification states
        notifications_file = users_dir / "notification_states.txt"
        if notifications_file.exists():
            imported = self._import_data_file(
                notifications_file,
                lambda parts: self._import_notification_state(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        if not dry_run and total_imported > 0:
            session.commit()
        
        self.imported_counts['user_data'] = total_imported
        action = "Would import" if dry_run else "Imported"
        print(f"    ✅ {action} {total_imported} user-related records")
        return True
    
    def _import_session_data(self, session: DBSession, dry_run: bool) -> bool:
        """Import session data from text_archives/sessions/"""
        print("  📄 Importing session data...")
        
        sessions_dir = self.archives_dir / "sessions"
        if not sessions_dir.exists():
            print("    ⚠️  No sessions directory found")
            return True
        
        total_imported = 0
        
        # Import all session files
        for session_file in sessions_dir.glob("*_sessions.txt"):
            imported = self._import_data_file(
                session_file,
                lambda parts: self._import_session(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        if not dry_run and total_imported > 0:
            session.commit()
        
        self.imported_counts['sessions'] = total_imported
        action = "Would import" if dry_run else "Imported"
        print(f"    ✅ {action} {total_imported} session records")
        return True
    
    def _import_authentication_data(self, session: DBSession, dry_run: bool) -> bool:
        """Import authentication data from text_archives/authentication/"""
        print("  📄 Importing authentication data...")
        
        auth_dir = self.archives_dir / "authentication"
        if not auth_dir.exists():
            print("    ⚠️  No authentication directory found")
            return True
        
        total_imported = 0
        
        # Import auth requests
        requests_file = auth_dir / "auth_requests.txt"
        if requests_file.exists():
            imported = self._import_data_file(
                requests_file,
                lambda parts: self._import_auth_request(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        # Import auth approvals
        approvals_file = auth_dir / "auth_approvals.txt"
        if approvals_file.exists():
            imported = self._import_data_file(
                approvals_file,
                lambda parts: self._import_auth_approval(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        # Import auth audit logs
        audit_file = auth_dir / "auth_audit_logs.txt"
        if audit_file.exists():
            imported = self._import_data_file(
                audit_file,
                lambda parts: self._import_auth_audit_log(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        if not dry_run and total_imported > 0:
            session.commit()
        
        self.imported_counts['authentication'] = total_imported
        action = "Would import" if dry_run else "Imported"
        print(f"    ✅ {action} {total_imported} authentication records")
        return True
    
    def _import_invite_data(self, session: DBSession, dry_run: bool) -> bool:
        """Import invite data from text_archives/invites/"""
        print("  📄 Importing invite data...")
        
        invites_dir = self.archives_dir / "invites"
        if not invites_dir.exists():
            print("    ⚠️  No invites directory found")
            return True
        
        total_imported = 0
        
        # Import invite tokens
        tokens_file = invites_dir / "invite_tokens.txt"
        if tokens_file.exists():
            imported = self._import_data_file(
                tokens_file,
                lambda parts: self._import_invite_token(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        # Import invite token usage
        usage_file = invites_dir / "invite_token_usage.txt"
        if usage_file.exists():
            imported = self._import_data_file(
                usage_file,
                lambda parts: self._import_invite_usage(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        if not dry_run and total_imported > 0:
            session.commit()
        
        self.imported_counts['invites'] = total_imported
        action = "Would import" if dry_run else "Imported"
        print(f"    ✅ {action} {total_imported} invite records")
        return True
    
    def _import_role_data(self, session: DBSession, dry_run: bool) -> bool:
        """Import role data from text_archives/roles/"""
        print("  📄 Importing role data...")
        
        roles_dir = self.archives_dir / "roles"
        if not roles_dir.exists():
            print("    ⚠️  No roles directory found")
            return True
        
        total_imported = 0
        
        # Import roles
        roles_file = roles_dir / "roles.txt"
        if roles_file.exists():
            imported = self._import_data_file(
                roles_file,
                lambda parts: self._import_role(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        # Import user roles
        user_roles_file = roles_dir / "user_roles.txt"
        if user_roles_file.exists():
            imported = self._import_data_file(
                user_roles_file,
                lambda parts: self._import_user_role(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        if not dry_run and total_imported > 0:
            session.commit()
        
        self.imported_counts['roles'] = total_imported
        action = "Would import" if dry_run else "Imported"
        print(f"    ✅ {action} {total_imported} role records")
        return True
    
    def _import_security_data(self, session: DBSession, dry_run: bool) -> bool:
        """Import security data from text_archives/security/"""
        print("  📄 Importing security data...")
        
        security_dir = self.archives_dir / "security"
        if not security_dir.exists():
            print("    ⚠️  No security directory found")
            return True
        
        total_imported = 0
        
        # Import all security event files
        for security_file in security_dir.glob("*_security_events.txt"):
            imported = self._import_data_file(
                security_file,
                lambda parts: self._import_security_log(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        if not dry_run and total_imported > 0:
            session.commit()
        
        self.imported_counts['security'] = total_imported
        action = "Would import" if dry_run else "Imported"
        print(f"    ✅ {action} {total_imported} security records")
        return True
    
    def _import_system_data(self, session: DBSession, dry_run: bool) -> bool:
        """Import system data from text_archives/system/"""
        print("  📄 Importing system data...")
        
        system_dir = self.archives_dir / "system"
        if not system_dir.exists():
            print("    ⚠️  No system directory found")
            return True
        
        total_imported = 0
        
        # Import changelog entries
        changelog_file = system_dir / "changelog_entries.txt"
        if changelog_file.exists():
            imported = self._import_data_file(
                changelog_file,
                lambda parts: self._import_changelog_entry(session, parts, dry_run),
                dry_run
            )
            total_imported += imported
        
        if not dry_run and total_imported > 0:
            session.commit()
        
        self.imported_counts['system'] = total_imported
        action = "Would import" if dry_run else "Imported"
        print(f"    ✅ {action} {total_imported} system records")
        return True
    
    def _import_data_file(self, file_path: Path, import_func, dry_run: bool) -> int:
        """Import data from a text archive file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[3:]  # Skip header lines
        
        imported_count = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split('|')
            if import_func(parts):
                imported_count += 1
        
        return imported_count
    
    # Individual import functions for each data type
    def _import_prayer_attribute(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 6:
            return False
        
        attr_id, set_at_str, prayer_id, attr_name, attr_value, set_by_user_id = parts[:6]
        set_at = datetime.strptime(set_at_str, "%B %d %Y at %H:%M")
        attr_value = attr_value.replace('\\|', '|')
        
        # Check if already exists
        existing = session.exec(select(PrayerAttribute).where(PrayerAttribute.id == attr_id)).first()
        
        if not existing and not dry_run:
            attr = PrayerAttribute(
                id=attr_id,
                prayer_id=prayer_id,
                attribute_name=attr_name,
                attribute_value=attr_value or None,
                set_by_user_id=set_by_user_id,
                set_at=set_at
            )
            session.add(attr)
        
        return not existing
    
    def _import_prayer_mark(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 4:
            return False
        
        mark_id, created_at_str, prayer_id, username = parts[:4]
        created_at = datetime.strptime(created_at_str, "%B %d %Y at %H:%M")
        
        # Check if already exists
        existing = session.exec(select(PrayerMark).where(PrayerMark.id == mark_id)).first()
        
        if not existing and not dry_run:
            mark = PrayerMark(
                id=mark_id,
                prayer_id=prayer_id,
                username=username,
                created_at=created_at
            )
            session.add(mark)
        
        return not existing
    
    def _import_prayer_skip(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 4:
            return False
        
        skip_id, created_at_str, prayer_id, user_id = parts[:4]
        created_at = datetime.strptime(created_at_str, "%B %d %Y at %H:%M")
        
        # Check if already exists
        existing = session.exec(select(PrayerSkip).where(PrayerSkip.id == skip_id)).first()
        
        if not existing and not dry_run:
            skip = PrayerSkip(
                id=skip_id,
                prayer_id=prayer_id,
                user_id=user_id,
                created_at=created_at
            )
            session.add(skip)
        
        return not existing
    
    def _import_prayer_activity_log(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 7:
            return False
        
        log_id, created_at_str, prayer_id, user_id, action, old_value, new_value = parts[:7]
        created_at = datetime.strptime(created_at_str, "%B %d %Y at %H:%M")
        old_value = old_value.replace('\\|', '|') if old_value else None
        new_value = new_value.replace('\\|', '|') if new_value else None
        
        # Check if already exists
        existing = session.exec(select(PrayerActivityLog).where(PrayerActivityLog.id == log_id)).first()
        
        if not existing and not dry_run:
            activity = PrayerActivityLog(
                id=log_id,
                prayer_id=prayer_id,
                user_id=user_id,
                action=action,
                old_value=old_value,
                new_value=new_value,
                created_at=created_at
            )
            session.add(activity)
        
        return not existing
    
    def _import_notification_state(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 7:
            return False
        
        state_id, created_at_str, user_id, auth_request_id, notification_type, is_read, read_at_str = parts[:7]
        created_at = datetime.strptime(created_at_str, "%B %d %Y at %H:%M")
        read_at = datetime.strptime(read_at_str, "%B %d %Y at %H:%M") if read_at_str != "never" else None
        
        # Check if already exists
        existing = session.exec(select(NotificationState).where(NotificationState.id == state_id)).first()
        
        if not existing and not dry_run:
            state = NotificationState(
                id=state_id,
                user_id=user_id,
                auth_request_id=auth_request_id,
                notification_type=notification_type,
                is_read=(is_read == "yes"),
                created_at=created_at,
                read_at=read_at
            )
            session.add(state)
        
        return not existing
    
    def _import_session(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 7:
            return False
        
        created_str, session_id, username, expires_str, device_info, ip_address, is_fully_auth = parts[:7]
        created_at = datetime.strptime(created_str, "%B %d %Y at %H:%M")
        expires_at = datetime.strptime(expires_str, "%B %d %Y at %H:%M")
        
        # Check if already exists
        existing = session.exec(select(Session).where(Session.id == session_id)).first()
        
        if not existing and not dry_run:
            sess = Session(
                id=session_id,
                username=username,
                created_at=created_at,
                expires_at=expires_at,
                device_info=device_info if device_info != "unknown" else None,
                ip_address=ip_address if ip_address != "unknown" else None,
                is_fully_authenticated=(is_fully_auth == "yes")
            )
            session.add(sess)
        
        return not existing
    
    def _import_auth_request(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 7:
            return False
        
        req_id, created_str, user_id, device_info, ip_address, status, expires_str = parts[:7]
        created_at = datetime.strptime(created_str, "%B %d %Y at %H:%M")
        expires_at = datetime.strptime(expires_str, "%B %d %Y at %H:%M")
        
        # Check if already exists
        existing = session.exec(select(AuthenticationRequest).where(AuthenticationRequest.id == req_id)).first()
        
        if not existing and not dry_run:
            req = AuthenticationRequest(
                id=req_id,
                user_id=user_id,
                device_info=device_info if device_info != "unknown" else None,
                ip_address=ip_address if ip_address != "unknown" else None,
                status=status,
                created_at=created_at,
                expires_at=expires_at
            )
            session.add(req)
        
        return not existing
    
    def _import_auth_approval(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 5:
            return False
        
        approved_str, request_id, approver_user_id, approval_status, notes = parts[:5]
        approved_at = datetime.strptime(approved_str, "%B %d %Y at %H:%M")
        notes = notes.replace('\\|', '|')
        
        # Check if already exists
        existing = session.exec(select(AuthApproval).where(
            AuthApproval.request_id == request_id,
            AuthApproval.approver_user_id == approver_user_id
        )).first()
        
        if not existing and not dry_run:
            approval = AuthApproval(
                request_id=request_id,
                approver_user_id=approver_user_id,
                approval_status=approval_status,
                notes=notes or None,
                approved_at=approved_at
            )
            session.add(approval)
        
        return not existing
    
    def _import_auth_audit_log(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 6:
            return False
        
        timestamp_str, user_id, action, ip_address, user_agent, details = parts[:6]
        timestamp = datetime.strptime(timestamp_str, "%B %d %Y at %H:%M")
        user_agent = user_agent.replace('\\|', '|')
        details = details.replace('\\|', '|')
        
        # Check if already exists
        existing = session.exec(select(AuthAuditLog).where(
            AuthAuditLog.user_id == user_id,
            AuthAuditLog.timestamp == timestamp,
            AuthAuditLog.action == action
        )).first()
        
        if not existing and not dry_run:
            audit = AuthAuditLog(
                user_id=user_id,
                action=action,
                ip_address=ip_address if ip_address != "unknown" else None,
                user_agent=user_agent if user_agent != "unknown" else None,
                details=details or None,
                timestamp=timestamp
            )
            session.add(audit)
        
        return not existing
    
    def _import_invite_token(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 6:
            return False
        
        token, created_by_user, usage_count, max_uses, expires_str, used_by_user_id = parts[:6]
        expires_at = datetime.strptime(expires_str, "%B %d %Y at %H:%M")
        max_uses_val = None if max_uses == "unlimited" else int(max_uses)
        
        # Check if already exists
        existing = session.exec(select(InviteToken).where(InviteToken.token == token)).first()
        
        if not existing and not dry_run:
            invite = InviteToken(
                token=token,
                created_by_user=created_by_user,
                usage_count=int(usage_count),
                max_uses=max_uses_val,
                expires_at=expires_at,
                used_by_user_id=used_by_user_id if used_by_user_id != "none" else None
            )
            session.add(invite)
        
        return not existing
    
    def _import_invite_usage(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 5:
            return False
        
        used_str, token_id, used_by_user_id, ip_address, user_agent = parts[:5]
        used_at = datetime.strptime(used_str, "%B %d %Y at %H:%M")
        user_agent = user_agent.replace('\\|', '|')
        
        # Check if already exists
        existing = session.exec(select(InviteTokenUsage).where(
            InviteTokenUsage.token_id == token_id,
            InviteTokenUsage.used_by_user_id == used_by_user_id,
            InviteTokenUsage.used_at == used_at
        )).first()
        
        if not existing and not dry_run:
            usage = InviteTokenUsage(
                token_id=token_id,
                used_by_user_id=used_by_user_id,
                ip_address=ip_address if ip_address != "unknown" else None,
                user_agent=user_agent if user_agent != "unknown" else None,
                used_at=used_at
            )
            session.add(usage)
        
        return not existing
    
    def _import_role(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 6:
            return False
        
        role_id, role_name, description, permissions, created_by, is_system_role = parts[:6]
        
        # Check if already exists
        existing = session.exec(select(Role).where(Role.id == role_id)).first()
        
        if not existing and not dry_run:
            role = Role(
                id=role_id,
                name=role_name,
                description=description or None,
                permissions=permissions,
                created_by=created_by or "system",
                is_system_role=(is_system_role == "yes")
            )
            session.add(role)
        
        return not existing
    
    def _import_user_role(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 6:
            return False
        
        ur_id, granted_str, user_id, role_id, granted_by, expires_str = parts[:6]
        granted_at = datetime.strptime(granted_str, "%B %d %Y at %H:%M")
        expires_at = datetime.strptime(expires_str, "%B %d %Y at %H:%M") if expires_str != "never" else None
        
        # Check if already exists
        existing = session.exec(select(UserRole).where(UserRole.id == ur_id)).first()
        
        if not existing and not dry_run:
            user_role = UserRole(
                id=ur_id,
                user_id=user_id,
                role_id=role_id,
                granted_by=granted_by or "system",
                granted_at=granted_at,
                expires_at=expires_at
            )
            session.add(user_role)
        
        return not existing
    
    def _import_security_log(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 5:
            return False
        
        timestamp_str, event_type, user_id, ip_address, details = parts[:5]
        timestamp = datetime.strptime(timestamp_str, "%B %d %Y at %H:%M")
        
        # Check if already exists (using timestamp and event type as key)
        existing = session.exec(select(SecurityLog).where(
            SecurityLog.created_at == timestamp,
            SecurityLog.event_type == event_type,
            SecurityLog.user_id == (user_id if user_id != "anonymous" else None)
        )).first()
        
        if not existing and not dry_run:
            log = SecurityLog(
                event_type=event_type,
                user_id=user_id if user_id != "anonymous" else None,
                ip_address=ip_address if ip_address != "unknown" else None,
                details=details or None,
                created_at=timestamp
            )
            session.add(log)
        
        return not existing
    
    def _import_changelog_entry(self, session: DBSession, parts: List[str], dry_run: bool) -> bool:
        if len(parts) < 6:
            return False
        
        created_str, version, title, description, category, created_by = parts[:6]
        created_at = datetime.strptime(created_str, "%B %d %Y at %H:%M")
        title = title.replace('\\|', '|')
        description = description.replace('\\|', '|').replace('\\\\n', '\n')
        
        # Check if already exists
        existing = session.exec(select(ChangelogEntry).where(
            ChangelogEntry.version == version,
            ChangelogEntry.title == title
        )).first()
        
        if not existing and not dry_run:
            entry = ChangelogEntry(
                version=version,
                title=title,
                description=description or None,
                category=category or None,
                created_by=created_by or "system",
                created_at=created_at
            )
            session.add(entry)
        
        return not existing
    
    def _print_import_summary(self, dry_run: bool):
        """Print summary of imported data."""
        action = "Would import" if dry_run else "Imported"
        print(f"\n📂 Data {action.lower()} from: {self.archives_dir}/")
        print(f"\n{action} Summary:")
        total_records = 0
        for category, count in self.imported_counts.items():
            print(f"  • {category}: {count} records")
            total_records += count
        print(f"\nTotal: {total_records} records {action.lower()}")


# Convenience function for CLI usage
def import_all_database_data(dry_run: bool = False) -> bool:
    """Import all database data from text archives."""
    service = ImportService()
    return service.import_all(dry_run)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Import all database data from text archives')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without making them')
    args = parser.parse_args()
    
    success = import_all_database_data(args.dry_run)
    sys.exit(0 if success else 1)