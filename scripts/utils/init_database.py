#!/usr/bin/env python3
"""
Safe database initialization script.
Only use this to create initial database schema.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def init_database():
    """Safely initialize database tables"""
    db_path = Path("thywill.db")
    
    if db_path.exists():
        response = input(f"Database {db_path} already exists. Are you sure you want to recreate it? (yes/no): ")
        if response.lower() != 'yes':
            print("Database initialization cancelled.")
            return False
        
        # Backup existing database
        backup_path = f"thywill_backup_{int(time.time())}.db"
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Backup created: {backup_path}")
    
    # Set environment variable to trigger database creation
    os.environ['INIT_DATABASE'] = 'true'
    
    # Import models to trigger table creation
    from models import engine
    from sqlmodel import SQLModel
    
    print("Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("✅ Database initialization complete!")
    
    return True

if __name__ == "__main__":
    import time
    init_database()