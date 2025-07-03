#!/usr/bin/env python3
"""
Safe startup script for ThyWill application.
Includes database protection and proper initialization.
"""

import os
import sys
from pathlib import Path

def check_database_exists():
    """Check if database exists and is properly initialized"""
    db_path = Path("thywill.db")
    return db_path.exists() and db_path.stat().st_size > 0

def safe_startup():
    """Safely start the application with database protection"""
    print("🚀 Starting ThyWill application...")
    
    # Check if database exists
    if not check_database_exists():
        print("⚠️  Database not found or empty.")
        print("Use 'python init_database.py' to create the initial database.")
        print("Or set INIT_DATABASE=true to create tables on startup.")
        
        if os.getenv('INIT_DATABASE', 'false').lower() != 'true':
            print("❌ Startup aborted to prevent data loss.")
            sys.exit(1)
    
    # Set production flag if not set
    if 'ENVIRONMENT' not in os.environ:
        os.environ['ENVIRONMENT'] = 'production'
    
    # Import and start the app
    print("✅ Database protection active")
    print("✅ Starting application server...")
    
    # Start the app (replace this with your actual startup code)
    from app import app
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    safe_startup()