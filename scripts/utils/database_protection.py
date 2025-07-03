#!/usr/bin/env python3
"""
Database Protection System

This module provides safeguards against accidental data loss:
1. Automatic backups before dangerous operations
2. Environment-based protection
3. Safe table creation methods
"""

import os
import shutil
import time
from pathlib import Path
from typing import Optional
# Remove direct SQLAlchemy import
from sqlmodel import SQLModel

class DatabaseProtection:
    """Database protection utilities"""
    
    @staticmethod
    def is_production() -> bool:
        """Check if we're in production environment"""
        return os.getenv('ENVIRONMENT', 'development') == 'production'
    
    @staticmethod
    def backup_database(db_path: str = "thywill.db") -> Optional[str]:
        """Create a backup of the database"""
        if not Path(db_path).exists():
            return None
        
        timestamp = int(time.time())
        backup_path = f"backups/thywill_backup_{timestamp}.db"
        
        # Create backups directory if it doesn't exist
        Path("backups").mkdir(exist_ok=True)
        
        try:
            shutil.copy2(db_path, backup_path)
            print(f"✅ Database backup created: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return None
    
    @staticmethod
    def safe_create_tables(engine, force: bool = False):
        """Safely create database tables with protection"""
        if DatabaseProtection.is_production() and not force:
            if not os.getenv('INIT_DATABASE', 'false').lower() == 'true':
                print("⚠️  Production database creation blocked. Use INIT_DATABASE=true to override.")
                return False
        
        # Create backup before any schema changes
        backup_path = DatabaseProtection.backup_database()
        if backup_path:
            print(f"Backup created before schema changes: {backup_path}")
        
        try:
            SQLModel.metadata.create_all(engine)
            print("✅ Database tables created successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to create tables: {e}")
            return False
    
    @staticmethod
    def safe_create_table(table_class, engine):
        """Safely create a single table"""
        table_name = table_class.__tablename__
        
        # Check if table exists using direct SQL query
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=?"), (table_name,))
            exists = result.fetchone() is not None
        
        if not exists:
            table_class.__table__.create(engine, checkfirst=True)
            print(f"✅ Created table: {table_name}")
        else:
            print(f"✓ Table already exists: {table_name}")

def require_explicit_confirmation(action: str) -> bool:
    """Require explicit user confirmation for dangerous operations"""
    if os.getenv('FORCE_YES', 'false').lower() == 'true':
        return True
    
    response = input(f"⚠️  You are about to {action}. Type 'yes' to confirm: ")
    return response.lower() == 'yes'