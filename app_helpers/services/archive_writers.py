"""
Archive Writers Service

This service handles writing comprehensive archive files for complete database reconstruction.
Extends the archive-first philosophy to cover authentication, roles, and system state.

Archive Categories:
- Authentication: Auth requests, approvals, security events, sessions
- Roles: Role definitions, assignments, permission changes
- System: Invite tokens, configuration, feature flags
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from app_helpers.services.text_archive_service import TextArchiveService

logger = logging.getLogger(__name__)

# Import configuration
try:
    from app import TEXT_ARCHIVE_ENABLED, TEXT_ARCHIVE_BASE_DIR
except (ImportError, Exception):
    # Fallback for testing or when app.py can't be imported
    import os
    TEXT_ARCHIVE_ENABLED = os.getenv('TEXT_ARCHIVE_ENABLED', 'false').lower() == 'true'
    TEXT_ARCHIVE_BASE_DIR = os.getenv('TEXT_ARCHIVE_BASE_DIR', '/tmp/test_archives_fallback')


class AuthArchiveWriter:
    """Handles archiving of authentication and security data"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or TEXT_ARCHIVE_BASE_DIR)
        self.enabled = TEXT_ARCHIVE_ENABLED
        
        if self.enabled:
            # Create auth directory structure
            (self.base_dir / "auth").mkdir(parents=True, exist_ok=True)
            (self.base_dir / "auth" / "notifications").mkdir(parents=True, exist_ok=True)
    
    def log_auth_request(self, auth_request: Dict) -> str:
        """Log authentication request to monthly archive"""
        if not self.enabled:
            return ""
        
        now = datetime.now()
        monthly_file = self.base_dir / "auth" / f"{now.year}_{now.month:02d}_auth_requests.txt"
        
        # Create header if new file
        if not monthly_file.exists():
            header = f"Authentication Requests for {now.strftime('%B %Y')}\n"
            header += "Format: timestamp|user_id|device_info|ip_address|status|details\n\n"
            self._write_file_atomic(str(monthly_file), header)
        
        # Format auth request line
        timestamp = auth_request.get('created_at', now).isoformat()
        user_id = auth_request.get('user_id', '')
        device_info = auth_request.get('device_info', '').replace('|', '_')
        ip_address = auth_request.get('ip_address', '')
        status = auth_request.get('status', 'pending')
        
        # Add expiration and other details
        details = []
        if auth_request.get('expires_at'):
            details.append(f"expires_{auth_request['expires_at'].isoformat()}")
        if auth_request.get('verification_code'):
            details.append("verification_required")
        
        request_line = f"{timestamp}|{user_id}|{device_info}|{ip_address}|{status}|{','.join(details)}"
        
        self._append_to_file(str(monthly_file), request_line)
        logger.info(f"Logged auth request for user {user_id}")
        
        return str(monthly_file)
    
    def log_auth_approval(self, approval: Dict) -> str:
        """Log authentication approval to monthly archive"""
        if not self.enabled:
            return ""
        
        now = datetime.now()
        monthly_file = self.base_dir / "auth" / f"{now.year}_{now.month:02d}_auth_approvals.txt"
        
        # Create header if new file
        if not monthly_file.exists():
            header = f"Authentication Approvals for {now.strftime('%B %Y')}\n"
            header += "Format: timestamp|auth_request_id|approver_user_id|action|details\n\n"
            self._write_file_atomic(str(monthly_file), header)
        
        # Format approval line
        timestamp = approval.get('created_at', now).isoformat()
        auth_request_id = approval.get('auth_request_id', '')
        approver_id = approval.get('approver_user_id', '')
        action = approval.get('action', 'approved')  # approved, rejected
        details = approval.get('details', '')
        
        approval_line = f"{timestamp}|{auth_request_id}|{approver_id}|{action}|{details}"
        
        self._append_to_file(str(monthly_file), approval_line)
        logger.info(f"Logged auth approval by user {approver_id}")
        
        return str(monthly_file)
    
    def log_security_event(self, event: Dict) -> str:
        """Log security event to monthly archive"""
        if not self.enabled:
            return ""
        
        now = datetime.now()
        monthly_file = self.base_dir / "auth" / f"{now.year}_{now.month:02d}_security_events.txt"
        
        # Create header if new file
        if not monthly_file.exists():
            header = f"Security Events for {now.strftime('%B %Y')}\n"
            header += "Format: timestamp|event_type|user_id|ip_address|user_agent|details\n\n"
            self._write_file_atomic(str(monthly_file), header)
        
        # Format security event line
        timestamp = event.get('created_at', now).isoformat()
        event_type = event.get('event_type', '')
        user_id = event.get('user_id', '')
        ip_address = event.get('ip_address', '')
        user_agent = event.get('user_agent', '').replace('|', '_')
        details = event.get('details', '').replace('|', '_')
        
        event_line = f"{timestamp}|{event_type}|{user_id}|{ip_address}|{user_agent}|{details}"
        
        self._append_to_file(str(monthly_file), event_line)
        logger.info(f"Logged security event: {event_type}")
        
        return str(monthly_file)
    
    def snapshot_sessions(self, sessions: List[Dict]) -> str:
        """Create daily snapshot of active sessions"""
        if not self.enabled:
            return ""
        
        now = datetime.now()
        daily_file = self.base_dir / "auth" / f"{now.year}_{now.month:02d}_{now.day:02d}_sessions_snapshot.txt"
        
        # Build session snapshot content
        content = []
        content.append(f"Session Snapshot for {now.strftime('%B %d, %Y at %H:%M')}")
        content.append("Format: session_id|user_id|created_at|expires_at|device_info|ip_address|is_fully_authenticated")
        content.append("")
        
        for session in sessions:
            session_line = f"{session.get('id', '')}|{session.get('user_id', '')}|{session.get('created_at', '').isoformat() if session.get('created_at') else ''}|{session.get('expires_at', '').isoformat() if session.get('expires_at') else ''}|{session.get('device_info', '').replace('|', '_')}|{session.get('ip_address', '')}|{session.get('is_fully_authenticated', True)}"
            content.append(session_line)
        
        content.append("")
        content.append(f"Total active sessions: {len(sessions)}")
        
        self._write_file_atomic(str(daily_file), '\n'.join(content))
        logger.info(f"Created session snapshot with {len(sessions)} sessions")
        
        return str(daily_file)
    
    def log_notification_event(self, notification: Dict) -> str:
        """Log notification state change to monthly archive"""
        if not self.enabled:
            return ""
        
        now = datetime.now()
        monthly_file = self.base_dir / "auth" / "notifications" / f"{now.year}_{now.month:02d}_notifications.txt"
        
        # Create header if new file
        if not monthly_file.exists():
            header = f"Notification Events for {now.strftime('%B %Y')}\n"
            header += "Format: timestamp|user_id|auth_request_id|notification_type|action|details\n\n"
            self._write_file_atomic(str(monthly_file), header)
        
        # Format notification line
        timestamp = notification.get('timestamp', now).isoformat()
        user_id = notification.get('user_id', '')
        auth_request_id = notification.get('auth_request_id', '')
        notification_type = notification.get('notification_type', 'auth_request')
        action = notification.get('action', 'created')  # created, read, verified
        details = notification.get('details', '')
        
        notification_line = f"{timestamp}|{user_id}|{auth_request_id}|{notification_type}|{action}|{details}"
        
        self._append_to_file(str(monthly_file), notification_line)
        logger.info(f"Logged notification event for user {user_id}")
        
        return str(monthly_file)
    
    def _write_file_atomic(self, file_path: str, content: str):
        """Write file atomically using temporary file and rename"""
        temp_path = file_path + '.tmp'
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            
            os.rename(temp_path, file_path)
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    
    def _append_to_file(self, file_path: str, content: str):
        """Thread-safe append operation"""
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content + '\n')
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            logger.error(f"Failed to append to auth archive {file_path}: {e}")


