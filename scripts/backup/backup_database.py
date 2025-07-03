#!/usr/bin/env python3
"""
Database backup utility for ThyWill
Creates timestamped backups of the production database
"""

import os
import shutil
import time
from pathlib import Path
from datetime import datetime

def create_backup():
    """Create a timestamped backup of the database"""
    db_path = Path("thywill.db")
    
    if not db_path.exists():
        print("❌ Database file not found: thywill.db")
        return False
    
    # Create backups directory if it doesn't exist
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    # Create timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"thywill_backup_{timestamp}.db"
    
    try:
        # Copy database file
        shutil.copy2(db_path, backup_path)
        
        # Get file sizes for verification
        original_size = db_path.stat().st_size
        backup_size = backup_path.stat().st_size
        
        if original_size == backup_size:
            print(f"✅ Backup created successfully: {backup_path}")
            print(f"   Database size: {original_size:,} bytes")
            return True
        else:
            print(f"❌ Backup verification failed (size mismatch)")
            backup_path.unlink()  # Delete failed backup
            return False
            
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def list_backups():
    """List all available backups"""
    backup_dir = Path("backups")
    
    if not backup_dir.exists():
        print("No backups directory found")
        return
    
    backups = list(backup_dir.glob("thywill_backup_*.db"))
    
    if not backups:
        print("No backups found")
        return
    
    print("Available backups:")
    for backup in sorted(backups, reverse=True):
        size = backup.stat().st_size
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"  {backup.name} ({size:,} bytes, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")

def restore_backup(backup_filename: str):
    """Restore from a backup file"""
    backup_path = Path("backups") / backup_filename
    
    if not backup_path.exists():
        print(f"❌ Backup file not found: {backup_path}")
        return False
    
    db_path = Path("thywill.db")
    
    # Create backup of current database before restore
    if db_path.exists():
        current_backup = f"thywill_before_restore_{int(time.time())}.db"
        shutil.copy2(db_path, Path("backups") / current_backup)
        print(f"📁 Current database backed up as: {current_backup}")
    
    try:
        # Restore the backup
        shutil.copy2(backup_path, db_path)
        print(f"✅ Database restored from: {backup_filename}")
        return True
        
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python backup_database.py create       # Create new backup")
        print("  python backup_database.py list         # List all backups")
        print("  python backup_database.py restore <filename>  # Restore from backup")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        create_backup()
    elif command == "list":
        list_backups()
    elif command == "restore" and len(sys.argv) >= 3:
        restore_backup(sys.argv[2])
    else:
        print("Invalid command or missing filename for restore")
        sys.exit(1)