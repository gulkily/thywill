#!/usr/bin/env python3
"""
Migration script to remove religious preference system from ThyWill

This migration removes:
- religious_preference field from User model
- prayer_style field from User model  
- target_audience field from Prayer model
"""

from sqlmodel import Session, text
from models import engine
import sys
import sqlite3

def backup_preference_data():
    """Create a backup of preference data before removal"""
    print("📦 Creating backup of preference data...")
    
    try:
        with sqlite3.connect("thywill.db") as conn:
            cursor = conn.cursor()
            
            # Check if preference fields exist
            cursor.execute("PRAGMA table_info(user)")
            user_columns = [col[1] for col in cursor.fetchall()]
            
            cursor.execute("PRAGMA table_info(prayer)")
            prayer_columns = [col[1] for col in cursor.fetchall()]
            
            has_religious_pref = 'religious_preference' in user_columns
            has_prayer_style = 'prayer_style' in user_columns
            has_target_audience = 'target_audience' in prayer_columns
            
            if not (has_religious_pref or has_prayer_style or has_target_audience):
                print("✅ No preference fields found - already removed")
                return True
            
            # Create backup table for user preferences
            if has_religious_pref or has_prayer_style:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences_backup (
                        user_id VARCHAR(32) PRIMARY KEY,
                        display_name VARCHAR,
                        religious_preference VARCHAR,
                        prayer_style VARCHAR,
                        backup_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Copy preference data
                query_parts = ["display_name", "display_name"]
                if has_religious_pref:
                    query_parts.append("religious_preference")
                else:
                    query_parts.append("NULL as religious_preference")
                    
                if has_prayer_style:
                    query_parts.append("prayer_style")
                else:
                    query_parts.append("NULL as prayer_style")
                
                cursor.execute(f"""
                    INSERT OR REPLACE INTO user_preferences_backup 
                    (user_id, display_name, religious_preference, prayer_style)
                    SELECT {', '.join(query_parts)} FROM user
                    WHERE religious_preference IS NOT NULL 
                       OR prayer_style IS NOT NULL
                """)
                
                user_backup_count = cursor.rowcount
                print(f"   ✓ Backed up {user_backup_count} user preferences")
            
            # Create backup table for prayer target audiences
            if has_target_audience:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS prayer_target_audience_backup (
                        prayer_id VARCHAR(32) PRIMARY KEY,
                        target_audience VARCHAR,
                        backup_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO prayer_target_audience_backup 
                    (prayer_id, target_audience)
                    SELECT id, target_audience FROM prayer
                    WHERE target_audience IS NOT NULL
                """)
                
                prayer_backup_count = cursor.rowcount
                print(f"   ✓ Backed up {prayer_backup_count} prayer target audiences")
            
            conn.commit()
            print("✅ Preference data backup completed")
            return True
            
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return False

def remove_user_preference_columns():
    """Remove religious preference columns from User table"""
    print("🔄 Removing user preference columns...")
    
    try:
        with sqlite3.connect("thywill.db") as conn:
            cursor = conn.cursor()
            
            # Check current schema
            cursor.execute("PRAGMA table_info(user)")
            columns = cursor.fetchall()
            
            # Filter out preference columns
            keep_columns = []
            for col in columns:
                col_name = col[1]
                if col_name not in ['religious_preference', 'prayer_style']:
                    keep_columns.append(col)
            
            if len(keep_columns) == len(columns):
                print("✅ User preference columns already removed")
                return True
            
            # Create new table without preference columns
            column_defs = []
            for col in keep_columns:
                col_def = f"{col[1]} {col[2]}"
                if col[3]:  # NOT NULL
                    col_def += " NOT NULL"
                if col[4] is not None:  # DEFAULT
                    col_def += f" DEFAULT {col[4]}"
                if col[5]:  # PRIMARY KEY
                    col_def += " PRIMARY KEY"
                column_defs.append(col_def)
            
            cursor.execute(f"""
                CREATE TABLE user_new (
                    {', '.join(column_defs)}
                )
            """)
            
            # Copy data to new table
            column_names = [col[1] for col in keep_columns]
            cursor.execute(f"""
                INSERT INTO user_new ({', '.join(column_names)})
                SELECT {', '.join(column_names)} FROM user
            """)
            
            # Replace old table
            cursor.execute("DROP TABLE user")
            cursor.execute("ALTER TABLE user_new RENAME TO user")
            
            # Recreate indexes
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_display_name_unique ON user(display_name)")
            
            conn.commit()
            print("✅ User preference columns removed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error removing user columns: {e}")
        return False

def remove_prayer_target_audience():
    """Remove target_audience column from Prayer table"""
    print("🔄 Removing prayer target_audience column...")
    
    try:
        with sqlite3.connect("thywill.db") as conn:
            cursor = conn.cursor()
            
            # Check current schema
            cursor.execute("PRAGMA table_info(prayer)")
            columns = cursor.fetchall()
            
            # Filter out target_audience column
            keep_columns = []
            for col in columns:
                if col[1] != 'target_audience':
                    keep_columns.append(col)
            
            if len(keep_columns) == len(columns):
                print("✅ Prayer target_audience column already removed")
                return True
            
            # Create new table without target_audience
            column_defs = []
            for col in keep_columns:
                col_def = f"{col[1]} {col[2]}"
                if col[3]:  # NOT NULL
                    col_def += " NOT NULL"
                if col[4] is not None:  # DEFAULT
                    col_def += f" DEFAULT {col[4]}"
                if col[5]:  # PRIMARY KEY
                    col_def += " PRIMARY KEY"
                column_defs.append(col_def)
            
            cursor.execute(f"""
                CREATE TABLE prayer_new (
                    {', '.join(column_defs)}
                )
            """)
            
            # Copy data to new table
            column_names = [col[1] for col in keep_columns]
            cursor.execute(f"""
                INSERT INTO prayer_new ({', '.join(column_names)})
                SELECT {', '.join(column_names)} FROM prayer
            """)
            
            # Replace old table
            cursor.execute("DROP TABLE prayer")
            cursor.execute("ALTER TABLE prayer_new RENAME TO prayer")
            
            conn.commit()
            print("✅ Prayer target_audience column removed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Error removing prayer column: {e}")
        return False

def verify_removal():
    """Verify that preference columns have been removed"""
    print("🔍 Verifying preference column removal...")
    
    try:
        with sqlite3.connect("thywill.db") as conn:
            cursor = conn.cursor()
            
            # Check user table
            cursor.execute("PRAGMA table_info(user)")
            user_columns = [col[1] for col in cursor.fetchall()]
            
            # Check prayer table
            cursor.execute("PRAGMA table_info(prayer)")
            prayer_columns = [col[1] for col in cursor.fetchall()]
            
            # Verify removal
            removed_columns = []
            if 'religious_preference' not in user_columns:
                removed_columns.append('user.religious_preference')
            if 'prayer_style' not in user_columns:
                removed_columns.append('user.prayer_style')
            if 'target_audience' not in prayer_columns:
                removed_columns.append('prayer.target_audience')
            
            still_present = []
            if 'religious_preference' in user_columns:
                still_present.append('user.religious_preference')
            if 'prayer_style' in user_columns:
                still_present.append('user.prayer_style')
            if 'target_audience' in prayer_columns:
                still_present.append('prayer.target_audience')
            
            if still_present:
                print(f"❌ Columns still present: {', '.join(still_present)}")
                return False
            
            print(f"✅ Successfully removed columns: {', '.join(removed_columns)}")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying removal: {e}")
        return False

def main():
    """Main migration execution"""
    print("=" * 60)
    print("RELIGIOUS PREFERENCE REMOVAL MIGRATION")
    print("=" * 60)
    
    try:
        # Step 1: Backup preference data
        if not backup_preference_data():
            print("❌ Migration failed at backup step")
            return False
        
        # Step 2: Remove user preference columns
        if not remove_user_preference_columns():
            print("❌ Migration failed at user column removal step")
            return False
        
        # Step 3: Remove prayer target audience column
        if not remove_prayer_target_audience():
            print("❌ Migration failed at prayer column removal step")
            return False
        
        # Step 4: Verify removal
        if not verify_removal():
            print("❌ Migration failed at verification step")
            return False
        
        print("\n✅ Migration completed successfully!")
        print("Religious preference system has been completely removed.")
        print("Backup data is preserved in *_backup tables for recovery if needed.")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)