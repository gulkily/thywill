#!/usr/bin/env python3
"""
Migration script to handle duplicate users and add unique constraint
"""

from sqlmodel import Session, select, text
from models import engine, User
from datetime import datetime
import uuid
import sys
import sqlite3

def find_duplicate_usernames(session: Session):
    """Find all usernames that have duplicates"""
    result = session.exec(text("""
        SELECT display_name, COUNT(*) as count 
        FROM user 
        GROUP BY display_name 
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """))
    return result.fetchall()

def get_users_by_username(session: Session, username: str):
    """Get all users with a specific username"""
    stmt = select(User).where(User.display_name == username)
    return session.exec(stmt).all()

def select_primary_user(users):
    """Select which user to keep as primary (oldest by creation date)"""
    return min(users, key=lambda u: u.created_at)

def merge_user_data(session: Session, primary_user: User, duplicate_user: User):
    """Merge data from duplicate user into primary user"""
    merge_stats = {
        'prayers_transferred': 0,
        'sessions_transferred': 0,
        'invites_transferred': 0,
        'prayer_marks_transferred': 0
    }
    
    # Transfer prayers
    prayer_update = session.exec(text("""
        UPDATE prayer SET author_id = :primary_id 
        WHERE author_id = :duplicate_id
    """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
    merge_stats['prayers_transferred'] = prayer_update.rowcount if hasattr(prayer_update, 'rowcount') else 0
    
    # Transfer sessions  
    session_update = session.exec(text("""
        UPDATE session SET user_id = :primary_id 
        WHERE user_id = :duplicate_id
    """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
    merge_stats['sessions_transferred'] = session_update.rowcount if hasattr(session_update, 'rowcount') else 0
    
    # Transfer invite relationships (invited_by_user_id)
    invite_update = session.exec(text("""
        UPDATE user SET invited_by_user_id = :primary_id 
        WHERE invited_by_user_id = :duplicate_id
    """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
    merge_stats['invites_transferred'] = invite_update.rowcount if hasattr(invite_update, 'rowcount') else 0
    
    # Transfer prayer marks
    prayermark_update = session.exec(text("""
        UPDATE prayermark SET user_id = :primary_id 
        WHERE user_id = :duplicate_id
    """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
    merge_stats['prayer_marks_transferred'] = prayermark_update.rowcount if hasattr(prayermark_update, 'rowcount') else 0
    
    # Update any other foreign key references that might exist
    # Security logs
    try:
        session.exec(text("""
            UPDATE securitylog SET user_id = :primary_id 
            WHERE user_id = :duplicate_id
        """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
    except:
        pass  # Table might not exist
    
    # Authentication requests
    try:
        session.exec(text("""
            UPDATE authenticationrequest SET user_id = :primary_id 
            WHERE user_id = :duplicate_id
        """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
        
        session.exec(text("""
            UPDATE authapproval SET approver_id = :primary_id 
            WHERE approver_id = :duplicate_id
        """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
    except:
        pass  # Tables might not exist
    
    # Merge text archive paths if duplicate has one and primary doesn't
    if duplicate_user.text_file_path and not primary_user.text_file_path:
        primary_user.text_file_path = duplicate_user.text_file_path
        session.add(primary_user)
    
    # Preserve religious preferences if primary user doesn't have them
    if duplicate_user.religious_preference and duplicate_user.religious_preference != 'unspecified':
        if not primary_user.religious_preference or primary_user.religious_preference == 'unspecified':
            primary_user.religious_preference = duplicate_user.religious_preference
    
    if duplicate_user.prayer_style and not primary_user.prayer_style:
        primary_user.prayer_style = duplicate_user.prayer_style
    
    session.add(primary_user)
    
    return merge_stats

def log_merge_action(session: Session, primary_user: User, duplicate_user: User, merge_stats: dict):
    """Log the merge action for audit trail"""
    merge_id = uuid.uuid4().hex
    
    # Insert into user_merge_log table
    session.exec(text("""
        INSERT INTO user_merge_log 
        (id, primary_user_id, merged_user_id, original_display_name, 
         merge_timestamp, prayers_transferred, sessions_transferred, 
         invites_transferred, merge_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """), (
        merge_id,
        primary_user.id,
        duplicate_user.id, 
        duplicate_user.display_name,
        datetime.now(),
        merge_stats['prayers_transferred'],
        merge_stats['sessions_transferred'], 
        merge_stats['invites_transferred'],
        'duplicate_display_name_migration'
    ))
    
    print(f"   ✓ Logged merge: {duplicate_user.id} -> {primary_user.id}")

def remove_duplicate_user(session: Session, duplicate_user: User):
    """Remove the duplicate user after data merge"""
    session.delete(duplicate_user)
    print(f"   ✓ Removed duplicate user: {duplicate_user.id}")

def migrate_duplicate_users():
    """Main migration function to handle duplicate users"""
    print("🔄 Starting duplicate user migration...")
    
    with Session(engine) as session:
        # First, ensure the merge log table exists
        session.exec(text("""
            CREATE TABLE IF NOT EXISTS user_merge_log (
                id VARCHAR(32) PRIMARY KEY,
                primary_user_id VARCHAR(32) NOT NULL,
                merged_user_id VARCHAR(32) NOT NULL,
                original_display_name VARCHAR NOT NULL,
                merge_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                prayers_transferred INTEGER DEFAULT 0,
                sessions_transferred INTEGER DEFAULT 0,
                invites_transferred INTEGER DEFAULT 0,
                merge_reason VARCHAR(255) DEFAULT 'duplicate_display_name'
            )
        """))
        
        # Find duplicate usernames
        duplicates = find_duplicate_usernames(session)
        
        if not duplicates:
            print("✅ No duplicate usernames found")
            return True
        
        print(f"🔍 Found {len(duplicates)} usernames with duplicates:")
        for username, count in duplicates:
            print(f"   - '{username}': {count} users")
        
        # Process each duplicate group
        total_merged = 0
        for username, count in duplicates:
            print(f"\n🔄 Processing duplicates for '{username}'...")
            
            users = get_users_by_username(session, username)
            primary_user = select_primary_user(users)
            
            print(f"   ✓ Selected primary user: {primary_user.id} (created: {primary_user.created_at})")
            
            # Merge each duplicate into the primary
            for user in users:
                if user.id != primary_user.id:
                    print(f"   🔄 Merging duplicate: {user.id} -> {primary_user.id}")
                    
                    merge_stats = merge_user_data(session, primary_user, user)
                    log_merge_action(session, primary_user, user, merge_stats)
                    remove_duplicate_user(session, user)
                    
                    total_merged += 1
                    
                    print(f"   ✅ Merged user {user.id}: {merge_stats}")
        
        # Commit all changes
        session.commit()
        print(f"\n✅ Successfully merged {total_merged} duplicate users")
        
        return True

def add_unique_constraint():
    """Add unique constraint to display_name field"""
    print("🔄 Adding unique constraint to display_name...")
    
    try:
        with sqlite3.connect("thywill.db") as conn:
            # Check if constraint already exists
            cursor = conn.execute("PRAGMA index_list(user)")
            indexes = cursor.fetchall()
            
            for index in indexes:
                if 'display_name' in index[1]:
                    print("✅ Unique constraint already exists")
                    return True
            
            # Add unique constraint
            conn.execute("CREATE UNIQUE INDEX idx_user_display_name_unique ON user(display_name)")
            conn.commit()
            print("✅ Unique constraint added successfully")
            return True
            
    except sqlite3.IntegrityError as e:
        print(f"❌ Failed to add unique constraint - duplicates still exist: {e}")
        return False
    except Exception as e:
        print(f"❌ Error adding constraint: {e}")
        return False

def main():
    """Main migration execution"""
    print("=" * 60)
    print("DUPLICATE USER MIGRATION")
    print("=" * 60)
    
    try:
        # Step 1: Merge duplicate users
        if not migrate_duplicate_users():
            print("❌ Migration failed at duplicate user merge step")
            return False
        
        # Step 2: Add unique constraint
        if not add_unique_constraint():
            print("❌ Migration failed at constraint addition step")
            return False
        
        print("\n✅ Migration completed successfully!")
        print("All duplicate users have been merged and unique constraint added.")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)