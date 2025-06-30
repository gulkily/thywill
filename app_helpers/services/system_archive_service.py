#!/usr/bin/env python3
"""
System Archive Service - Real-time archival of system state data

This service implements a hybrid approach:
- Current state snapshots for easy reading
- Complete event logs for perfect audit trails

Archive Structure:
text_archives/system/
├── current_state/
│   ├── active_sessions.txt     # Current session snapshot
│   ├── active_admins.txt       # Current admin roles
│   ├── active_tokens.txt       # Active invite tokens
│   └── auth_requests.txt       # Pending auth requests
└── event_log/
    ├── session_events_2025_06.txt    # All session changes
    ├── admin_events_2025_06.txt      # Admin role changes
    ├── token_events_2025_06.txt      # Token lifecycle events
    └── auth_events_2025_06.txt       # Auth request events
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from sqlmodel import Session, select
import logging

from models import User, Session as UserSession, InviteToken, AuthenticationRequest, SecurityLog
from .text_archive_service import TextArchiveService

logger = logging.getLogger(__name__)


class SystemArchiveService:
    """Service for archiving system state with hybrid state + event approach"""
    
    def __init__(self, base_dir: str = None):
        self.text_archive = TextArchiveService(base_dir)
        self.base_dir = self.text_archive.base_dir
        self.system_dir = self.base_dir / "system"
        self.current_state_dir = self.system_dir / "current_state"
        self.event_log_dir = self.system_dir / "event_log"
        
        # Ensure directories exist
        self.current_state_dir.mkdir(parents=True, exist_ok=True)
        self.event_log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_session_event(self, event_type: str, session_data: Dict, user_id: int = None):
        """Log session lifecycle event and update current state"""
        try:
            # Log the event
            event_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,  # created, updated, expired, deleted
                'session_data': session_data,
                'user_id': user_id
            }
            
            self._append_to_event_log('session_events', event_data)
            
            # Update current state snapshot
            self._update_sessions_snapshot()
            
            logger.debug(f"Logged session event: {event_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to log session event: {e}")
    
    def log_admin_event(self, event_type: str, user_id: int, admin_data: Dict, changed_by: int = None):
        """Log admin role change event and update current state"""
        try:
            event_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,  # granted, revoked, updated
                'user_id': user_id,
                'admin_data': admin_data,
                'changed_by': changed_by
            }
            
            self._append_to_event_log('admin_events', event_data)
            self._update_admins_snapshot()
            
            logger.info(f"Logged admin event: {event_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to log admin event: {e}")
    
    def log_token_event(self, event_type: str, token_data: Dict, user_id: int = None):
        """Log invite token lifecycle event and update current state"""
        try:
            event_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,  # created, used, expired, revoked
                'token_data': token_data,
                'user_id': user_id
            }
            
            self._append_to_event_log('token_events', event_data)
            self._update_tokens_snapshot()
            
            logger.debug(f"Logged token event: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to log token event: {e}")
    
    def log_auth_request_event(self, event_type: str, request_data: Dict, user_id: int = None):
        """Log authentication request event and update current state"""
        try:
            event_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event_type': event_type,  # created, approved, denied, expired
                'request_data': request_data,
                'user_id': user_id
            }
            
            self._append_to_event_log('auth_events', event_data)
            self._update_auth_requests_snapshot()
            
            logger.debug(f"Logged auth request event: {event_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to log auth request event: {e}")
    
    def _append_to_event_log(self, log_type: str, event_data: Dict):
        """Append event to monthly event log file"""
        now = datetime.now(timezone.utc)
        log_filename = f"{log_type}_{now.strftime('%Y_%m')}.txt"
        log_file = self.event_log_dir / log_filename
        
        # Format event as human-readable text
        timestamp = event_data['timestamp']
        event_type = event_data['event_type']
        
        # Create readable event line
        if log_type == 'session_events':
            session_id = event_data['session_data'].get('id', 'unknown')
            user_id = event_data.get('user_id', 'unknown')
            line = f"{timestamp} - Session {session_id} {event_type} for user {user_id}"
            
        elif log_type == 'admin_events':
            user_id = event_data['user_id']
            changed_by = event_data.get('changed_by', 'system')
            line = f"{timestamp} - Admin role {event_type} for user {user_id} by {changed_by}"
            
        elif log_type == 'token_events':
            token_data = event_data['token_data']
            token_id = token_data.get('id', 'unknown')
            line = f"{timestamp} - Invite token {token_id} {event_type}"
            
        elif log_type == 'auth_events':
            request_data = event_data['request_data']
            request_id = request_data.get('id', 'unknown')
            user_id = event_data.get('user_id', 'unknown')
            line = f"{timestamp} - Auth request {request_id} {event_type} for user {user_id}"
        
        else:
            line = f"{timestamp} - {event_type}: {json.dumps(event_data, default=str)}"
        
        # Append to file
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    
    def _update_sessions_snapshot(self):
        """Update current active sessions snapshot"""
        try:
            from models import engine
            with Session(engine) as session:
                active_sessions = session.exec(
                    select(UserSession).where(UserSession.is_active == True)
                ).all()
                
                # Generate human-readable snapshot
                lines = []
                lines.append(f"# Active Sessions Snapshot")
                lines.append(f"# Generated: {datetime.now(timezone.utc).isoformat()}")
                lines.append(f"# Total active sessions: {len(active_sessions)}")
                lines.append("")
                
                for sess in active_sessions:
                    user = session.get(User, sess.user_id) if sess.user_id else None
                    username = user.display_name if user else "Unknown User"
                    
                    lines.append(f"Session {sess.id}:")
                    lines.append(f"  User: {username} (ID: {sess.user_id})")
                    lines.append(f"  Created: {sess.created_at}")
                    lines.append(f"  Last seen: {sess.last_activity}")
                    lines.append(f"  IP: {sess.ip_address}")
                    lines.append(f"  Device: {sess.device_info or 'Unknown'}")
                    lines.append(f"  Fully authenticated: {sess.is_fully_authenticated}")
                    lines.append("")
                
                # Write to snapshot file
                snapshot_file = self.current_state_dir / "active_sessions.txt"
                snapshot_file.write_text('\n'.join(lines), encoding='utf-8')
                
        except Exception as e:
            logger.error(f"Failed to update sessions snapshot: {e}")
    
    def _update_admins_snapshot(self):
        """Update current admin users snapshot"""
        try:
            from models import engine
            with Session(engine) as session:
                # Get users with admin role (assuming is_admin field exists)
                admin_users = session.exec(
                    select(User).where(User.is_admin == True)
                ).all()
                
                lines = []
                lines.append(f"# Admin Users Snapshot")
                lines.append(f"# Generated: {datetime.now(timezone.utc).isoformat()}")
                lines.append(f"# Total admin users: {len(admin_users)}")
                lines.append("")
                
                for user in admin_users:
                    lines.append(f"Admin User {user.id}:")
                    lines.append(f"  Username: {user.display_name}")
                    lines.append(f"  Joined: {user.created_at}")
                    lines.append("")
                
                snapshot_file = self.current_state_dir / "active_admins.txt"
                snapshot_file.write_text('\n'.join(lines), encoding='utf-8')
                
        except Exception as e:
            logger.error(f"Failed to update admins snapshot: {e}")
    
    def _update_tokens_snapshot(self):
        """Update current active invite tokens snapshot"""
        try:
            from models import engine
            with Session(engine) as session:
                # Get unexpired, unused tokens
                now = datetime.now(timezone.utc)
                active_tokens = session.exec(
                    select(InviteToken).where(
                        InviteToken.used_at.is_(None),
                        InviteToken.expires_at > now
                    )
                ).all()
                
                lines = []
                lines.append(f"# Active Invite Tokens Snapshot")
                lines.append(f"# Generated: {datetime.now(timezone.utc).isoformat()}")
                lines.append(f"# Total active tokens: {len(active_tokens)}")
                lines.append("")
                
                for token in active_tokens:
                    inviter = session.get(User, token.inviter_id) if token.inviter_id else None
                    inviter_name = inviter.display_name if inviter else "Unknown"
                    
                    lines.append(f"Token {token.id}:")
                    lines.append(f"  Token: {token.token}")
                    lines.append(f"  Created by: {inviter_name} (ID: {token.inviter_id})")
                    lines.append(f"  Created: {token.created_at}")
                    lines.append(f"  Expires: {token.expires_at}")
                    lines.append(f"  Max uses: {token.max_uses}")
                    lines.append(f"  Uses remaining: {token.max_uses - token.uses}")
                    lines.append("")
                
                snapshot_file = self.current_state_dir / "active_tokens.txt"
                snapshot_file.write_text('\n'.join(lines), encoding='utf-8')
                
        except Exception as e:
            logger.error(f"Failed to update tokens snapshot: {e}")
    
    def _update_auth_requests_snapshot(self):
        """Update current pending auth requests snapshot"""
        try:
            from models import engine
            with Session(engine) as session:
                # Get pending auth requests
                pending_requests = session.exec(
                    select(AuthenticationRequest).where(
                        AuthenticationRequest.status == 'pending'
                    )
                ).all()
                
                lines = []
                lines.append(f"# Pending Auth Requests Snapshot")
                lines.append(f"# Generated: {datetime.now(timezone.utc).isoformat()}")
                lines.append(f"# Total pending requests: {len(pending_requests)}")
                lines.append("")
                
                for req in pending_requests:
                    user = session.get(User, req.user_id) if req.user_id else None
                    username = user.display_name if user else "Unknown User"
                    
                    lines.append(f"Auth Request {req.id}:")
                    lines.append(f"  User: {username} (ID: {req.user_id})")
                    lines.append(f"  Created: {req.created_at}")
                    lines.append(f"  Expires: {req.expires_at}")
                    lines.append(f"  IP: {req.ip_address}")
                    lines.append(f"  Device: {req.device_info or 'Unknown'}")
                    lines.append(f"  Approval count: {req.approval_count}")
                    lines.append("")
                
                snapshot_file = self.current_state_dir / "auth_requests.txt"
                snapshot_file.write_text('\n'.join(lines), encoding='utf-8')
                
        except Exception as e:
            logger.error(f"Failed to update auth requests snapshot: {e}")
    
    def rebuild_all_snapshots(self):
        """Rebuild all current state snapshots from database"""
        logger.info("Rebuilding all system state snapshots...")
        self._update_sessions_snapshot()
        self._update_admins_snapshot()
        self._update_tokens_snapshot()
        self._update_auth_requests_snapshot()
        logger.info("System state snapshots rebuilt successfully")
    
    def get_system_archive_stats(self) -> Dict[str, Any]:
        """Get statistics about system archives"""
        stats = {
            'system_dir_exists': self.system_dir.exists(),
            'current_state_files': [],
            'event_log_files': [],
            'total_events_by_type': {}
        }
        
        # Check current state files
        if self.current_state_dir.exists():
            stats['current_state_files'] = [
                f.name for f in self.current_state_dir.glob("*.txt")
            ]
        
        # Check event log files and count events
        if self.event_log_dir.exists():
            for log_file in self.event_log_dir.glob("*.txt"):
                stats['event_log_files'].append(log_file.name)
                
                # Count lines (events) in each log file
                try:
                    line_count = len(log_file.read_text(encoding='utf-8').strip().split('\n'))
                    event_type = log_file.stem.split('_')[0]  # Extract type from filename
                    stats['total_events_by_type'][event_type] = stats['total_events_by_type'].get(event_type, 0) + line_count
                except Exception as e:
                    logger.warning(f"Failed to count events in {log_file}: {e}")
        
        return stats