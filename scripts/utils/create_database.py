#!/usr/bin/env python3
"""
Standalone Database Creation Script

This script creates the ThyWill database tables from scratch.
It should ONLY be run when you want to initialize a new database.

WARNING: This will create tables but will not overwrite existing data.
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Remove direct SQLAlchemy import
from sqlmodel import SQLModel, Session, select

def create_default_roles():
    """Create default system roles"""
    from models import engine, Role
    
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
        
        # Check if roles already exist and create them if they don't
        for role in [admin_role, moderator_role, user_role]:
            stmt = select(Role).where(Role.name == role.name)
            existing = session.exec(stmt).first()
            if existing:
                print(f"   Role '{role.name}' already exists")
            else:
                session.add(role)
                print(f"   Created role '{role.name}'")
        
        session.commit()
        print("✅ Role system initialized")

def main():
    print("ThyWill Database Creation Script")
    print("=" * 40)
    
    # Check if database file already exists - exit immediately if it does
    db_path = Path("thywill.db")
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"❌ Database file already exists (size: {size} bytes)")
        print("Database initialization skipped to protect existing data.")
        print("If you want to recreate the database, remove 'thywill.db' first.")
        sys.exit(1)
    
    # No confirmation needed if database doesn't exist
    print("Database file not found - creating new database...")
    
    try:
        # Import models to get the engine and table definitions
        from models import engine, User, Prayer, InviteToken, Session as SessionModel
        from models import PrayerMark, PrayerSkip, AuthenticationRequest, AuthApproval
        from models import AuthAuditLog, SecurityLog, PrayerAttribute, PrayerActivityLog
        from models import Role, UserRole
        
        print("Creating database tables...")
        
        # Create all tables (create_all is safe - it won't overwrite existing tables)
        SQLModel.metadata.create_all(engine)
        
        # Set up role system with default roles
        print("Setting up role-based permission system...")
        create_default_roles()
        
        # Get table count for verification
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            final_tables = [row[0] for row in result.fetchall()]
        
        print(f"✅ Database creation complete!")
        print(f"✅ Total tables: {len(final_tables)}")
        print(f"✅ Tables: {', '.join(sorted(final_tables))}")
        
        # Show database file size
        db_size = db_path.stat().st_size if db_path.exists() else 0
        print(f"✅ Database file size: {db_size} bytes")
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()