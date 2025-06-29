#!/usr/bin/env python3
"""
Role Management CLI Module

Handles admin role granting, revoking, and listing operations.
Can be run independently or called from the CLI script.
"""

import sys
from typing import List, Optional
from datetime import datetime
from sqlmodel import Session, select
from models import engine, User, Role, UserRole
from app_helpers.cli.user_lookup import find_user_by_identifier


def grant_admin_role(user_identifier: str) -> bool:
    """
    Grant admin role to a user.
    
    Args:
        user_identifier: User ID or display name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with Session(engine) as session:
            user = find_user_by_identifier(session, user_identifier)
            if not user:
                return False
            
            # Get admin role
            stmt = select(Role).where(Role.name == 'admin')
            admin_role = session.exec(stmt).first()
            
            if not admin_role:
                print('❌ Admin role not found. Run migration first: python migrate_to_roles.py')
                return False
            
            # Check if user already has admin role
            if user.has_role('admin', session):
                print(f'ℹ️  User "{user.display_name}" already has admin role')
                return True
            
            # Check for backward compatibility (old system)
            if user.id == 'admin':
                print(f'ℹ️  User "{user.display_name}" already has admin rights (old system)')
                print('   Run migration to convert to role-based system: python migrate_to_roles.py')
                return True
            
            # Grant admin role
            user_role = UserRole(
                user_id=user.id,
                role_id=admin_role.id,
                granted_by=None,  # CLI granted
                granted_at=datetime.utcnow()
            )
            session.add(user_role)
            session.commit()
            
            print(f'✅ Admin role granted to: "{user.display_name}"')
            print(f'   User ID: {user.id[:8]}...')
            print('   ✨ Using new role-based permission system')
            return True
            
    except Exception as e:
        print(f'❌ Error granting admin role: {e}')
        import traceback
        traceback.print_exc()
        return False


def revoke_admin_role(user_identifier: str) -> bool:
    """
    Revoke admin role from a user.
    
    Args:
        user_identifier: User ID or display name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with Session(engine) as session:
            user = find_user_by_identifier(session, user_identifier)
            if not user:
                return False
            
            # Get admin role
            stmt = select(Role).where(Role.name == 'admin')
            admin_role = session.exec(stmt).first()
            
            if not admin_role:
                print('❌ Admin role not found. Run migration first: python migrate_to_roles.py')
                return False
            
            # Check if user has admin role
            if not user.has_role('admin', session):
                print(f'ℹ️  User "{user.display_name}" does not have admin role')
                return True
            
            # Remove admin role
            stmt = select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == admin_role.id
            )
            user_roles = session.exec(stmt).all()
            
            for user_role in user_roles:
                session.delete(user_role)
            
            session.commit()
            
            print(f'✅ Admin role revoked from: "{user.display_name}"')
            print(f'   User ID: {user.id[:8]}...')
            print('   ✨ Using new role-based permission system')
            return True
            
    except Exception as e:
        print(f'❌ Error revoking admin role: {e}')
        import traceback
        traceback.print_exc()
        return False


def list_admin_users() -> List[User]:
    """
    List all users with admin privileges.
    
    Returns:
        List of admin users
    """
    try:
        with Session(engine) as session:
            # Get users with admin role (new system)
            stmt = select(User).join(UserRole).join(Role).where(Role.name == 'admin')
            role_based_admins = list(session.exec(stmt))
            
            # Get legacy admin user (old system)
            legacy_admin_stmt = select(User).where(User.id == 'admin')
            legacy_admin = session.exec(legacy_admin_stmt).first()
            
            all_admins = role_based_admins
            if legacy_admin and legacy_admin not in all_admins:
                all_admins.append(legacy_admin)
            
            return all_admins
            
    except Exception as e:
        print(f'❌ Error listing admin users: {e}')
        return []


def print_admin_list():
    """Print formatted list of admin users."""
    print('👑 Admin Users')
    print('=' * 25)
    print()
    
    admins = list_admin_users()
    
    if not admins:
        print('ℹ️  No admin users found')
        print('   Use "thywill admin grant <user>" to grant admin privileges')
        return
    
    print(f'Found {len(admins)} admin user(s):')
    print()
    
    for admin in admins:
        system_type = "(legacy)" if admin.id == 'admin' else "(role-based)"
        print(f'• "{admin.display_name}" {system_type}')
        print(f'  ID: {admin.id[:8]}...')
        print(f'  Created: {admin.created_at}')
        print()
    
    if any(admin.id == 'admin' for admin in admins):
        print('💡 Note: Legacy admin users should be migrated to role-based system')
        print('   Run: python migrate_to_roles.py')


def main():
    """Main entry point when run as a standalone script."""
    if len(sys.argv) < 2:
        print("Usage: python role_management.py [grant|revoke|list] [user_identifier]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "grant":
        if len(sys.argv) < 3:
            print("Usage: python role_management.py grant <user_identifier>")
            sys.exit(1)
        
        user_identifier = sys.argv[2]
        print(f"🔑 Granting Admin Rights to: {user_identifier}")
        print("=" * 40)
        
        if grant_admin_role(user_identifier):
            sys.exit(0)
        else:
            sys.exit(1)
            
    elif command == "revoke":
        if len(sys.argv) < 3:
            print("Usage: python role_management.py revoke <user_identifier>")
            sys.exit(1)
        
        user_identifier = sys.argv[2]
        print(f"🔓 Revoking Admin Role from: {user_identifier}")
        print("=" * 40)
        
        if revoke_admin_role(user_identifier):
            sys.exit(0)
        else:
            sys.exit(1)
            
    elif command == "list":
        print_admin_list()
        
    else:
        print(f"Unknown command: {command}")
        print("Usage: python role_management.py [grant|revoke|list] [user_identifier]")
        sys.exit(1)


if __name__ == '__main__':
    main()