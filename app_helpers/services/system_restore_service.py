#!/usr/bin/env python3
"""
System Restore Service - Restore system state from text archives

This service restores system state from the hybrid archive approach:
- Reads current state snapshots for quick restoration
- Can rebuild from event logs for complete recovery
- Handles graceful degradation if some archives are missing

Restoration Priority:
1. Current state snapshots (fastest)
2. Event log reconstruction (complete but slower)
3. Partial restoration with warnings
"""

import os
import re
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from sqlmodel import Session, select
import logging

from models import engine, User, Session as UserSession, InviteToken, AuthenticationRequest
from .system_archive_service import SystemArchiveService

logger = logging.getLogger(__name__)


class SystemRestoreService:
    """Service for restoring system state from text archives"""
    
    def __init__(self, base_dir: str = None):
        self.archive_service = SystemArchiveService(base_dir)
        self.system_dir = self.archive_service.system_dir
        self.current_state_dir = self.archive_service.current_state_dir
        self.event_log_dir = self.archive_service.event_log_dir
    
    def restore_all_system_state(self, dry_run: bool = False) -> Dict[str, Any]:
        """Restore all system state from archives"""
        results = {
            'sessions_restored': 0,
            'admins_restored': 0,
            'tokens_restored': 0,
            'auth_requests_restored': 0,
            'errors': [],
            'warnings': [],
            'dry_run': dry_run
        }
        
        logger.info(f"Starting system state restoration (dry_run={dry_run})")
        
        try:
            # Restore sessions
            session_result = self.restore_sessions(dry_run=dry_run)
            results['sessions_restored'] = session_result.get('restored_count', 0)
            if session_result.get('errors'):
                results['errors'].extend(session_result['errors'])
            if session_result.get('warnings'):
                results['warnings'].extend(session_result['warnings'])
            
            # Restore admin roles
            admin_result = self.restore_admin_roles(dry_run=dry_run)
            results['admins_restored'] = admin_result.get('restored_count', 0)
            if admin_result.get('errors'):
                results['errors'].extend(admin_result['errors'])
            
            # Restore invite tokens
            token_result = self.restore_invite_tokens(dry_run=dry_run)
            results['tokens_restored'] = token_result.get('restored_count', 0)
            if token_result.get('errors'):
                results['errors'].extend(token_result['errors'])
            
            # Restore auth requests
            auth_result = self.restore_auth_requests(dry_run=dry_run)
            results['auth_requests_restored'] = auth_result.get('restored_count', 0)
            if auth_result.get('errors'):
                results['errors'].extend(auth_result['errors'])
            
            logger.info(f"System state restoration completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"System state restoration failed: {e}")
            results['errors'].append(f"Global restoration error: {str(e)}")
            return results
    
    def restore_sessions(self, dry_run: bool = False) -> Dict[str, Any]:
        """Restore active sessions from archives"""
        result = {'restored_count': 0, 'errors': [], 'warnings': []}
        
        sessions_file = self.current_state_dir / "active_sessions.txt"
        if not sessions_file.exists():
            result['warnings'].append("No active sessions snapshot found")
            return result
        
        try:
            content = sessions_file.read_text(encoding='utf-8')
            sessions_data = self._parse_sessions_snapshot(content)
            
            if dry_run:
                result['restored_count'] = len(sessions_data)
                logger.info(f"Would restore {len(sessions_data)} sessions")
                return result
            
            # Restore sessions to database
            with Session(engine) as db_session:
                for session_info in sessions_data:
                    try:
                        # Check if user exists
                        user = db_session.get(User, session_info['user_id'])
                        if not user:
                            result['warnings'].append(f"User {session_info['user_id']} not found, skipping session")
                            continue
                        
                        # Check if session already exists
                        existing_session = db_session.get(UserSession, session_info['session_id'])
                        if existing_session:
                            result['warnings'].append(f"Session {session_info['session_id']} already exists, skipping")
                            continue
                        
                        # Create new session
                        new_session = UserSession(
                            id=session_info['session_id'],
                            user_id=session_info['user_id'],
                            created_at=session_info['created_at'],
                            last_activity=session_info['last_activity'],
                            ip_address=session_info['ip_address'],
                            device_info=session_info['device_info'],
                            is_fully_authenticated=session_info['is_fully_authenticated'],
                            is_active=True
                        )
                        
                        db_session.add(new_session)
                        result['restored_count'] += 1
                        
                    except Exception as e:
                        result['errors'].append(f"Failed to restore session {session_info.get('session_id')}: {str(e)}")
                
                db_session.commit()
                logger.info(f"Restored {result['restored_count']} sessions")
            
        except Exception as e:
            result['errors'].append(f"Failed to restore sessions: {str(e)}")
        
        return result
    
    def restore_admin_roles(self, dry_run: bool = False) -> Dict[str, Any]:
        """Restore admin role assignments from archives"""
        result = {'restored_count': 0, 'errors': [], 'warnings': []}
        
        admins_file = self.current_state_dir / "active_admins.txt"
        if not admins_file.exists():
            result['warnings'].append("No admin users snapshot found")
            return result
        
        try:
            content = admins_file.read_text(encoding='utf-8')
            admin_data = self._parse_admins_snapshot(content)
            
            if dry_run:
                result['restored_count'] = len(admin_data)
                logger.info(f"Would restore {len(admin_data)} admin roles")
                return result
            
            # Restore admin roles to database
            with Session(engine) as db_session:
                for admin_info in admin_data:
                    try:
                        user = db_session.get(User, admin_info['user_id'])
                        if not user:
                            result['warnings'].append(f"User {admin_info['user_id']} not found, skipping admin role")
                            continue
                        
                        if user.is_admin:
                            result['warnings'].append(f"User {admin_info['username']} already has admin role")
                            continue
                        
                        # Grant admin role
                        user.is_admin = True
                        result['restored_count'] += 1
                        
                    except Exception as e:
                        result['errors'].append(f"Failed to restore admin role for {admin_info.get('username')}: {str(e)}")
                
                db_session.commit()
                logger.info(f"Restored {result['restored_count']} admin roles")
            
        except Exception as e:
            result['errors'].append(f"Failed to restore admin roles: {str(e)}")
        
        return result
    
    def restore_invite_tokens(self, dry_run: bool = False) -> Dict[str, Any]:
        """Restore active invite tokens from archives"""
        result = {'restored_count': 0, 'errors': [], 'warnings': []}
        
        tokens_file = self.current_state_dir / "active_tokens.txt"
        if not tokens_file.exists():
            result['warnings'].append("No active tokens snapshot found")
            return result
        
        try:
            content = tokens_file.read_text(encoding='utf-8')
            tokens_data = self._parse_tokens_snapshot(content)
            
            if dry_run:
                result['restored_count'] = len(tokens_data)
                logger.info(f"Would restore {len(tokens_data)} invite tokens")
                return result
            
            # Restore tokens to database
            with Session(engine) as db_session:
                for token_info in tokens_data:
                    try:
                        # Check if inviter exists
                        inviter = db_session.get(User, token_info['inviter_id'])
                        if not inviter:
                            result['warnings'].append(f"Inviter {token_info['inviter_id']} not found, skipping token")
                            continue
                        
                        # Check if token already exists
                        existing_token = db_session.exec(
                            select(InviteToken).where(InviteToken.token == token_info['token'])
                        ).first()
                        if existing_token:
                            result['warnings'].append(f"Token {token_info['token']} already exists, skipping")
                            continue
                        
                        # Create new token
                        new_token = InviteToken(
                            id=token_info['token_id'],
                            token=token_info['token'],
                            inviter_id=token_info['inviter_id'],
                            created_at=token_info['created_at'],
                            expires_at=token_info['expires_at'],
                            max_uses=token_info['max_uses'],
                            uses=token_info['uses']
                        )
                        
                        db_session.add(new_token)
                        result['restored_count'] += 1
                        
                    except Exception as e:
                        result['errors'].append(f"Failed to restore token {token_info.get('token')}: {str(e)}")
                
                db_session.commit()
                logger.info(f"Restored {result['restored_count']} invite tokens")
            
        except Exception as e:
            result['errors'].append(f"Failed to restore invite tokens: {str(e)}")
        
        return result
    
    def restore_auth_requests(self, dry_run: bool = False) -> Dict[str, Any]:
        """Restore pending auth requests from archives"""
        result = {'restored_count': 0, 'errors': [], 'warnings': []}
        
        auth_file = self.current_state_dir / "auth_requests.txt"
        if not auth_file.exists():
            result['warnings'].append("No auth requests snapshot found")
            return result
        
        try:
            content = auth_file.read_text(encoding='utf-8')
            auth_data = self._parse_auth_requests_snapshot(content)
            
            if dry_run:
                result['restored_count'] = len(auth_data)
                logger.info(f"Would restore {len(auth_data)} auth requests")
                return result
            
            # Restore auth requests to database
            with Session(engine) as db_session:
                for auth_info in auth_data:
                    try:
                        # Check if user exists
                        user = db_session.get(User, auth_info['user_id'])
                        if not user:
                            result['warnings'].append(f"User {auth_info['user_id']} not found, skipping auth request")
                            continue
                        
                        # Check if request already exists
                        existing_request = db_session.get(AuthenticationRequest, auth_info['request_id'])
                        if existing_request:
                            result['warnings'].append(f"Auth request {auth_info['request_id']} already exists, skipping")
                            continue
                        
                        # Create new auth request
                        new_request = AuthenticationRequest(
                            id=auth_info['request_id'],
                            user_id=auth_info['user_id'],
                            created_at=auth_info['created_at'],
                            expires_at=auth_info['expires_at'],
                            ip_address=auth_info['ip_address'],
                            device_info=auth_info['device_info'],
                            approval_count=auth_info['approval_count'],
                            status='pending'
                        )
                        
                        db_session.add(new_request)
                        result['restored_count'] += 1
                        
                    except Exception as e:
                        result['errors'].append(f"Failed to restore auth request {auth_info.get('request_id')}: {str(e)}")
                
                db_session.commit()
                logger.info(f"Restored {result['restored_count']} auth requests")
            
        except Exception as e:
            result['errors'].append(f"Failed to restore auth requests: {str(e)}")
        
        return result
    
    def _parse_sessions_snapshot(self, content: str) -> List[Dict]:
        """Parse sessions snapshot into structured data"""
        sessions = []
        current_session = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('Session '):
                if current_session:
                    sessions.append(current_session)
                session_id = line.split('Session ')[1].rstrip(':')
                current_session = {'session_id': session_id}
            
            elif current_session and line.startswith('  '):
                key_value = line[2:].split(': ', 1)
                if len(key_value) == 2:
                    key, value = key_value
                    
                    if key == 'User':
                        # Extract user ID from "Username (ID: 123)"
                        user_match = re.search(r'\(ID: (\d+)\)', value)
                        if user_match:
                            current_session['user_id'] = int(user_match.group(1))
                    elif key in ['Created', 'Last seen']:
                        current_session[key.lower().replace(' ', '_')] = value
                    elif key == 'IP':
                        current_session['ip_address'] = value
                    elif key == 'Device':
                        current_session['device_info'] = value if value != 'Unknown' else None
                    elif key == 'Fully authenticated':
                        current_session['is_fully_authenticated'] = value.lower() == 'true'
        
        if current_session:
            sessions.append(current_session)
        
        return sessions
    
    def _parse_admins_snapshot(self, content: str) -> List[Dict]:
        """Parse admin snapshot into structured data"""
        admins = []
        current_admin = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('Admin User '):
                if current_admin:
                    admins.append(current_admin)
                user_id = int(line.split('Admin User ')[1].rstrip(':'))
                current_admin = {'user_id': user_id}
            
            elif current_admin and line.startswith('  '):
                key_value = line[2:].split(': ', 1)
                if len(key_value) == 2:
                    key, value = key_value
                    if key == 'Username':
                        current_admin['username'] = value
                    elif key == 'Joined':
                        current_admin['joined_at'] = value
        
        if current_admin:
            admins.append(current_admin)
        
        return admins
    
    def _parse_tokens_snapshot(self, content: str) -> List[Dict]:
        """Parse tokens snapshot into structured data"""
        tokens = []
        current_token = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('Token '):
                if current_token:
                    tokens.append(current_token)
                token_id = int(line.split('Token ')[1].rstrip(':'))
                current_token = {'token_id': token_id}
            
            elif current_token and line.startswith('  '):
                key_value = line[2:].split(': ', 1)
                if len(key_value) == 2:
                    key, value = key_value
                    
                    if key == 'Token':
                        current_token['token'] = value
                    elif key == 'Created by':
                        # Extract inviter ID from "Username (ID: 123)"
                        inviter_match = re.search(r'\(ID: (\d+)\)', value)
                        if inviter_match:
                            current_token['inviter_id'] = int(inviter_match.group(1))
                    elif key in ['Created', 'Expires']:
                        current_token[key.lower() + '_at'] = value
                    elif key == 'Max uses':
                        current_token['max_uses'] = int(value)
                    elif key == 'Uses remaining':
                        remaining = int(value)
                        max_uses = current_token.get('max_uses', 0)
                        current_token['uses'] = max_uses - remaining
        
        if current_token:
            tokens.append(current_token)
        
        return tokens
    
    def _parse_auth_requests_snapshot(self, content: str) -> List[Dict]:
        """Parse auth requests snapshot into structured data"""
        requests = []
        current_request = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('Auth Request '):
                if current_request:
                    requests.append(current_request)
                request_id = int(line.split('Auth Request ')[1].rstrip(':'))
                current_request = {'request_id': request_id}
            
            elif current_request and line.startswith('  '):
                key_value = line[2:].split(': ', 1)
                if len(key_value) == 2:
                    key, value = key_value
                    
                    if key == 'User':
                        # Extract user ID from "Username (ID: 123)"
                        user_match = re.search(r'\(ID: (\d+)\)', value)
                        if user_match:
                            current_request['user_id'] = int(user_match.group(1))
                    elif key in ['Created', 'Expires']:
                        current_request[key.lower() + '_at'] = value
                    elif key == 'IP':
                        current_request['ip_address'] = value
                    elif key == 'Device':
                        current_request['device_info'] = value if value != 'Unknown' else None
                    elif key == 'Approval count':
                        current_request['approval_count'] = int(value)
        
        if current_request:
            requests.append(current_request)
        
        return requests