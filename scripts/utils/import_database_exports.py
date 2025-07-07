#!/usr/bin/env python3
"""
Import Database Exports from Text Archives

This script imports all database exports created by the export-all command.
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Add current directory to path
sys.path.append('.')

# Import database models and session
from models import *
from sqlmodel import Session as DBSession, select

def import_sessions_from_text_archive(session: DBSession, archives_dir: str, dry_run: bool = False) -> bool:
    """Import sessions from text archive files."""
    print(f"  📄 {'Checking' if dry_run else 'Importing'} sessions...")
    
    session_dir = Path(archives_dir) / "database_exports" / "sessions"
    if not session_dir.exists():
        print(f"    ⚠️  No sessions directory found")
        return True
    
    # Find all session files
    session_files = list(session_dir.glob("*_sessions.txt"))
    if not session_files:
        print(f"    ⚠️  No session files found")
        return True
    
    total_sessions = 0
    imported_count = 0
    
    from models import Session as SessionModel
    
    for file_path in session_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Skip header lines and empty lines
        data_lines = [line.strip() for line in lines[3:] if line.strip()]
        
        for line in data_lines:
            total_sessions += 1
            if '|' not in line:
                continue
                
            parts = line.split('|')
            if len(parts) != 7:
                continue
            
            timestamp_str, session_id, username, expires_str, device, ip, auth_str = parts
            
            if not dry_run:
                # Check if session already exists
                existing = session.exec(select(SessionModel).where(SessionModel.id == session_id)).first()
                if existing:
                    continue  # Skip duplicates
                
                # Parse timestamps
                try:
                    created_at = datetime.strptime(timestamp_str, "%B %d %Y at %H:%M")
                    expires_at = datetime.strptime(expires_str, "%B %d %Y at %H:%M")
                except ValueError:
                    continue  # Skip malformed dates
                
                # Create session record
                new_session = SessionModel(
                    id=session_id,
                    username=username,
                    created_at=created_at,
                    expires_at=expires_at,
                    device_info=device if device != "unknown" else None,
                    ip_address=ip if ip != "unknown" else None,
                    is_fully_authenticated=(auth_str == "yes")
                )
                session.add(new_session)
                imported_count += 1
            else:
                imported_count += 1
    
    if not dry_run and imported_count > 0:
        session.commit()
    
    if dry_run:
        print(f"    ✅ Would import {imported_count} of {total_sessions} sessions")
    else:
        print(f"    ✅ Imported {imported_count} of {total_sessions} sessions")
    return True

def import_invite_tokens_from_text_archive(session: DBSession, archives_dir: str, dry_run: bool = False) -> bool:
    """Import invite tokens from text archive."""
    print(f"  📄 {'Checking' if dry_run else 'Importing'} invite tokens...")
    
    invite_file = Path(archives_dir) / "database_exports" / "invites" / "invite_tokens.txt"
    if not invite_file.exists():
        print(f"    ⚠️  No invite tokens file found")
        return True
    
    with open(invite_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Skip header lines and empty lines
    data_lines = [line.strip() for line in lines[3:] if line.strip()]
    
    imported_count = 0
    
    for line in data_lines:
        if '|' not in line:
            continue
            
        parts = line.split('|')
        if len(parts) != 6:
            continue
        
        token, created_by, usage_count_str, max_uses_str, expires_str, used_by = parts
        
        if not dry_run:
            # Check if token already exists
            existing = session.exec(select(InviteToken).where(InviteToken.token == token)).first()
            if existing:
                continue  # Skip duplicates
            
            # Parse data
            try:
                usage_count = int(usage_count_str)
                max_uses = int(max_uses_str) if max_uses_str != "unlimited" else None
                expires_at = datetime.strptime(expires_str, "%B %d %Y at %H:%M")
                used_by_user = used_by if used_by != "none" else None
            except ValueError:
                continue  # Skip malformed data
            
            # Create invite token record
            new_token = InviteToken(
                token=token,
                created_by_user=created_by,
                usage_count=usage_count,
                max_uses=max_uses,
                expires_at=expires_at,
                used_by_user_id=used_by_user
            )
            session.add(new_token)
            imported_count += 1
        else:
            imported_count += 1
    
    if not dry_run and imported_count > 0:
        session.commit()
    
    if dry_run:
        print(f"    ✅ Would import {imported_count} invite tokens")
    else:
        print(f"    ✅ Imported {imported_count} invite tokens")
    return True

def import_security_logs_from_text_archive(session: DBSession, archives_dir: str, dry_run: bool = False) -> bool:
    """Import security logs from text archives."""
    print(f"  📄 {'Checking' if dry_run else 'Importing'} security logs...")
    
    security_dir = Path(archives_dir) / "database_exports" / "security"
    if not security_dir.exists():
        print(f"    ⚠️  No security logs directory found")
        return True
    
    # Find all security log files
    security_files = list(security_dir.glob("*_security.txt"))
    if not security_files:
        print(f"    ⚠️  No security log files found")
        return True
    
    total_logs = 0
    imported_count = 0
    
    for file_path in security_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Skip header lines and empty lines
        data_lines = [line.strip() for line in lines[3:] if line.strip()]
        
        for line in data_lines:
            total_logs += 1
            if '|' not in line:
                continue
                
            parts = line.split('|')
            if len(parts) != 5:
                continue
            
            timestamp_str, event_type, user, ip, details = parts
            
            if not dry_run:
                # Parse timestamp
                try:
                    created_at = datetime.strptime(timestamp_str, "%B %d %Y at %H:%M")
                except ValueError:
                    continue
                
                # Create security log record
                new_log = SecurityLog(
                    event_type=event_type,
                    user_id=user if user != "anonymous" else None,
                    ip_address=ip if ip != "unknown" else None,
                    details=details if details else None,
                    created_at=created_at
                )
                session.add(new_log)
                imported_count += 1
            else:
                imported_count += 1
    
    if not dry_run and imported_count > 0:
        session.commit()
    
    if dry_run:
        print(f"    ✅ Would import {imported_count} of {total_logs} security log entries")
    else:
        print(f"    ✅ Imported {imported_count} of {total_logs} security log entries")
    return True

def import_roles_from_text_archive(session: DBSession, archives_dir: str, dry_run: bool = False) -> bool:
    """Import roles and user roles from text archive."""
    print(f"  📄 {'Checking' if dry_run else 'Importing'} roles and user roles...")
    
    roles_dir = Path(archives_dir) / "database_exports" / "roles"
    if not roles_dir.exists():
        print(f"    ⚠️  No roles directory found")
        return True
    
    imported_roles = 0
    imported_user_roles = 0
    
    # Import roles
    roles_file = roles_dir / "roles.txt"
    if roles_file.exists():
        with open(roles_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        data_lines = [line.strip() for line in lines[3:] if line.strip()]
        
        for line in data_lines:
            if '|' not in line:
                continue
                
            parts = line.split('|')
            if len(parts) != 5:
                continue
            
            role_name, description, permissions, created_by, is_system_str = parts
            
            if not dry_run:
                # Check if role already exists
                existing = session.exec(select(Role).where(Role.name == role_name)).first()
                if existing:
                    continue  # Skip duplicates
                
                # Create role record
                new_role = Role(
                    name=role_name,
                    description=description if description else None,
                    permissions=permissions,
                    created_by=created_by if created_by != "system" else None,
                    is_system_role=(is_system_str == "yes")
                )
                session.add(new_role)
                imported_roles += 1
            else:
                imported_roles += 1
    
    # Import user roles
    user_roles_file = roles_dir / "user_roles.txt"
    if user_roles_file.exists():
        with open(user_roles_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        data_lines = [line.strip() for line in lines[3:] if line.strip()]
        
        for line in data_lines:
            if '|' not in line:
                continue
                
            parts = line.split('|')
            if len(parts) != 5:
                continue
            
            granted_str, user_id, role_id, granted_by, expires_str = parts
            
            if not dry_run:
                # Check if user role already exists
                existing = session.exec(
                    select(UserRole).where(
                        UserRole.user_id == user_id,
                        UserRole.role_id == role_id
                    )
                ).first()
                if existing:
                    continue  # Skip duplicates
                
                # Parse timestamps
                try:
                    granted_at = datetime.strptime(granted_str, "%B %d %Y at %H:%M")
                    expires_at = datetime.strptime(expires_str, "%B %d %Y at %H:%M") if expires_str != "never" else None
                except ValueError:
                    continue
                
                # Create user role record
                new_user_role = UserRole(
                    user_id=user_id,
                    role_id=role_id,
                    granted_by=granted_by if granted_by != "system" else None,
                    granted_at=granted_at,
                    expires_at=expires_at
                )
                session.add(new_user_role)
                imported_user_roles += 1
            else:
                imported_user_roles += 1
    
    if not dry_run and (imported_roles > 0 or imported_user_roles > 0):
        session.commit()
    
    if dry_run:
        print(f"    ✅ Would import {imported_roles} roles and {imported_user_roles} user role assignments")
    else:
        print(f"    ✅ Imported {imported_roles} roles and {imported_user_roles} user role assignments")
    return True

def import_all_data(dry_run: bool = False):
    """Import all database data from text archives."""
    # Database operations will proceed - removed PRODUCTION_MODE check
    
    # Check if database is initialized, and initialize if needed
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
    
    # Create session
    with DBSession(engine) as session:
        archives_dir = "text_archives"
        
        # Import functions for different data types
        import_functions = [
            import_sessions_from_text_archive,
            import_invite_tokens_from_text_archive,
            import_security_logs_from_text_archive,
            import_roles_from_text_archive
        ]
        
        success = True
        for import_func in import_functions:
            try:
                if not import_func(session, archives_dir, dry_run):
                    success = False
            except Exception as e:
                print(f"❌ Error in {import_func.__name__}: {e}")
                success = False
        
        return success

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    success = import_all_data(dry_run)
    if success:
        if dry_run:
            print("✅ Import preview completed successfully!")
        else:
            print("✅ Complete database import completed successfully!")
    else:
        print("❌ Database import failed!")
        sys.exit(1)