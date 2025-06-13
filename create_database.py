#!/usr/bin/env python3
"""
Standalone Database Creation Script

This script creates the ThyWill database tables from scratch.
It should ONLY be run when you want to initialize a new database.

WARNING: This will create tables but will not overwrite existing data.
"""

import sys
import os
from pathlib import Path
from sqlalchemy import inspect
from sqlmodel import SQLModel

def main():
    print("ThyWill Database Creation Script")
    print("=" * 40)
    
    # Confirmation prompt
    response = input("Are you sure you want to create database tables? (type 'yes' to confirm): ")
    if response.lower() != 'yes':
        print("Database creation cancelled.")
        sys.exit(0)
    
    # Check if database file already exists
    db_path = Path("thywill.db")
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"⚠️  Database file already exists (size: {size} bytes)")
        if size > 1024:  # If larger than 1KB, probably has data
            response = input("Database appears to contain data. Continue anyway? (type 'yes' to confirm): ")
            if response.lower() != 'yes':
                print("Database creation cancelled to protect existing data.")
                sys.exit(0)
    
    try:
        # Import models to get the engine and table definitions
        from models import engine, User, Prayer, InviteToken, Session as SessionModel
        from models import PrayerMark, PrayerSkip, AuthenticationRequest, AuthApproval
        from models import AuthAuditLog, SecurityLog, PrayerAttribute, PrayerActivityLog
        
        print("Creating database tables...")
        
        # Check which tables already exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if existing_tables:
            print(f"Found {len(existing_tables)} existing tables: {', '.join(existing_tables)}")
        
        # Create all tables (create_all is safe - it won't overwrite existing tables)
        SQLModel.metadata.create_all(engine)
        
        # Verify tables were created
        inspector = inspect(engine)
        final_tables = inspector.get_table_names()
        
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