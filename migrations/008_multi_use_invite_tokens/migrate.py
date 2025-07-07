#!/usr/bin/env python3
"""
Migration 008: Convert single-use invite tokens to multi-use system

This migration:
1. Adds new columns (usage_count, max_uses) to InviteToken table
2. Creates new InviteTokenUsage table for tracking individual claims
3. Migrates existing data preserving all relationships
4. Creates usage records for tokens that were already used
5. Removes old 'used' column after successful migration

Follows the established ThyWill migration pattern.
"""

import os
import sys
import uuid
from datetime import datetime
from sqlalchemy import text
from sqlmodel import Session, create_engine

def get_engine():
    """Get database engine following ThyWill patterns"""
    # Use the same database path logic as the main application
    import sys
    
    # Test environment detection
    if ('pytest' in sys.modules or 
        'PYTEST_CURRENT_TEST' in os.environ or
        any('pytest' in arg for arg in sys.argv)):
        database_path = ':memory:'
    elif 'DATABASE_PATH' in os.environ:
        database_path = os.environ['DATABASE_PATH']
    else:
        database_path = 'thywill.db'
    
    if database_path == ':memory:':
        return create_engine(
            "sqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False}
        )
    else:
        return create_engine(
            f"sqlite:///{database_path}",
            echo=False,
            connect_args={"check_same_thread": False}
        )

def check_migration_needed(engine):
    """Check if migration is needed"""
    with engine.connect() as conn:
        try:
            result = conn.execute(text("SELECT usage_count, max_uses FROM invitetoken LIMIT 1"))
            return False  # Columns exist, migration already done
        except Exception:
            return True  # Columns don't exist, migration needed

