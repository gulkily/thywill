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


def grant_role(user_identifier: str, role_name: str) -> bool:
    """
    Grant any role to a user (not just admin).
    
    Args:
        user_identifier: User ID or display name
        role_name: Name of role to grant
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with Session(engine) as session:
            user = find_user_by_identifier(session, user_identifier)
            if not user:
                return False
            
            # Get role
            stmt = select(Role).where(Role.name == role_name)
            role = session.exec(stmt).first()
            
            if not role:
                print(f'❌ Role "{role_name}" not found.')
                return False
            
            # Check if user already has role
            if user.has_role(role_name, session):
                print(f'ℹ️  User "{user.display_name}" already has {role_name} role')
                return True
            
            # Grant role
            user_role = UserRole(
                user_id=user.id,
                role_id=role.id,
                granted_by=None,  # CLI granted
                granted_at=datetime.utcnow()
            )
            session.add(user_role)
            session.commit()
            
            print(f'✅ {role_name} role granted to: "{user.display_name}"')
            print(f'   User ID: {user.id[:8]}...')
            return True
            
    except Exception as e:
        print(f'❌ Error granting {role_name} role: {e}')
        import traceback
        traceback.print_exc()
        return False


def list_all_roles() -> List[Role]:
    """
    List all available roles in the system.
    
    Returns:
        List of Role objects
    """
    try:
        with Session(engine) as session:
            stmt = select(Role)
            return list(session.exec(stmt))
    except Exception as e:
        print(f'❌ Error listing roles: {e}')
        return []


def revoke_role(user_identifier: str, role_name: str) -> bool:
    """
    Revoke any role from a user.
    
    Args:
        user_identifier: User ID or display name
        role_name: Name of role to revoke
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with Session(engine) as session:
            user = find_user_by_identifier(session, user_identifier)
            if not user:
                return False
            
            # Get role
            stmt = select(Role).where(Role.name == role_name)
            role = session.exec(stmt).first()
            
            if not role:
                print(f'❌ Role "{role_name}" not found')
                return False
            
            # Check if user has this role
            if not user.has_role(role_name, session):
                print(f'ℹ️  User "{user.display_name}" does not have role "{role_name}"')
                return True
            
            # Revoke role
            stmt = select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id
            )
            user_roles = session.exec(stmt).all()
            
            for user_role in user_roles:
                session.delete(user_role)
            
            session.commit()
            
            print(f'✅ Role "{role_name}" revoked from: "{user.display_name}"')
            print(f'   User ID: {user.id[:8]}...')
            return True
            
    except Exception as e:
        print(f'❌ Error revoking role: {e}')
        import traceback
        traceback.print_exc()
        return False


def print_roles_list():
    """Print formatted list of all available roles."""
    print('🎭 Available Roles')
    print('=' * 25)
    print()
    
    roles = list_all_roles()
    
    if not roles:
        print('ℹ️  No roles found')
        print('   Roles may not be configured yet')
        return
    
    for role in roles:
        print(f'• {role.name}')
        if role.description:
            print(f'  Description: {role.description}')
        print()


def main():
    """Main entry point when run as a standalone script."""
    if len(sys.argv) < 2:
        print("Usage: python role_management.py [grant|revoke|list|list-roles] [user_identifier] [role_name]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "grant":
        if len(sys.argv) < 3:
            print("Usage: python role_management.py grant <user_identifier> [role_name]")
            print("Default role is 'admin' if not specified")
            sys.exit(1)
        
        user_identifier = sys.argv[2]
        role_name = sys.argv[3] if len(sys.argv) > 3 else "admin"
        
        print(f"🔑 Granting {role_name} Role to: {user_identifier}")
        print("=" * 40)
        
        if role_name == "admin":
            success = grant_admin_role(user_identifier)
        else:
            success = grant_role(user_identifier, role_name)
            
        sys.exit(0 if success else 1)
            
    elif command == "revoke":
        if len(sys.argv) < 3:
            print("Usage: python role_management.py revoke <user_identifier> [role_name]")
            print("Default role is 'admin' if not specified")
            sys.exit(1)
        
        user_identifier = sys.argv[2]
        role_name = sys.argv[3] if len(sys.argv) > 3 else "admin"
        
        print(f"🔓 Revoking {role_name} Role from: {user_identifier}")
        print("=" * 40)
        
        if role_name == "admin":
            success = revoke_admin_role(user_identifier)
        else:
            success = revoke_role(user_identifier, role_name)
            
        sys.exit(0 if success else 1)
            
    elif command == "list":
        print_admin_list()
        
    elif command == "list-roles":
        print_roles_list()
        
    else:
        print(f"Unknown command: {command}")
        print("Usage: python role_management.py [grant|revoke|list|list-roles] [user_identifier] [role_name]")
        sys.exit(1)


if __name__ == '__main__':
    main()