class RoleArchiveWriter:
    """Handles archiving of role and permission data"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or TEXT_ARCHIVE_BASE_DIR)
        self.enabled = TEXT_ARCHIVE_ENABLED
        
        if self.enabled:
            # Create roles directory structure
            (self.base_dir / "roles").mkdir(parents=True, exist_ok=True)
    
    def update_role_definitions(self, roles: List[Dict]) -> str:
        """Update the role definitions archive file"""
        if not self.enabled:
            return ""
        
        definitions_file = self.base_dir / "roles" / "role_definitions.txt"
        
        # Build role definitions content
        content = []
        content.append(f"Role Definitions - Updated {datetime.now().strftime('%B %d, %Y at %H:%M')}")
        content.append("Format: role_name|description|permissions_json|is_system_role|created_by")
        content.append("")
        
        for role in roles:
            permissions_json = json.dumps(role.get('permissions', []))
            role_line = f"{role.get('name', '')}|{role.get('description', '').replace('|', '_')}|{permissions_json}|{role.get('is_system_role', False)}|{role.get('created_by', '')}"
            content.append(role_line)
        
        content.append("")
        content.append(f"Total roles: {len(roles)}")
        
        self._write_file_atomic(str(definitions_file), '\n'.join(content))
        logger.info(f"Updated role definitions with {len(roles)} roles")
        
        return str(definitions_file)
    
    def log_role_assignment(self, assignment: Dict) -> str:
        """Log role assignment to monthly archive"""
        if not self.enabled:
            return ""
        
        now = datetime.now()
        monthly_file = self.base_dir / "roles" / f"{now.year}_{now.month:02d}_role_assignments.txt"
        
        # Create header if new file
        if not monthly_file.exists():
            header = f"Role Assignments for {now.strftime('%B %Y')}\n"
            header += "Format: timestamp|user_id|role_name|action|granted_by|expires_at|details\n\n"
            self._write_file_atomic(str(monthly_file), header)
        
        # Format assignment line
        timestamp = assignment.get('granted_at', now).isoformat()
        user_id = assignment.get('user_id', '')
        role_name = assignment.get('role_name', '')
        action = assignment.get('action', 'assigned')  # assigned, removed, expired
        granted_by = assignment.get('granted_by', '')
        expires_at = assignment.get('expires_at', '').isoformat() if assignment.get('expires_at') else ''
        details = assignment.get('details', '')
        
        assignment_line = f"{timestamp}|{user_id}|{role_name}|{action}|{granted_by}|{expires_at}|{details}"
        
        self._append_to_file(str(monthly_file), assignment_line)
        logger.info(f"Logged role assignment: {role_name} to user {user_id}")
        
        return str(monthly_file)
    
    def log_role_change(self, change_event: Dict) -> str:
        """Log role system change to history file"""
        if not self.enabled:
            return ""
        
        history_file = self.base_dir / "roles" / "role_history.txt"
        
        # Create header if new file
        if not history_file.exists():
            header = "Role System History\n"
            header += "Format: timestamp|change_type|role_name|changed_by|old_value|new_value|details\n\n"
            self._write_file_atomic(str(history_file), header)
        
        # Format change line
        timestamp = change_event.get('timestamp', datetime.now()).isoformat()
        change_type = change_event.get('change_type', '')  # created, modified, deleted
        role_name = change_event.get('role_name', '')
        changed_by = change_event.get('changed_by', '')
        old_value = change_event.get('old_value', '').replace('|', '_')
        new_value = change_event.get('new_value', '').replace('|', '_')
        details = change_event.get('details', '').replace('|', '_')
        
        change_line = f"{timestamp}|{change_type}|{role_name}|{changed_by}|{old_value}|{new_value}|{details}"
        
        self._append_to_file(str(history_file), change_line)
        logger.info(f"Logged role change: {change_type} for {role_name}")
        
        return str(history_file)
    
    def _write_file_atomic(self, file_path: str, content: str):
        """Write file atomically using temporary file and rename"""
        temp_path = file_path + '.tmp'
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            
            os.rename(temp_path, file_path)
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    
    def _append_to_file(self, file_path: str, content: str):
        """Thread-safe append operation"""
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content + '\n')
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            logger.error(f"Failed to append to role archive {file_path}: {e}")


class SystemArchiveWriter:
    """Handles archiving of system state and configuration"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or TEXT_ARCHIVE_BASE_DIR)
        self.enabled = TEXT_ARCHIVE_ENABLED
        
        if self.enabled:
            # Create system directory structure
            (self.base_dir / "system").mkdir(parents=True, exist_ok=True)
    
    def update_invite_tokens(self, tokens: List[Dict]) -> str:
        """Update active invite tokens archive"""
        if not self.enabled:
            return ""
        
        tokens_file = self.base_dir / "system" / "invite_tokens.txt"
        
        # Build tokens content
        content = []
        content.append(f"Active Invite Tokens - Updated {datetime.now().strftime('%B %d, %Y at %H:%M')}")
        content.append("Format: token|created_by_user|expires_at|used|used_by_user_id|created_at")
        content.append("")
        
        active_tokens = [t for t in tokens if not t.get('used', False)]
        expired_tokens = [t for t in tokens if t.get('expires_at') and t['expires_at'] < datetime.now()]
        
        content.append("ACTIVE TOKENS:")
        for token in active_tokens:
            if token.get('expires_at') and token['expires_at'] > datetime.now():
                token_line = f"{token.get('token', '')}|{token.get('created_by_user', '')}|{token.get('expires_at', '').isoformat() if token.get('expires_at') else ''}|{token.get('used', False)}|{token.get('used_by_user_id', '')}|{token.get('created_at', '').isoformat() if token.get('created_at') else ''}"
                content.append(token_line)
        
        content.append("")
        content.append("RECENTLY EXPIRED TOKENS:")
        for token in expired_tokens[-10:]:  # Last 10 expired tokens
            token_line = f"{token.get('token', '')}|{token.get('created_by_user', '')}|{token.get('expires_at', '').isoformat() if token.get('expires_at') else ''}|{token.get('used', False)}|{token.get('used_by_user_id', '')}|{token.get('created_at', '').isoformat() if token.get('created_at') else ''}"
            content.append(token_line)
        
        content.append("")
        content.append(f"Active tokens: {len(active_tokens)}")
        content.append(f"Total tokens: {len(tokens)}")
        
        self._write_file_atomic(str(tokens_file), '\n'.join(content))
        logger.info(f"Updated invite tokens archive with {len(active_tokens)} active tokens")
        
        return str(tokens_file)
    
    def snapshot_system_config(self, config: Dict) -> str:
        """Create system configuration snapshot"""
        if not self.enabled:
            return ""
        
        config_file = self.base_dir / "system" / "system_config.txt"
        
        # Build config content
        content = []
        content.append(f"System Configuration - Snapshot {datetime.now().strftime('%B %d, %Y at %H:%M')}")
        content.append("Format: key=value")
        content.append("")
        
        # Sort config keys for consistency
        for key in sorted(config.keys()):
            value = config[key]
            # Don't include sensitive values in plain text
            if 'secret' in key.lower() or 'key' in key.lower() or 'password' in key.lower():
                value = '[REDACTED]'
            content.append(f"{key}={value}")
        
        content.append("")
        content.append(f"Configuration items: {len(config)}")
        
        self._write_file_atomic(str(config_file), '\n'.join(content))
        logger.info("Created system configuration snapshot")
        
        return str(config_file)
    
    def log_feature_flag_change(self, flag: str, value: Any, changed_by: str = None) -> str:
        """Log feature flag change"""
        if not self.enabled:
            return ""
        
        now = datetime.now()
        flags_file = self.base_dir / "system" / f"{now.year}_{now.month:02d}_feature_flags.txt"
        
        # Create header if new file
        if not flags_file.exists():
            header = f"Feature Flag Changes for {now.strftime('%B %Y')}\n"
            header += "Format: timestamp|flag_name|new_value|changed_by|details\n\n"
            self._write_file_atomic(str(flags_file), header)
        
        # Format flag change line
        timestamp = now.isoformat()
        changed_by = changed_by or 'system'
        details = f"flag_changed"
        
        flag_line = f"{timestamp}|{flag}|{value}|{changed_by}|{details}"
        
        self._append_to_file(str(flags_file), flag_line)
        logger.info(f"Logged feature flag change: {flag} = {value}")
        
        return str(flags_file)
    
    def log_invite_usage(self, token: str, used_by: str, created_by: str) -> str:
        """Log invite token usage"""
        if not self.enabled:
            return ""
        
        now = datetime.now()
        usage_file = self.base_dir / "system" / f"{now.year}_{now.month:02d}_invite_usage.txt"
        
        # Create header if new file
        if not usage_file.exists():
            header = f"Invite Token Usage for {now.strftime('%B %Y')}\n"
            header += "Format: timestamp|token|used_by_user|created_by_user|action\n\n"
            self._write_file_atomic(str(usage_file), header)
        
        # Format usage line
        timestamp = now.isoformat()
        action = "token_used"
        
        usage_line = f"{timestamp}|{token}|{used_by}|{created_by}|{action}"
        
        self._append_to_file(str(usage_file), usage_line)
        logger.info(f"Logged invite token usage by {used_by}")
        
        return str(usage_file)
    
    def _write_file_atomic(self, file_path: str, content: str):
        """Write file atomically using temporary file and rename"""
        temp_path = file_path + '.tmp'
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            
            os.rename(temp_path, file_path)
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    
    def _append_to_file(self, file_path: str, content: str):
        """Thread-safe append operation"""
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content + '\n')
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            logger.error(f"Failed to append to system archive {file_path}: {e}")


# Global instances for use throughout the application
auth_archive_writer = AuthArchiveWriter()
role_archive_writer = RoleArchiveWriter()
system_archive_writer = SystemArchiveWriter()