def create_backup_table(engine):
    """Create backup of existing invite tokens"""
    print("Creating backup table...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Create backup table
            conn.execute(text("""
                CREATE TABLE invitetoken_backup_008 AS 
                SELECT * FROM invitetoken
            """))
            
            trans.commit()
            print("✓ Backup table 'invitetoken_backup_008' created")
            
        except Exception as e:
            trans.rollback()
            raise Exception(f"Failed to create backup: {e}")

def migrate_schema(engine):
    """Perform the schema migration"""
    print("Migrating database schema...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # Step 1: Add new columns to InviteToken table
            print("  Adding new columns to invitetoken table...")
            conn.execute(text("ALTER TABLE invitetoken ADD COLUMN usage_count INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE invitetoken ADD COLUMN max_uses INTEGER DEFAULT NULL"))
            
            # Step 2: Create InviteTokenUsage table
            print("  Creating invite_token_usage table...")
            conn.execute(text("""
                CREATE TABLE invite_token_usage (
                    id TEXT PRIMARY KEY,
                    invite_token_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    claimed_at TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    FOREIGN KEY (invite_token_id) REFERENCES invitetoken (token),
                    FOREIGN KEY (user_id) REFERENCES user (display_name)
                )
            """))
            
            # Step 3: Set default max_uses for existing tokens
            default_max_uses = int(os.getenv("DEFAULT_INVITE_MAX_USES", "1"))
            print(f"  Setting max_uses = {default_max_uses} for existing tokens")
            conn.execute(text(f"UPDATE invitetoken SET max_uses = {default_max_uses}"))
            
            # Step 4: Migrate existing usage data
            print("  Migrating existing token usage data...")
            
            # Set usage_count = 1 for tokens that were already used
            conn.execute(text("UPDATE invitetoken SET usage_count = 1 WHERE used = 1"))
            
            # Create usage records for tokens that were already used
            used_tokens = conn.execute(text("""
                SELECT token, used_by_user_id, expires_at 
                FROM invitetoken 
                WHERE used = 1 AND used_by_user_id IS NOT NULL
            """)).fetchall()
            
            for token, user_id, expires_at in used_tokens:
                usage_id = uuid.uuid4().hex
                conn.execute(text("""
                    INSERT INTO invite_token_usage (id, invite_token_id, user_id, claimed_at, ip_address)
                    VALUES (:id, :token, :user_id, :claimed_at, NULL)
                """), {
                    'id': usage_id,
                    'token': token,
                    'user_id': user_id,
                    'claimed_at': expires_at  # Best approximation for historical data
                })
            
            print(f"  Created {len(used_tokens)} usage records for previously used tokens")
            
            trans.commit()
            print("✓ Schema migration completed successfully")
            
        except Exception as e:
            trans.rollback()
            raise Exception(f"Schema migration failed: {e}")

def remove_old_column(engine):
    """Remove the old 'used' column by recreating the table"""
    print("Removing old 'used' column...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # Create new table without 'used' column
            conn.execute(text("""
                CREATE TABLE invitetoken_new (
                    token TEXT PRIMARY KEY,
                    created_by_user TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    max_uses INTEGER DEFAULT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used_by_user_id TEXT DEFAULT NULL
                )
            """))
            
            # Copy data from old table to new table
            conn.execute(text("""
                INSERT INTO invitetoken_new 
                (token, created_by_user, usage_count, max_uses, expires_at, used_by_user_id)
                SELECT token, created_by_user, usage_count, max_uses, expires_at, used_by_user_id
                FROM invitetoken
            """))
            
            # Drop old table and rename new table
            conn.execute(text("DROP TABLE invitetoken"))
            conn.execute(text("ALTER TABLE invitetoken_new RENAME TO invitetoken"))
            
            # Recreate indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_invitetoken_used_by ON invitetoken(used_by_user_id)"))
            
            trans.commit()
            print("✓ Old 'used' column removed successfully")
            
        except Exception as e:
            trans.rollback()
            raise Exception(f"Failed to remove old column: {e}")

def verify_migration(engine):
    """Verify the migration was successful"""
    print("Verifying migration...")
    
    with engine.connect() as conn:
        # Check new columns exist and have correct data
        result = conn.execute(text("""
            SELECT COUNT(*) as total_tokens,
                   SUM(CASE WHEN usage_count = 0 THEN 1 ELSE 0 END) as unused_tokens,
                   SUM(CASE WHEN usage_count > 0 THEN 1 ELSE 0 END) as used_tokens,
                   SUM(CASE WHEN max_uses IS NOT NULL THEN 1 ELSE 0 END) as tokens_with_max_uses
            FROM invitetoken
        """)).fetchone()
        
        total_tokens, unused_tokens, used_tokens, tokens_with_max_uses = result
        
        print(f"  Total tokens: {total_tokens}")
        print(f"  Unused tokens: {unused_tokens}")
        print(f"  Used tokens: {used_tokens}")
        print(f"  Tokens with max_uses set: {tokens_with_max_uses}")
        
        # Check usage records
        usage_count = conn.execute(text("SELECT COUNT(*) FROM invite_token_usage")).scalar()
        print(f"  Usage records created: {usage_count}")
        
        # Verify consistency
        if used_tokens == usage_count:
            print("✓ Data consistency verified")
            return True
        else:
            print(f"✗ Data inconsistency: {used_tokens} used tokens but {usage_count} usage records")
            return False

def migrate():
    """Main migration function following ThyWill pattern"""
    print("Running migration 008: Multi-use invite tokens")
    
    engine = get_engine()
    
    # Check if migration is needed
    if not check_migration_needed(engine):
        print("Migration already applied, skipping.")
        return True
    
    try:
        # Create backup
        create_backup_table(engine)
        
        # Perform migration steps
        migrate_schema(engine)
        
        # Verify migration
        if not verify_migration(engine):
            raise Exception("Migration verification failed")
        
        # Clean up old column
        remove_old_column(engine)
        
        print("✓ Migration 008 completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Migration 008 failed: {e}")
        print("Backup table 'invitetoken_backup_008' available for recovery")
        return False

def rollback():
    """Rollback migration following ThyWill pattern"""
    print("Rolling back migration 008: Multi-use invite tokens")
    
    engine = get_engine()
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # Check if backup exists
            backup_exists = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='invitetoken_backup_008'
            """)).fetchone()
            
            if not backup_exists:
                raise Exception("Backup table 'invitetoken_backup_008' not found")
            
            # Drop new table and usage table
            conn.execute(text("DROP TABLE IF EXISTS invite_token_usage"))
            conn.execute(text("DROP TABLE IF EXISTS invitetoken"))
            
            # Restore from backup
            conn.execute(text("ALTER TABLE invitetoken_backup_008 RENAME TO invitetoken"))
            
            # Recreate original indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_invitetoken_used_by ON invitetoken(used_by_user_id)"))
            
            trans.commit()
            print("✓ Migration 008 rolled back successfully")
            return True
            
        except Exception as e:
            trans.rollback()
            print(f"✗ Rollback failed: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate()