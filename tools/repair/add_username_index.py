#!/usr/bin/env python3
"""
Add Database Index for Username Performance

This script adds a database index on user.display_name to improve the performance
of username-to-ID resolution, which is critical for the archive reconstruction process.

The index will significantly speed up:
- Username lookups during import processes
- Orphaned data reconstruction
- User resolution in authentication flows
"""

import os
import sys
import logging
from sqlmodel import Session, text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def add_username_index():
    """Add database index on user.display_name for performance"""
    
    with Session(engine) as session:
        try:
            # Check if index already exists
            result = session.exec(text("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_user_display_name'
            """)).first()
            
            if result:
                logger.info("Index idx_user_display_name already exists")
                return True
            
            # Create the index
            logger.info("Creating index on user.display_name...")
            session.exec(text("""
                CREATE INDEX idx_user_display_name ON user(display_name)
            """))
            
            # Also create a case-insensitive index for better username resolution
            logger.info("Creating case-insensitive index on user.display_name...")
            session.exec(text("""
                CREATE INDEX idx_user_display_name_lower ON user(LOWER(display_name))
            """))
            
            session.commit()
            logger.info("Successfully created username performance indexes")
            
            # Verify the indexes were created
            indexes = session.exec(text("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name LIKE 'idx_user_display_name%'
            """)).all()
            
            logger.info(f"Created indexes: {[idx for idx in indexes]}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create username index: {e}")
            return False


def main():
    """Main function"""
    logger.info("Adding database index for username performance...")
    
    success = add_username_index()
    
    if success:
        print("✅ Username performance indexes added successfully")
        return 0
    else:
        print("❌ Failed to add username indexes")
        return 1


if __name__ == '__main__':
    sys.exit(main())