#!/usr/bin/env python3
"""
Export Service for ThyWill

Handles complete database export to unified text archive structure.
Replaces inline scripts with clean, maintainable code.
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


class ExportService:
    """Service for exporting all database data to text archives."""
    
    def __init__(self, archives_dir: str = "text_archives"):
        self.archives_dir = Path(archives_dir)
        self.exported_counts = {}
        
    def export_all(self) -> bool:
        """Export all database data to unified text archive structure."""
        print("📤 Exporting Complete Database to Text Archives")
        print("=" * 50)
        
        # Database operations will proceed - removed PRODUCTION_MODE check
            
        # Ensure archives directory exists
        self.archives_dir.mkdir(exist_ok=True)
        
        try:
            from models import engine
            with DBSession(engine) as session:
                success = True
                
                # Export all data categories
                export_functions = [
                    self._export_prayer_data,
                    self._export_user_data,
                    self._export_user_attributes,
                    self._export_session_data,
                    self._export_authentication_data,
                    self._export_invite_data,
                    self._export_role_data,
                    self._export_security_data,
                    self._export_system_data
                ]
                
                for export_func in export_functions:
                    try:
                        if not export_func(session):
                            success = False
                    except Exception as e:
                        print(f"❌ Error in {export_func.__name__}: {e}")
                        success = False
                
                if success:
                    self._create_export_summary()
                    print("\n✅ Complete database export completed successfully!")
                    self._print_export_summary()
                    return True
                else:
                    print("\n❌ Database export completed with errors")
                    return False
                    
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            return False
    
    def _export_prayer_data(self, session: DBSession) -> bool:
        """Export all prayer-related data to text_archives/prayers/"""
        print("  📄 Exporting prayer data...")
        
        prayers = session.exec(select(Prayer)).all()
        prayer_attributes = session.exec(select(PrayerAttribute)).all()
        prayer_marks = session.exec(select(PrayerMark)).all()
        prayer_skips = session.exec(select(PrayerSkip)).all()
        prayer_activity_logs = session.exec(select(PrayerActivityLog)).all()
        
        if not any([prayers, prayer_attributes, prayer_marks, prayer_skips, prayer_activity_logs]):
            print("    ⚠️  No prayer data found")
            return True
        
        prayer_dir = self.archives_dir / "prayers"
        prayer_dir.mkdir(exist_ok=True)
        
        total_exported = 0
        
        # Export additional prayer data (beyond what's already archived)
        if prayer_attributes:
            self._write_data_file(
                prayer_dir / "prayer_attributes.txt",
                "Prayer Attributes",
                "id|created_at|prayer_id|attribute_name|attribute_value|created_by",
                [(attr.id,
                  attr.created_at.strftime("%B %d %Y at %H:%M"),
                  attr.prayer_id,
                  attr.attribute_name,
                  (attr.attribute_value or "").replace('|', '\\|'),
                  attr.created_by) for attr in prayer_attributes]
            )
            total_exported += len(prayer_attributes)
        
        if prayer_marks:
            self._write_data_file(
                prayer_dir / "prayer_marks.txt", 
                "Prayer Marks",
                "id|created_at|prayer_id|username",
                [(mark.id,
                  mark.created_at.strftime("%B %d %Y at %H:%M"),
                  mark.prayer_id,
                  mark.username) for mark in prayer_marks]
            )
            total_exported += len(prayer_marks)
        
        if prayer_skips:
            self._write_data_file(
                prayer_dir / "prayer_skips.txt",
                "Prayer Skips", 
                "id|created_at|prayer_id|user_id",
                [(skip.id,
                  skip.created_at.strftime("%B %d %Y at %H:%M"),
                  skip.prayer_id,
                  skip.user_id) for skip in prayer_skips]
            )
            total_exported += len(prayer_skips)
        
        if prayer_activity_logs:
            self._write_data_file(
                prayer_dir / "prayer_activity_logs.txt",
                "Prayer Activity Logs",
                "id|created_at|prayer_id|user_id|action|old_value|new_value", 
                [(log.id,
                  log.created_at.strftime("%B %d %Y at %H:%M"),
                  log.prayer_id,
                  log.user_id,
                  log.action,
                  (log.old_value or "").replace('|', '\\|'),
                  (log.new_value or "").replace('|', '\\|')) for log in prayer_activity_logs]
            )
            total_exported += len(prayer_activity_logs)
        
        self.exported_counts['prayer_data'] = total_exported
        print(f"    ✅ Exported {total_exported} prayer-related records")
        return True
    
    def _export_user_data(self, session: DBSession) -> bool:
        """Export all user-related data to text_archives/users/"""
        print("  📄 Exporting user data...")
        
        notification_states = session.exec(select(NotificationState)).all()
        
        if not notification_states:
            print("    ⚠️  No additional user data found")
            return True
        
        users_dir = self.archives_dir / "users"
        users_dir.mkdir(exist_ok=True)
        
        # Export notification states (users themselves are already archived)
        self._write_data_file(
            users_dir / "notification_states.txt",
            "User Notification States",
            "id|created_at|user_id|auth_request_id|notification_type|is_read|read_at",
            [(state.id,
              state.created_at.strftime("%B %d %Y at %H:%M"),
              state.user_id,
              state.auth_request_id,
              state.notification_type,
              "yes" if state.is_read else "no",
              state.read_at.strftime("%B %d %Y at %H:%M") if state.read_at else "never") for state in notification_states]
        )
        
        self.exported_counts['user_data'] = len(notification_states)
        print(f"    ✅ Exported {len(notification_states)} notification states")
        return True
    
    def _export_user_attributes(self, session: DBSession) -> bool:
        """Export user attributes to text_archives/users/user_attributes.txt"""
        print("  📄 Exporting user attributes...")
        
        users = session.exec(select(User)).all()
        
        if not users:
            print("    ⚠️  No users found")
            return True
        
        users_dir = self.archives_dir / "users"
        users_dir.mkdir(exist_ok=True)
        
        # Create user attributes file
        user_attributes_path = users_dir / "user_attributes.txt"
        
        try:
            # Sort users by display_name for consistent output and deduplication
            unique_users = {}
            for user in users:
                unique_users[user.display_name] = user
            
            with open(user_attributes_path, 'w') as f:
                f.write("User Attributes\n\n")
                
                # Export users in sorted order to ensure consistent output
                for username in sorted(unique_users.keys()):
                    user = unique_users[username]
                    f.write(f"username: {username}\n")
                    f.write(f"is_supporter: {str(user.is_supporter).lower()}\n")
                    if user.supporter_since:
                        f.write(f"supporter_since: {user.supporter_since.strftime('%Y-%m-%d')}\n")
                    if user.supporter_type:
                        f.write(f"supporter_type: {user.supporter_type}\n")
                    f.write(f"welcome_message_dismissed: {str(user.welcome_message_dismissed).lower()}\n")
                    f.write("\n")  # Empty line between users
                
            self.exported_counts['user_attributes'] = len(unique_users)
            print(f"    ✅ Exported {len(unique_users)} user attribute records")
            return True
            
        except Exception as e:
            print(f"    ❌ Error exporting user attributes: {e}")
            return False
    
    def _export_session_data(self, session: DBSession) -> bool:
        """Export session data to text_archives/sessions/"""
        print("  📄 Exporting session data...")
        
        sessions = session.exec(select(Session)).all()
        
        if not sessions:
            print("    ⚠️  No session data found")
            return True
        
        sessions_dir = self.archives_dir / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        
        # Group sessions by month
        sessions_by_month = {}
        for sess in sessions:
            month_key = sess.created_at.strftime("%Y_%m")
            if month_key not in sessions_by_month:
                sessions_by_month[month_key] = []
            sessions_by_month[month_key].append(sess)
        
        total_exported = 0
        for month_key, month_sessions in sessions_by_month.items():
            month_date = datetime.strptime(month_key, "%Y_%m")
            file_path = sessions_dir / f"{month_key}_sessions.txt"
            
            self._write_data_file(
                file_path,
                f"Sessions for {month_date.strftime('%B %Y')}",
                "created_at|session_id|username|expires_at|device_info|ip_address|is_fully_authenticated",
                [(sess.created_at.strftime("%B %d %Y at %H:%M"),
                  sess.id,
                  sess.username,
                  sess.expires_at.strftime("%B %d %Y at %H:%M"),
                  sess.device_info or "unknown",
                  sess.ip_address or "unknown",
                  "yes" if sess.is_fully_authenticated else "no") for sess in month_sessions]
            )
            total_exported += len(month_sessions)
        
        self.exported_counts['sessions'] = total_exported
        print(f"    ✅ Exported {total_exported} sessions across {len(sessions_by_month)} monthly files")
        return True
    
    def _export_authentication_data(self, session: DBSession) -> bool:
        """Export authentication data to text_archives/authentication/"""
        print("  📄 Exporting authentication data...")
        
        auth_requests = session.exec(select(AuthenticationRequest)).all()
        auth_approvals = session.exec(select(AuthApproval)).all()
        auth_audit_logs = session.exec(select(AuthAuditLog)).all()
        
        if not any([auth_requests, auth_approvals, auth_audit_logs]):
            print("    ⚠️  No authentication data found")
            return True
        
        auth_dir = self.archives_dir / "authentication"
        auth_dir.mkdir(exist_ok=True)
        
        total_exported = 0
        
        if auth_requests:
            self._write_data_file(
                auth_dir / "auth_requests.txt",
                "Authentication Requests",
                "id|created_at|user_id|device_info|ip_address|status|expires_at",
                [(req.id,
                  req.created_at.strftime("%B %d %Y at %H:%M"),
                  req.user_id,
                  req.device_info or "unknown",
                  req.ip_address or "unknown",
                  req.status,
                  req.expires_at.strftime("%B %d %Y at %H:%M")) for req in auth_requests]
            )
            total_exported += len(auth_requests)
        
        if auth_approvals:
            self._write_data_file(
                auth_dir / "auth_approvals.txt",
                "Authentication Approvals",
                "created_at|auth_request_id|approver_user_id",
                [(approval.created_at.strftime("%B %d %Y at %H:%M"),
                  approval.auth_request_id,
                  approval.approver_user_id) for approval in auth_approvals]
            )
            total_exported += len(auth_approvals)
        
        if auth_audit_logs:
            self._write_data_file(
                auth_dir / "auth_audit_logs.txt",
                "Authentication Audit Logs",
                "created_at|auth_request_id|action|actor_user_id|actor_type|details|ip_address|user_agent",
                [(log.created_at.strftime("%B %d %Y at %H:%M"),
                  log.auth_request_id,
                  log.action,
                  log.actor_user_id or "unknown",
                  log.actor_type or "unknown",
                  (log.details or "").replace('|', '\\|'),
                  log.ip_address or "unknown",
                  (log.user_agent or "unknown").replace('|', '\\|')) for log in auth_audit_logs]
            )
            total_exported += len(auth_audit_logs)
        
        self.exported_counts['authentication'] = total_exported
        print(f"    ✅ Exported {total_exported} authentication records")
        return True
    
    def _export_invite_data(self, session: DBSession) -> bool:
        """Export invite data to text_archives/invites/"""
        print("  📄 Exporting invite data...")
        
        invite_tokens = session.exec(select(InviteToken)).all()
        invite_usage = session.exec(select(InviteTokenUsage)).all()
        
        if not any([invite_tokens, invite_usage]):
            print("    ⚠️  No invite data found")
            return True
        
        invites_dir = self.archives_dir / "invites"
        invites_dir.mkdir(exist_ok=True)
        
        total_exported = 0
        
        if invite_tokens:
            self._write_data_file(
                invites_dir / "invite_tokens.txt",
                "Invite Tokens",
                "token|created_by_user|usage_count|max_uses|expires_at|used_by_user_id",
                [(token.token,
                  token.created_by_user,
                  token.usage_count,
                  token.max_uses or "unlimited",
                  token.expires_at.strftime("%B %d %Y at %H:%M"),
                  token.used_by_user_id or "none") for token in invite_tokens]
            )
            total_exported += len(invite_tokens)
        
        if invite_usage:
            self._write_data_file(
                invites_dir / "invite_token_usage.txt",
                "Invite Token Usage",
                "claimed_at|invite_token_id|user_id|ip_address",
                [(usage.claimed_at.strftime("%B %d %Y at %H:%M"),
                  usage.invite_token_id,
                  usage.user_id,
                  usage.ip_address or "unknown") for usage in invite_usage]
            )
            total_exported += len(invite_usage)
        
        self.exported_counts['invites'] = total_exported
        print(f"    ✅ Exported {total_exported} invite records")
        return True
    
    def _export_role_data(self, session: DBSession) -> bool:
        """Export role data to text_archives/roles/"""
        print("  📄 Exporting role data...")
        
        roles = session.exec(select(Role)).all()
        user_roles = session.exec(select(UserRole)).all()
        
        if not any([roles, user_roles]):
            print("    ⚠️  No role data found")
            return True
        
        roles_dir = self.archives_dir / "roles"
        roles_dir.mkdir(exist_ok=True)
        
        total_exported = 0
        
        if roles:
            self._write_data_file(
                roles_dir / "roles.txt",
                "System Roles",
                "id|role_name|description|permissions|created_by|is_system_role",
                [(role.id,
                  role.name,
                  role.description or "",
                  role.permissions,
                  role.created_by or "system",
                  "yes" if role.is_system_role else "no") for role in roles]
            )
            total_exported += len(roles)
        
        if user_roles:
            self._write_data_file(
                roles_dir / "user_roles.txt",
                "User Role Assignments",
                "id|granted_at|user_id|role_id|granted_by|expires_at",
                [(ur.id,
                  ur.granted_at.strftime("%B %d %Y at %H:%M"),
                  ur.user_id,
                  ur.role_id,
                  ur.granted_by or "system",
                  ur.expires_at.strftime("%B %d %Y at %H:%M") if ur.expires_at else "never") for ur in user_roles]
            )
            total_exported += len(user_roles)
        
        self.exported_counts['roles'] = total_exported
        print(f"    ✅ Exported {total_exported} role records")
        return True
    
    def _export_security_data(self, session: DBSession) -> bool:
        """Export security data to text_archives/security/ (existing location)"""
        print("  📄 Exporting security data...")
        
        security_logs = session.exec(select(SecurityLog)).all()
        
        if not security_logs:
            print("    ⚠️  No security data found")
            return True
        
        security_dir = self.archives_dir / "security"
        security_dir.mkdir(exist_ok=True)
        
        # Group logs by month (following existing pattern)
        logs_by_month = {}
        for log in security_logs:
            month_key = log.created_at.strftime("%Y_%m")
            if month_key not in logs_by_month:
                logs_by_month[month_key] = []
            logs_by_month[month_key].append(log)
        
        total_exported = 0
        for month_key, month_logs in logs_by_month.items():
            month_date = datetime.strptime(month_key, "%Y_%m")
            file_path = security_dir / f"{month_key}_security_events.txt"
            
            self._write_data_file(
                file_path,
                f"Security Events for {month_date.strftime('%B %Y')}",
                "timestamp|event_type|user_id|ip_address|details",
                [(log.created_at.strftime("%B %d %Y at %H:%M"),
                  log.event_type,
                  log.user_id or "anonymous",
                  log.ip_address or "unknown",
                  log.details or "") for log in month_logs]
            )
            total_exported += len(month_logs)
        
        self.exported_counts['security'] = total_exported
        print(f"    ✅ Exported {total_exported} security events across {len(logs_by_month)} monthly files")
        return True
    
    def _export_system_data(self, session: DBSession) -> bool:
        """Export system data to text_archives/system/"""
        print("  📄 Exporting system data...")
        
        changelog_entries = session.exec(select(ChangelogEntry)).all()
        
        if not changelog_entries:
            print("    ⚠️  No system data found")
            return True
        
        system_dir = self.archives_dir / "system"
        system_dir.mkdir(exist_ok=True)
        
        self._write_data_file(
            system_dir / "changelog_entries.txt",
            "System Changelog Entries",
            "created_at|commit_id|original_message|friendly_description|change_type|commit_date",
            [(entry.created_at.strftime("%B %d %Y at %H:%M"),
              entry.commit_id,
              (entry.original_message or "").replace('|', '\\|'),
              (entry.friendly_description or "").replace('|', '\\|').replace('\n', '\\\\n'),
              entry.change_type or "",
              entry.commit_date.strftime("%B %d %Y at %H:%M")) for entry in changelog_entries]
        )
        
        self.exported_counts['system'] = len(changelog_entries)
        print(f"    ✅ Exported {len(changelog_entries)} system records")
        return True
    
    def _write_data_file(self, file_path: Path, title: str, format_line: str, data: List[tuple]):
        """Write data to a text archive file with proper formatting."""
        header = f"{title} (exported {datetime.utcnow().strftime('%B %d %Y at %H:%M')})\n"
        header += f"Format: {format_line}\n\n"
        
        lines = [header]
        for row in data:
            line = "|".join(str(field) for field in row)
            lines.append(line)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _create_export_summary(self):
        """Create export summary file."""
        summary_file = self.archives_dir / "export_summary.txt"
        
        lines = [
            "Complete Database Export Summary",
            f"Exported: {datetime.utcnow().strftime('%B %d %Y at %H:%M')}",
            "",
            "This export includes all database data organized by category:",
        ]
        
        for category, count in self.exported_counts.items():
            lines.append(f"• {category}: {count} records")
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _print_export_summary(self):
        """Print summary of exported data."""
        print(f"\n📂 All data exported to: {self.archives_dir}/")
        print("\nExport Summary:")
        total_records = 0
        for category, count in self.exported_counts.items():
            print(f"  • {category}: {count} records")
            total_records += count
        print(f"\nTotal: {total_records} records exported")


# Convenience function for CLI usage
def export_all_database_data() -> bool:
    """Export all database data to text archives."""
    service = ExportService()
    return service.export_all()


if __name__ == "__main__":
    success = export_all_database_data()
    sys.exit(0 if success else 1)