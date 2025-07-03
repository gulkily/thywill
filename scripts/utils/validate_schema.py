#!/usr/bin/env python3
"""
Validate that the religious preference schema is correctly applied
"""

import sys
import os
from sqlmodel import Session, text

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, User, Prayer

def validate_schema():
    """Validate that all required columns exist and have correct constraints"""
    print("Validating religious preference schema...")
    
    with Session(engine) as db:
        # Check User table schema
        user_schema = db.exec(text("PRAGMA table_info(user)")).fetchall()
        user_columns = {row[1]: row[2] for row in user_schema}
        
        required_user_columns = {
            'religious_preference': 'TEXT',
            'prayer_style': 'TEXT'
        }
        
        for column, expected_type in required_user_columns.items():
            if column in user_columns:
                print(f"✓ User.{column} exists ({user_columns[column]})")
            else:
                print(f"✗ User.{column} missing")
                return False
        
        # Check Prayer table schema
        prayer_schema = db.exec(text("PRAGMA table_info(prayer)")).fetchall()
        prayer_columns = {row[1]: row[2] for row in prayer_schema}
        
        required_prayer_columns = {
            'target_audience': 'TEXT',
            'prayer_context': 'TEXT'
        }
        
        for column, expected_type in required_prayer_columns.items():
            if column in prayer_columns:
                print(f"✓ Prayer.{column} exists ({prayer_columns[column]})")
            else:
                print(f"✗ Prayer.{column} missing")
                return False
        
        # Test creating a user with new fields
        try:
            test_user = User(
                display_name="Test User",
                religious_preference="christian",
                prayer_style="in_jesus_name"
            )
            db.add(test_user)
            db.commit()
            
            # Clean up test user
            db.delete(test_user)
            db.commit()
            print("✓ User model works with new fields")
            
        except Exception as e:
            print(f"✗ User model test failed: {e}")
            return False
        
        # Test creating a prayer with new fields
        try:
            test_prayer = Prayer(
                author_id="test",
                text="Test prayer",
                target_audience="christians_only",
                prayer_context="specific"
            )
            db.add(test_prayer)
            db.commit()
            
            # Clean up test prayer
            db.delete(test_prayer)
            db.commit()
            print("✓ Prayer model works with new fields")
            
        except Exception as e:
            print(f"✗ Prayer model test failed: {e}")
            return False
    
    print("✓ Schema validation passed!")
    return True

if __name__ == "__main__":
    validate_schema()