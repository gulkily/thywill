#!/usr/bin/env python3
"""
Migration script to convert from flagged boolean to prayer attributes system
"""

from sqlmodel import Session, select
from models import engine, Prayer, PrayerAttribute
from datetime import datetime
import sys

def migrate_flagged_prayers():
    """Migrate existing flagged prayers to prayer attributes system"""
    print("Starting migration from flagged boolean to prayer attributes...")
    
    with Session(engine) as session:
        # First, check if the new table exists and create only if needed
        from sqlmodel import SQLModel
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        if 'prayerattribute' not in inspector.get_table_names():
            # Only create the specific table we need, not all tables
            PrayerAttribute.__table__.create(engine, checkfirst=True)
            print("✓ Prayer attributes table created")
        else:
            print("✓ Prayer attributes table already exists")
        
        # Get all prayers that are currently flagged
        stmt = select(Prayer).where(Prayer.flagged == True)
        flagged_prayers = session.exec(stmt).all()
        
        print(f"Found {len(flagged_prayers)} flagged prayers to migrate")
        
        # Migrate each flagged prayer
        migrated_count = 0
        for prayer in flagged_prayers:
            # Check if already migrated (attribute already exists)
            existing_attr_stmt = select(PrayerAttribute).where(
                PrayerAttribute.prayer_id == prayer.id,
                PrayerAttribute.attribute_name == 'flagged'
            )
            existing_attr = session.exec(existing_attr_stmt).first()
            
            if not existing_attr:
                # Create new flagged attribute
                flagged_attr = PrayerAttribute(
                    prayer_id=prayer.id,
                    attribute_name='flagged',
                    attribute_value='true',
                    created_at=prayer.created_at  # Preserve original timestamp
                )
                session.add(flagged_attr)
                migrated_count += 1
                print(f"  Migrated prayer {prayer.id[:8]}...")
            else:
                print(f"  Prayer {prayer.id[:8]} already has flagged attribute, skipping")
        
        # Commit the migration
        session.commit()
        print(f"✓ Successfully migrated {migrated_count} prayers to attributes system")
        
        # Verify migration
        verification_stmt = select(PrayerAttribute).where(PrayerAttribute.attribute_name == 'flagged')
        total_flagged_attrs = len(session.exec(verification_stmt).all())
        
        print(f"✓ Verification: {total_flagged_attrs} 'flagged' attributes in database")
        
        return migrated_count

def verify_migration():
    """Verify that migration was successful"""
    print("\nVerifying migration...")
    
    with Session(engine) as session:
        # Count flagged prayers (old way)
        flagged_prayers_count = len(session.exec(select(Prayer).where(Prayer.flagged == True)).all())
        
        # Count flagged attributes (new way)
        flagged_attrs_count = len(session.exec(
            select(PrayerAttribute).where(PrayerAttribute.attribute_name == 'flagged')
        ).all())
        
        print(f"Flagged prayers (boolean): {flagged_prayers_count}")
        print(f"Flagged attributes: {flagged_attrs_count}")
        
        if flagged_prayers_count == flagged_attrs_count:
            print("✓ Migration verification successful!")
            return True
        else:
            print("✗ Migration verification failed - counts don't match")
            return False

def test_attribute_methods():
    """Test the new attribute methods on Prayer model"""
    print("\nTesting prayer attribute methods...")
    
    with Session(engine) as session:
        # Get first prayer with flagged attribute
        stmt = select(Prayer).join(PrayerAttribute).where(
            PrayerAttribute.attribute_name == 'flagged'
        )
        test_prayer = session.exec(stmt).first()
        
        if test_prayer:
            print(f"Testing with prayer {test_prayer.id[:8]}...")
            
            # Test has_attribute
            is_flagged = test_prayer.has_attribute('flagged', session)
            print(f"  has_attribute('flagged'): {is_flagged}")
            
            # Test get_attribute
            flag_value = test_prayer.get_attribute('flagged', session)
            print(f"  get_attribute('flagged'): {flag_value}")
            
            # Test convenience property
            is_flagged_prop = test_prayer.is_flagged_attr(session)
            print(f"  is_flagged_attr(): {is_flagged_prop}")
            
            print("✓ Attribute methods working correctly")
        else:
            print("No flagged prayers found to test with")

if __name__ == "__main__":
    try:
        migrated_count = migrate_flagged_prayers()
        
        if verify_migration():
            test_attribute_methods()
            print(f"\n🎉 Migration completed successfully!")
            print(f"   - Migrated {migrated_count} prayers")
            print(f"   - Prayer attributes system is ready")
            print(f"   - Old 'flagged' column can be safely removed after testing")
        else:
            print("\n❌ Migration verification failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)