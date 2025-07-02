#!/usr/bin/env python3
"""
ThyWill Role-Based Permission System Migration

This script migrates from the old ID-based admin system to the new role-based system.
It creates the necessary tables and migrates existing admin users.

Usage: python migrate_to_roles.py [--dry-run]
"""

import argparse
import sys
import json
from datetime import datetime
from sqlmodel import Session, select, text
from models import engine, User, Role, UserRole

def create_tables():
    """Create the new role and user_role tables"""
    print("Creating role and user_role tables...")
    
    # Create tables using raw SQL to ensure compatibility
    with engine.begin() as conn:
        # Create role table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS role (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                permissions TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                created_by TEXT,
                is_system_role BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY(created_by) REFERENCES user(display_name)
            )
        """))
        
        # Create user_roles table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role_id TEXT NOT NULL,
                granted_by TEXT,
                granted_at TEXT NOT NULL,
                expires_at TEXT,
                FOREIGN KEY(user_id) REFERENCES user(display_name),
                FOREIGN KEY(role_id) REFERENCES role(id),
                FOREIGN KEY(granted_by) REFERENCES user(display_name)
            )
        """))
        
        print("✅ Tables created successfully")

def create_default_roles():
    """Create default system roles"""
    print("Creating default system roles...")
    
    with Session(engine) as session:
        # Admin role with all permissions
        admin_role = Role(
            name="admin",
            description="Full administrative access",
            permissions=json.dumps([
                "*",  # Wildcard permission for everything
                "admin.users",
                "admin.roles", 
                "admin.prayers",
                "admin.system",
                "moderate.prayers",
                "view.analytics"
            ]),
            is_system_role=True,
            created_by=None  # System created
        )
        
        # Moderator role
        moderator_role = Role(
            name="moderator", 
            description="Prayer moderation and user management",
            permissions=json.dumps([
                "moderate.prayers",
                "view.users",
                "flag.prayers",
                "view.reports"
            ]),
            is_system_role=True,
            created_by=None
        )
        
        # User role (default for all users)
        user_role = Role(
            name="user",
            description="Standard user permissions",
            permissions=json.dumps([
                "create.prayers",
                "view.prayers",
                "mark.prayers",
                "view.profile"
            ]),
            is_system_role=True,
            created_by=None
        )
        
        # Check if roles already exist
        existing_roles = {}
        for role in [admin_role, moderator_role, user_role]:
            stmt = select(Role).where(Role.name == role.name)
            existing = session.exec(stmt).first()
            if existing:
                print(f"   Role '{role.name}' already exists")
                existing_roles[role.name] = existing
            else:
                session.add(role)
                existing_roles[role.name] = role
                print(f"   Created role '{role.name}'")
        
        session.commit()
        print("✅ Default roles created")
        return existing_roles

def migrate_existing_admin(dry_run=False):
    """Migrate existing admin user from ID-based system to role-based"""
    print("Migrating existing admin user...")
    
    with Session(engine) as session:
        # Find current admin user (user with display_name = "admin")
        stmt = select(User).where(User.display_name == "admin")
        admin_user = session.exec(stmt).first()
        
        if not admin_user:
            print("   No existing admin user found (display_name = 'admin')")
            return None
        
        print(f"   Found admin user: {admin_user.display_name}")
        
        if dry_run:
            print("   [DRY RUN] Would migrate admin user to role-based system")
            return admin_user
        
        # Get admin role
        stmt = select(Role).where(Role.name == "admin")
        admin_role = session.exec(stmt).first()
        
        if not admin_role:
            print("   ❌ Admin role not found!")
            return None
        
        # Check if user already has admin role
        stmt = select(UserRole).where(
            UserRole.user_id == admin_user.display_name,
            UserRole.role_id == admin_role.id
        )
        existing_user_role = session.exec(stmt).first()
        
        if existing_user_role:
            print("   Admin user already has admin role")
        else:
            # Grant admin role to user
            user_role = UserRole(
                user_id=admin_user.display_name,
                role_id=admin_role.id,
                granted_by=None,  # System migration
                granted_at=datetime.utcnow()
            )
            session.add(user_role)
            print("   ✅ Granted admin role to existing admin user")
        
        session.commit()
        return admin_user

def assign_default_roles_to_users(dry_run=False):
    """Assign default 'user' role to all users who don't have any roles"""
    print("Assigning default roles to users...")
    
    with Session(engine) as session:
        # Get user role
        stmt = select(Role).where(Role.name == "user")
        user_role = session.exec(stmt).first()
        
        if not user_role:
            print("   ❌ Default user role not found!")
            return
        
        # Get all users
        stmt = select(User)
        all_users = session.exec(stmt).all()
        
        users_granted = 0
        for user in all_users:
            # Check if user has any roles
            stmt = select(UserRole).where(UserRole.user_id == user.display_name)
            existing_roles = session.exec(stmt).all()
            
            if not existing_roles:
                if dry_run:
                    print(f"   [DRY RUN] Would grant user role to: {user.display_name}")
                    users_granted += 1
                else:
                    # Grant default user role
                    user_role_assignment = UserRole(
                        user_id=user.display_name,
                        role_id=user_role.id,
                        granted_by=None,  # System migration
                        granted_at=datetime.utcnow()
                    )
                    session.add(user_role_assignment)
                    users_granted += 1
        
        if not dry_run:
            session.commit()
        
        print(f"   ✅ {'Would grant' if dry_run else 'Granted'} default user role to {users_granted} users")

def verify_migration():
    """Verify the migration was successful"""
    print("Verifying migration...")
    
    with Session(engine) as session:
        # Count roles
        stmt = select(Role)
        roles = session.exec(stmt).all()
        print(f"   Roles in system: {len(roles)}")
        for role in roles:
            print(f"     - {role.name}: {role.description}")
        
        # Count user-role assignments
        stmt = select(UserRole)
        user_roles = session.exec(stmt).all()
        print(f"   User-role assignments: {len(user_roles)}")
        
        # Check for admin users
        stmt = select(User).join(UserRole, User.display_name == UserRole.user_id).join(Role, UserRole.role_id == Role.id).where(Role.name == "admin")
        admin_users = session.exec(stmt).all()
        print(f"   Admin users: {len(admin_users)}")
        for admin in admin_users:
            print(f"     - {admin.display_name}")
        
        print("✅ Migration verification complete")

def main():
    parser = argparse.ArgumentParser(
        description="Migrate ThyWill to role-based permission system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_to_roles.py              # Run migration
  python migrate_to_roles.py --dry-run    # Preview changes without applying
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    args = parser.parse_args()
    
    print("🔄 ThyWill Role-Based Permission System Migration")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()
    
    try:
        # Step 1: Create tables
        if not args.dry_run:
            create_tables()
        else:
            print("[DRY RUN] Would create role and user_role tables")
        
        # Step 2: Create default roles
        if not args.dry_run:
            roles = create_default_roles()
        else:
            print("[DRY RUN] Would create default roles: admin, moderator, user")
        
        # Step 3: Migrate existing admin
        migrate_existing_admin(args.dry_run)
        
        # Step 4: Assign default roles to all users
        assign_default_roles_to_users(args.dry_run)
        
        # Step 5: Verify (only in real run)
        if not args.dry_run:
            verify_migration()
        
        print()
        if args.dry_run:
            print("✅ Dry run completed successfully")
            print("Run without --dry-run to apply changes")
        else:
            print("✅ Migration completed successfully!")
            print()
            print("Next steps:")
            print("1. Update the is_admin() function to use roles")
            print("2. Update CLI commands to use new role system")
            print("3. Test the new permission system")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()