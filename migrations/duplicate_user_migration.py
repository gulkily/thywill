"""
Duplicate user migration module for automatic execution on startup
"""

from sqlmodel import Session, select, text
from models import engine, User
from datetime import datetime
import uuid
import sqlite3
import sys
import argparse

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
    try:
        result = session.exec(text("""
            UPDATE prayer SET author_id = :primary_id 
            WHERE author_id = :duplicate_id
        """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
        merge_stats['prayers_transferred'] = result.rowcount if hasattr(result, 'rowcount') else 0
    except Exception:
        pass
    
    # Transfer sessions  
    try:
        result = session.exec(text("""
            UPDATE session SET user_id = :primary_id 
            WHERE user_id = :duplicate_id
        """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
        merge_stats['sessions_transferred'] = result.rowcount if hasattr(result, 'rowcount') else 0
    except Exception:
        pass
    
    # Transfer invite relationships (invited_by_user_id)
    try:
        result = session.exec(text("""
            UPDATE user SET invited_by_user_id = :primary_id 
            WHERE invited_by_user_id = :duplicate_id
        """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
        merge_stats['invites_transferred'] = result.rowcount if hasattr(result, 'rowcount') else 0
    except Exception:
        pass
    
    # Transfer prayer marks
    try:
        result = session.exec(text("""
            UPDATE prayermark SET user_id = :primary_id 
            WHERE user_id = :duplicate_id
        """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
        merge_stats['prayer_marks_transferred'] = result.rowcount if hasattr(result, 'rowcount') else 0
    except Exception:
        pass
    
    # Update any other foreign key references that might exist
    # Security logs
    try:
        session.exec(text("""
            UPDATE securitylog SET user_id = :primary_id 
            WHERE user_id = :duplicate_id
        """), {'primary_id': primary_user.id, 'duplicate_id': duplicate_user.id})
    except Exception:
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
    except Exception:
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
    
    # Ensure merge log table exists
    try:
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
    except Exception:
        pass
    
    # Insert into user_merge_log table
    try:
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
            'automatic_startup_migration'
        ))
    except Exception as e:
        print(f"   ⚠️  Failed to log merge action: {e}")

def check_constraint_exists():
    """Check if unique constraint already exists"""
    try:
        with sqlite3.connect("thywill.db") as conn:
            cursor = conn.execute("PRAGMA index_list(user)")
            indexes = cursor.fetchall()
            
            for index in indexes:
                if 'display_name' in index[1]:
                    return True
            return False
    except Exception:
        return False

def add_unique_constraint():
    """Add unique constraint to display_name field"""
    if check_constraint_exists():
        return True
        
    try:
        with sqlite3.connect("thywill.db") as conn:
            conn.execute("CREATE UNIQUE INDEX idx_user_display_name_unique ON user(display_name)")
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        print("❌ Failed to add unique constraint - duplicates still exist")
        return False
    except Exception as e:
        print(f"❌ Error adding constraint: {e}")
        return False

def run_duplicate_user_migration():
    """Main migration function called from startup"""
    # Check if constraint already exists - if so, migration already completed
    if check_constraint_exists():
        return True
        
    print("🔄 Checking for duplicate users...")
    
    with Session(engine) as session:
        # Find duplicate usernames
        duplicates = find_duplicate_usernames(session)
        
        if not duplicates:
            print("✅ No duplicate users found")
            # Add constraint and finish
            if add_unique_constraint():
                print("✅ Unique constraint added to display_name")
            return True
        
        print(f"⚠️  Found {len(duplicates)} usernames with duplicates - merging...")
        
        # Process each duplicate group
        total_merged = 0
        for username, count in duplicates:
            users = get_users_by_username(session, username)
            primary_user = select_primary_user(users)
            
            # Merge each duplicate into the primary
            for user in users:
                if user.id != primary_user.id:
                    merge_stats = merge_user_data(session, primary_user, user)
                    log_merge_action(session, primary_user, user, merge_stats)
                    session.delete(user)
                    total_merged += 1
        
        # Commit all changes
        session.commit()
        print(f"✅ Merged {total_merged} duplicate users")
        
        # Add unique constraint
        if add_unique_constraint():
            print("✅ Unique constraint added to display_name")
            return True
        else:
            print("❌ Failed to add unique constraint")
            return False

def check_duplicates_only():
    """Check and display duplicate users without merging"""
    with Session(engine) as session:
        duplicates = find_duplicate_usernames(session)
        
        if not duplicates:
            print('✅ No duplicate usernames found')
            return
        
        print(f'⚠️  Found {len(duplicates)} usernames with duplicates:')
        for username, count in duplicates:
            print(f'   "{username}": {count} users')
        
        # Get specific user IDs for each duplicate
        for username, count in duplicates:
            users = get_users_by_username(session, username)
            
            print(f'\n📋 Users with username "{username}":')
            sorted_users = sorted(users, key=lambda u: u.created_at)
            for i, user in enumerate(sorted_users):
                marker = '👑 PRIMARY' if i == 0 else '🔄 DUPLICATE'
                print(f'   {marker}: {user.id} (created: {user.created_at})')

def interactive_merge():
    """Run migration with user confirmation"""
    with Session(engine) as session:
        duplicates = find_duplicate_usernames(session)
        
        if not duplicates:
            print("✅ No duplicate users found - nothing to merge")
            return True
        
        print(f"⚠️  Found {len(duplicates)} duplicate usernames. This will:")
        print("   - Merge duplicate user accounts")
        print("   - Preserve all data (prayers, sessions, etc.)")
        print("   - Keep the oldest account as primary")
        print("   - Add unique constraint to prevent future duplicates")
        print("")
        
        response = input("Proceed with duplicate user merge? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Merge cancelled")
            return False
        
        # Create backup
        import shutil
        from datetime import datetime
        backup_file = f"thywill_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        print(f"Creating backup: {backup_file}")
        shutil.copy("thywill.db", backup_file)
        
        # Run the migration
        success = run_duplicate_user_migration()
        
        if success:
            print(f"✅ Duplicate users merged successfully")
            print(f"Backup saved as: {backup_file}")
        else:
            print("❌ Merge failed - database unchanged")
            # Remove backup file since it wasn't needed
            try:
                import os
                os.remove(backup_file)
            except:
                pass
        
        return success

def main():
    """Main entry point for command line usage"""
    parser = argparse.ArgumentParser(description='Manage duplicate users')
    parser.add_argument('--check-only', action='store_true', 
                       help='Only check for duplicates, do not merge')
    parser.add_argument('--interactive', action='store_true',
                       help='Run interactive merge with user confirmation')
    
    args = parser.parse_args()
    
    if args.check_only:
        check_duplicates_only()
    elif args.interactive:
        success = interactive_merge()
        sys.exit(0 if success else 1)
    else:
        # Default behavior - automatic migration
        success = run_duplicate_user_migration()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()