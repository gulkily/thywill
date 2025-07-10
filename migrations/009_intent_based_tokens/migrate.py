#!/usr/bin/env python3
"""
Migration 009: Intent-Based Tokens
Add token_type field to invite_tokens table for preventing username conflicts.
"""

import sqlite3
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from models import engine
from sqlmodel import text

def migrate_up():
    """Apply the migration - add token_type column and indexes."""
    print("Migration 009: Adding token_type field to invite_tokens...")
    
    with engine.begin() as conn:
        # Check if token_type column already exists (idempotency)
        result = conn.execute(text("PRAGMA table_info(invitetoken)"))
        columns = [row.name for row in result]
        
        if 'token_type' not in columns:
            # Add token_type column with default value
            print("  Adding token_type column...")
            conn.execute(text("ALTER TABLE invitetoken ADD COLUMN token_type VARCHAR(20) DEFAULT 'new_user'"))
            
            # Update any existing NULL values (should not be any, but just in case)
            print("  Setting default values for existing tokens...")
            result = conn.execute(text("UPDATE invitetoken SET token_type = 'new_user' WHERE token_type IS NULL"))
            print(f"  Updated {result.rowcount} existing tokens to 'new_user' type")
        else:
            print("  token_type column already exists, skipping...")
        
        # Check and add performance indexes (idempotent)
        result = conn.execute(text("PRAGMA index_list(invitetoken)"))
        existing_indexes = [row.name for row in result]
        
        if 'idx_invitetoken_token_type' not in existing_indexes:
            print("  Adding token_type index...")
            conn.execute(text("CREATE INDEX idx_invitetoken_token_type ON invitetoken(token_type)"))
        else:
            print("  token_type index already exists, skipping...")
            
        if 'idx_invitetoken_type_creator' not in existing_indexes:
            print("  Adding type_creator index...")
            conn.execute(text("CREATE INDEX idx_invitetoken_type_creator ON invitetoken(token_type, created_by_user)"))
        else:
            print("  type_creator index already exists, skipping...")
        
        # Verify the migration
        result = conn.execute(text("SELECT COUNT(*) as total, token_type FROM invitetoken GROUP BY token_type"))
        for row in result:
            print(f"  Found {row.total} tokens of type '{row.token_type}'")
    
    print("Migration 009: Completed successfully!")
    return True

def migrate_down():
    """Rollback the migration - remove token_type column and indexes."""
    print("Migration 009 Down: Removing token_type field from invite_tokens...")
    
    with engine.begin() as conn:
        # Drop indexes first
        print("  Dropping indexes...")
        conn.execute(text("DROP INDEX IF EXISTS idx_invitetoken_type_creator"))
        conn.execute(text("DROP INDEX IF EXISTS idx_invitetoken_token_type"))
        
        # Remove the column
        print("  Removing token_type column...")
        conn.execute(text("ALTER TABLE invitetoken DROP COLUMN token_type"))
    
    print("Migration 009 Down: Completed successfully!")
    return True

def verify_migration():
    """Verify the migration was applied correctly."""
    try:
        with engine.begin() as conn:
            # Check if token_type column exists
            result = conn.execute(text("PRAGMA table_info(invitetoken)"))
            columns = [row.name for row in result]
            
            if 'token_type' not in columns:
                print("ERROR: token_type column not found!")
                return False
            
            # Check if indexes exist
            result = conn.execute(text("PRAGMA index_list(invitetoken)"))
            indexes = [row.name for row in result]
            
            required_indexes = ['idx_invitetoken_token_type', 'idx_invitetoken_type_creator']
            for idx in required_indexes:
                if idx not in indexes:
                    print(f"WARNING: Index {idx} not found")
            
            # Check token types
            result = conn.execute(text("SELECT DISTINCT token_type FROM invitetoken"))
            token_types = [row.token_type for row in result]
            print(f"Found token types: {token_types}")
            
            return True
    except Exception as e:
        print(f"Migration verification failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "down":
        migrate_down()
    elif len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_migration()
    else:
        migrate_up()