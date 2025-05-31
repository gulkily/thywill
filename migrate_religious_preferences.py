#!/usr/bin/env python3
"""
Migration script for religious preference feature
Run this script to add new database columns for religious preferences

Supports two religious preference options:
- "christian": Users who identify as Christian
- "unspecified": All faiths welcome (default)

Prayer targeting options:
- "all": Visible to everyone (default)
- "christians_only": Visible only to Christian users
"""

import sys
import os
from sqlmodel import Session, text
from datetime import datetime

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, User, Prayer

def check_column_exists(session: Session, table_name: str, column_name: str) -> bool:
    """Check if a column exists in the given table"""
    result = session.exec(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(row[1] == column_name for row in result)

def migrate_religious_preferences():
    """Add religious preference columns to User and Prayer tables"""
    print("Starting religious preference migration...")
    
    with Session(engine) as db:
        try:
            # Check and add User table columns
            if not check_column_exists(db, "user", "religious_preference"):
                db.exec(text("ALTER TABLE user ADD COLUMN religious_preference TEXT DEFAULT 'unspecified'"))
                print("✓ Added religious_preference column to user table")
            else:
                print("- religious_preference column already exists in user table")
                
            if not check_column_exists(db, "user", "prayer_style"):
                db.exec(text("ALTER TABLE user ADD COLUMN prayer_style TEXT DEFAULT NULL"))
                print("✓ Added prayer_style column to user table")
            else:
                print("- prayer_style column already exists in user table")
            
            # Check and add Prayer table columns
            if not check_column_exists(db, "prayer", "target_audience"):
                db.exec(text("ALTER TABLE prayer ADD COLUMN target_audience TEXT DEFAULT 'all'"))
                print("✓ Added target_audience column to prayer table")
            else:
                print("- target_audience column already exists in prayer table")
                
            if not check_column_exists(db, "prayer", "prayer_context"):
                db.exec(text("ALTER TABLE prayer ADD COLUMN prayer_context TEXT DEFAULT NULL"))
                print("✓ Added prayer_context column to prayer table")
            else:
                print("- prayer_context column already exists in prayer table")
            
            db.commit()
            print("✓ Migration completed successfully")
            
            # Verify the migration
            user_count = db.exec(text("SELECT COUNT(*) FROM user")).first()
            prayer_count = db.exec(text("SELECT COUNT(*) FROM prayer")).first()
            print(f"✓ Verified: {user_count} users and {prayer_count} prayers migrated")
            
        except Exception as e:
            db.rollback()
            print(f"✗ Migration failed: {e}")
            raise
    
    print("Migration completed!")

def rollback_migration():
    """Remove religious preference columns (for testing purposes)"""
    print("Rolling back religious preference migration...")
    
    with Session(engine) as db:
        try:
            # Note: SQLite doesn't support DROP COLUMN, so we'd need to recreate tables
            # This is primarily for development/testing purposes
            print("Warning: SQLite doesn't support DROP COLUMN")
            print("To fully rollback, restore from backup or recreate database")
            
        except Exception as e:
            print(f"✗ Rollback failed: {e}")
            raise

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        migrate_religious_preferences()