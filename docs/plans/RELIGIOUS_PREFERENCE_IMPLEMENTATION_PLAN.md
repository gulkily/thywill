# Religious Preference Feature - 3-Stage Implementation Plan

## Overview

This document provides a detailed 3-stage implementation plan for the religious preference feature, building on the design proposal. Each stage includes specific deliverables, testing requirements, and success criteria.

## Stage 1: Database Schema and Migration (Week 1)

### Objectives
- Add new database fields for religious preferences
- Create and test migration scripts
- Ensure backward compatibility with existing data

### Deliverables

#### 1.1 Model Updates (`models.py`)
```python
# Add to User model (line 6)
class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    display_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # New fields for religious preferences
    religious_preference: str | None = Field(default="unspecified", max_length=50)
    prayer_style: str | None = Field(default=None, max_length=100)

# Add to Prayer model (line 11)
class Prayer(SQLModel, table=True):
    # ... existing fields ...
    # New fields for prayer targeting
    target_audience: str | None = Field(default="all", max_length=50)
    prayer_context: str | None = Field(default=None, max_length=100)
```

#### 1.2 Migration Script (`migrate_religious_preferences.py`)
```python
#!/usr/bin/env python3
"""
Migration script for religious preference feature
Run this script to add new database columns for religious preferences
"""

import sys
import os
from sqlmodel import Session, text
from datetime import datetime

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, User, Prayer

def check_column_exists(session: Session, table_name: str, column_name: str) -> bool:
    """Check if a column exists in the given table"""
    result = session.exec(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(row[1] == column_name for row in result)

def migrate_religious_preferences():
    """Add religious preference columns to User and Prayer tables"""
    print("Starting religious preference migration...")
    
    with Session(engine) as db:
        try:
            # Check and add User table columns
            if not check_column_exists(db, "user", "religious_preference"):
                db.exec(text("ALTER TABLE user ADD COLUMN religious_preference TEXT DEFAULT 'unspecified'"))
                print("✓ Added religious_preference column to user table")
            else:
                print("- religious_preference column already exists in user table")
                
            if not check_column_exists(db, "user", "prayer_style"):
                db.exec(text("ALTER TABLE user ADD COLUMN prayer_style TEXT DEFAULT NULL"))
                print("✓ Added prayer_style column to user table")
            else:
                print("- prayer_style column already exists in user table")
            
            # Check and add Prayer table columns
            if not check_column_exists(db, "prayer", "target_audience"):
                db.exec(text("ALTER TABLE prayer ADD COLUMN target_audience TEXT DEFAULT 'all'"))
                print("✓ Added target_audience column to prayer table")
            else:
                print("- target_audience column already exists in prayer table")
                
            if not check_column_exists(db, "prayer", "prayer_context"):
                db.exec(text("ALTER TABLE prayer ADD COLUMN prayer_context TEXT DEFAULT NULL"))
                print("✓ Added prayer_context column to prayer table")
            else:
                print("- prayer_context column already exists in prayer table")
            
            db.commit()
            print("✓ Migration completed successfully")
            
            # Verify the migration
            user_count = db.exec(text("SELECT COUNT(*) FROM user")).first()
            prayer_count = db.exec(text("SELECT COUNT(*) FROM prayer")).first()
            print(f"✓ Verified: {user_count} users and {prayer_count} prayers migrated")
            
        except Exception as e:
            db.rollback()
            print(f"✗ Migration failed: {e}")
            raise
    
    print("Migration completed!")

def rollback_migration():
    """Remove religious preference columns (for testing purposes)"""
    print("Rolling back religious preference migration...")
    
    with Session(engine) as db:
        try:
            # Note: SQLite doesn't support DROP COLUMN, so we'd need to recreate tables
            # This is primarily for development/testing purposes
            print("Warning: SQLite doesn't support DROP COLUMN")
            print("To fully rollback, restore from backup or recreate database")
            
        except Exception as e:
            print(f"✗ Rollback failed: {e}")
            raise

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        migrate_religious_preferences()
```

#### 1.3 Schema Validation Script (`validate_schema.py`)
```python
#!/usr/bin/env python3
"""
Validate that the religious preference schema is correctly applied
"""

from sqlmodel import Session, text
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
```

### Testing Requirements

#### 1.4 Unit Tests for Schema (`tests/unit/test_religious_preference_schema.py`)
```python
"""Unit tests for religious preference database schema"""
import pytest
from datetime import datetime
from sqlmodel import Session, select, text

from models import User, Prayer, engine
from tests.factories import UserFactory, PrayerFactory


@pytest.mark.unit
class TestReligiousPreferenceSchema:
    """Test religious preference database schema"""
    
    def test_user_model_has_religious_preference_fields(self, test_session):
        """Test that User model has religious preference fields with correct defaults"""
        user = User(display_name="Test User")
        test_session.add(user)
        test_session.commit()
        
        # Test defaults
        assert user.religious_preference == "unspecified"
        assert user.prayer_style is None
    
    def test_user_religious_preference_validation(self, test_session):
        """Test religious preference field accepts valid values"""
        valid_preferences = ["christian", "non_christian", "unspecified"]
        
        for preference in valid_preferences:
            user = User(
                display_name=f"User {preference}",
                religious_preference=preference
            )
            test_session.add(user)
            test_session.commit()
            
            retrieved_user = test_session.get(User, user.id)
            assert retrieved_user.religious_preference == preference
    
    def test_user_prayer_style_for_christians(self, test_session):
        """Test prayer style field for Christian users"""
        user = User(
            display_name="Christian User",
            religious_preference="christian",
            prayer_style="in_jesus_name"
        )
        test_session.add(user)
        test_session.commit()
        
        retrieved_user = test_session.get(User, user.id)
        assert retrieved_user.prayer_style == "in_jesus_name"
    
    def test_prayer_model_has_target_audience_fields(self, test_session):
        """Test that Prayer model has target audience fields with correct defaults"""
        prayer = Prayer(
            author_id="test_user",
            text="Test prayer"
        )
        test_session.add(prayer)
        test_session.commit()
        
        # Test defaults
        assert prayer.target_audience == "all"
        assert prayer.prayer_context is None
    
    def test_prayer_target_audience_validation(self, test_session):
        """Test target audience field accepts valid values"""
        valid_audiences = ["all", "christians_only", "non_christians_only"]
        
        for audience in valid_audiences:
            prayer = Prayer(
                author_id="test_user",
                text=f"Prayer for {audience}",
                target_audience=audience
            )
            test_session.add(prayer)
            test_session.commit()
            
            retrieved_prayer = test_session.get(Prayer, prayer.id)
            assert retrieved_prayer.target_audience == audience
    
    def test_migration_preserves_existing_data(self, test_session):
        """Test that migration preserves existing user and prayer data"""
        # Create user without religious preference (simulating pre-migration data)
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Verify existing data is preserved
        retrieved_user = test_session.get(User, user.id)
        retrieved_prayer = test_session.get(Prayer, prayer.id)
        
        assert retrieved_user.display_name == user.display_name
        assert retrieved_prayer.text == prayer.text
        
        # Verify new fields have default values
        assert retrieved_user.religious_preference == "unspecified"
        assert retrieved_prayer.target_audience == "all"


@pytest.mark.integration  
class TestReligiousPreferenceMigration:
    """Integration tests for migration script"""
    
    def test_migration_script_execution(self):
        """Test that migration script runs without errors"""
        # This would test the actual migration script
        # In practice, this might involve creating a test database
        # and running the migration script against it
        pass
    
    def test_schema_validation_after_migration(self):
        """Test that schema validation passes after migration"""
        # This would test the validate_schema.py script
        pass
```

### Success Criteria
- ✅ Migration script runs without errors on development database
- ✅ All existing data preserved during migration
- ✅ New fields have correct defaults and constraints
- ✅ Schema validation script passes
- ✅ Unit tests pass for new schema
- ✅ No breaking changes to existing functionality

---

## Stage 2: Backend Logic and API (Week 2)

### Objectives
- Implement prayer filtering logic based on religious preferences
- Create API endpoints for managing user preferences
- Update existing prayer creation and assignment logic

### Deliverables

#### 2.1 Core Filtering Functions (`app.py` additions)
```python
# Add these functions to app.py after line 100

def get_filtered_prayers_for_user(user: User, db: Session, include_archived: bool = False, include_answered: bool = False) -> list[Prayer]:
    """Get prayers filtered based on user's religious preferences and attributes"""
    
    # Base query for non-flagged prayers
    base_query = select(Prayer).where(Prayer.flagged == False)
    
    # Apply attribute filtering
    excluded_attributes = []
    if not include_archived:
        excluded_attributes.append('archived')
    if not include_answered:
        excluded_attributes.append('answered')
    
    if excluded_attributes:
        excluded_prayer_ids = db.exec(
            select(PrayerAttribute.prayer_id).where(
                PrayerAttribute.attribute_name.in_(excluded_attributes)
            )
        ).all()
        
        if excluded_prayer_ids:
            base_query = base_query.where(~Prayer.id.in_(excluded_prayer_ids))
    
    # Apply religious preference filtering
    if user.religious_preference == "christian":
        # Christians see: all prayers + christian-only prayers
        base_query = base_query.where(
            Prayer.target_audience.in_(["all", "christians_only"])
        )
    elif user.religious_preference == "non_christian":
        # Non-Christians see: all prayers + non-christian-only prayers  
        base_query = base_query.where(
            Prayer.target_audience.in_(["all", "non_christians_only"])
        )
    else:
        # Unspecified users see only "all" prayers
        base_query = base_query.where(Prayer.target_audience == "all")
    
    return db.exec(base_query.order_by(Prayer.created_at.desc())).all()

def find_compatible_prayer_partner(prayer: Prayer, db: Session, exclude_user_ids: list[str] = None) -> User | None:
    """Find a user compatible with the prayer's religious targeting requirements"""
    
    # Build user query based on prayer target audience
    user_query = select(User)
    
    # Apply religious compatibility filtering
    if prayer.target_audience == "christians_only":
        user_query = user_query.where(User.religious_preference == "christian")
    elif prayer.target_audience == "non_christians_only":
        user_query = user_query.where(User.religious_preference == "non_christian")
    # For "all", no additional religious filtering needed
    
    # Exclude users who have already been assigned this prayer
    assigned_user_ids = db.exec(
        select(PrayerMark.user_id).where(PrayerMark.prayer_id == prayer.id)
    ).all()
    
    # Add additional exclusions if provided
    if exclude_user_ids:
        assigned_user_ids.extend(exclude_user_ids)
    
    if assigned_user_ids:
        user_query = user_query.where(~User.id.in_(assigned_user_ids))
    
    # Exclude the prayer author
    user_query = user_query.where(User.id != prayer.author_id)
    
    return db.exec(user_query).first()

def get_religious_preference_stats(db: Session) -> dict:
    """Get statistics about religious preference distribution"""
    stats = {}
    
    # User preference distribution
    user_prefs = db.exec(
        text("SELECT religious_preference, COUNT(*) FROM user GROUP BY religious_preference")
    ).fetchall()
    stats['user_preferences'] = {pref: count for pref, count in user_prefs}
    
    # Prayer target audience distribution
    prayer_targets = db.exec(
        text("SELECT target_audience, COUNT(*) FROM prayer GROUP BY target_audience")
    ).fetchall()
    stats['prayer_targets'] = {target: count for target, count in prayer_targets}
    
    return stats
```

#### 2.2 User Preference Management API
```python
# Add these endpoints to app.py

@app.get("/profile/preferences")
async def get_user_preferences(request: Request):
    """Display user religious preference settings"""
    user = require_full_auth(request)
    
    with Session(engine) as db:
        db_user = db.get(User, user.id)
        return templates.TemplateResponse("preferences.html", {
            "request": request,
            "user": db_user
        })

@app.post("/profile/preferences")
async def update_religious_preferences(
    request: Request,
    religious_preference: str = Form(...),
    prayer_style: str = Form(None)
):
    """Update user's religious preferences"""
    user = require_full_auth(request)
    
    # Validate religious preference
    valid_preferences = ["christian", "non_christian", "unspecified"]
    if religious_preference not in valid_preferences:
        raise HTTPException(400, "Invalid religious preference")
    
    # Validate prayer style for Christians
    valid_prayer_styles = ["in_jesus_name", "interfaith", None, ""]
    if prayer_style and prayer_style not in valid_prayer_styles:
        raise HTTPException(400, "Invalid prayer style")
    
    with Session(engine) as db:
        db_user = db.get(User, user.id)
        old_preference = db_user.religious_preference
        old_style = db_user.prayer_style
        
        db_user.religious_preference = religious_preference
        
        # Only set prayer style for Christian users
        if religious_preference == "christian":
            db_user.prayer_style = prayer_style if prayer_style else None
        else:
            db_user.prayer_style = None
        
        db.add(db_user)
        db.commit()
        
        # Log the preference change for analytics
        print(f"User {user.id} changed preference: {old_preference} -> {religious_preference}, style: {old_style} -> {db_user.prayer_style}")
    
    return RedirectResponse("/profile", status_code=303)

@app.get("/api/religious-stats")
async def get_religious_stats(request: Request):
    """Get religious preference statistics (admin only)"""
    user = require_full_auth(request)
    
    if not is_admin(user):
        raise HTTPException(403, "Admin access required")
    
    with Session(engine) as db:
        stats = get_religious_preference_stats(db)
        return stats
```

#### 2.3 Enhanced Prayer Creation
```python
# Update the existing create_prayer endpoint in app.py

@app.post("/prayers")
async def create_prayer(
    request: Request,
    text: str = Form(...),
    target_audience: str = Form("all"),
    project_tag: str = Form(None),
    prayer_context: str = Form(None)
):
    """Create a new prayer with religious targeting options"""
    user = require_full_auth(request)
    
    # Validate target audience
    valid_audiences = ["all", "christians_only", "non_christians_only"]
    if target_audience not in valid_audiences:
        target_audience = "all"
    
    # Validate prayer context length
    if prayer_context and len(prayer_context) > 100:
        prayer_context = prayer_context[:100]
    
    with Session(engine) as db:
        prayer = Prayer(
            author_id=user.id,
            text=text,
            target_audience=target_audience,
            prayer_context=prayer_context,
            project_tag=project_tag
        )
        db.add(prayer)
        db.commit()
        
        # Try to find a compatible prayer partner immediately
        compatible_user = find_compatible_prayer_partner(prayer, db)
        if compatible_user:
            # Assign prayer to compatible user
            mark = PrayerMark(user_id=compatible_user.id, prayer_id=prayer.id)
            db.add(mark)
            db.commit()
            print(f"Prayer {prayer.id} assigned to compatible user {compatible_user.id}")
    
    return RedirectResponse("/feed", status_code=303)
```

#### 2.4 Updated Feed Logic
```python
# Update the existing feed endpoint in app.py

@app.get("/feed")
async def feed(request: Request):
    """Display prayer feed filtered by user's religious preferences"""
    user = require_full_auth(request)
    
    with Session(engine) as db:
        # Get user's prayers with religious filtering
        prayers = get_filtered_prayers_for_user(user, db, include_archived=False, include_answered=False)
        
        # Get user's prayer marks for displaying status
        user_marks = db.exec(
            select(PrayerMark.prayer_id).where(PrayerMark.user_id == user.id)
        ).all()
        
        # Get prayer counts for navigation
        total_count = len(prayers)
        answered_prayers = get_filtered_prayers_for_user(user, db, include_answered=True, include_archived=False)
        answered_count = len([p for p in answered_prayers if p.is_answered(db)])
        archived_prayers = get_filtered_prayers_for_user(user, db, include_archived=True, include_answered=False)
        archived_count = len([p for p in archived_prayers if p.is_archived(db)])
        
        return templates.TemplateResponse("feed.html", {
            "request": request,
            "user": user,
            "prayers": prayers,
            "user_marks": user_marks,
            "total_count": total_count,
            "answered_count": answered_count,
            "archived_count": archived_count
        })
```

### Testing Requirements

#### 2.5 Unit Tests for Filtering Logic (`tests/unit/test_religious_preference_filtering.py`)
```python
"""Unit tests for religious preference filtering logic"""
import pytest
from sqlmodel import Session

from models import User, Prayer, PrayerMark
from tests.factories import UserFactory, PrayerFactory
from app import get_filtered_prayers_for_user, find_compatible_prayer_partner


@pytest.mark.unit
class TestReligiousPreferenceFiltering:
    """Test religious preference-based prayer filtering"""
    
    def test_christian_user_sees_all_and_christian_only_prayers(self, test_session):
        """Christian users should see 'all' and 'christians_only' prayers"""
        christian_user = UserFactory.create(religious_preference="christian")
        
        all_prayer = PrayerFactory.create(target_audience="all")
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        non_christian_prayer = PrayerFactory.create(target_audience="non_christians_only")
        
        test_session.add_all([christian_user, all_prayer, christian_prayer, non_christian_prayer])
        test_session.commit()
        
        filtered_prayers = get_filtered_prayers_for_user(christian_user, test_session)
        prayer_ids = [p.id for p in filtered_prayers]
        
        assert all_prayer.id in prayer_ids
        assert christian_prayer.id in prayer_ids
        assert non_christian_prayer.id not in prayer_ids
    
    def test_non_christian_user_sees_all_and_non_christian_only_prayers(self, test_session):
        """Non-Christian users should see 'all' and 'non_christians_only' prayers"""
        non_christian_user = UserFactory.create(religious_preference="non_christian")
        
        all_prayer = PrayerFactory.create(target_audience="all")
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        non_christian_prayer = PrayerFactory.create(target_audience="non_christians_only")
        
        test_session.add_all([non_christian_user, all_prayer, christian_prayer, non_christian_prayer])
        test_session.commit()
        
        filtered_prayers = get_filtered_prayers_for_user(non_christian_user, test_session)
        prayer_ids = [p.id for p in filtered_prayers]
        
        assert all_prayer.id in prayer_ids
        assert christian_prayer.id not in prayer_ids
        assert non_christian_prayer.id in prayer_ids
    
    def test_unspecified_user_sees_only_all_prayers(self, test_session):
        """Users with unspecified preference should see only 'all' prayers"""
        unspecified_user = UserFactory.create(religious_preference="unspecified")
        
        all_prayer = PrayerFactory.create(target_audience="all")
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        non_christian_prayer = PrayerFactory.create(target_audience="non_christians_only")
        
        test_session.add_all([unspecified_user, all_prayer, christian_prayer, non_christian_prayer])
        test_session.commit()
        
        filtered_prayers = get_filtered_prayers_for_user(unspecified_user, test_session)
        prayer_ids = [p.id for p in filtered_prayers]
        
        assert all_prayer.id in prayer_ids
        assert christian_prayer.id not in prayer_ids
        assert non_christian_prayer.id not in prayer_ids
    
    def test_find_compatible_christian_prayer_partner(self, test_session):
        """Christian-only prayers should be assigned to Christian users"""
        christian_user = UserFactory.create(religious_preference="christian")
        non_christian_user = UserFactory.create(religious_preference="non_christian")
        unspecified_user = UserFactory.create(religious_preference="unspecified")
        
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        
        test_session.add_all([christian_user, non_christian_user, unspecified_user, christian_prayer])
        test_session.commit()
        
        compatible_user = find_compatible_prayer_partner(christian_prayer, test_session)
        
        assert compatible_user is not None
        assert compatible_user.religious_preference == "christian"
        assert compatible_user.id == christian_user.id
    
    def test_find_compatible_non_christian_prayer_partner(self, test_session):
        """Non-Christian-only prayers should be assigned to non-Christian users"""
        christian_user = UserFactory.create(religious_preference="christian")
        non_christian_user = UserFactory.create(religious_preference="non_christian")
        
        non_christian_prayer = PrayerFactory.create(target_audience="non_christians_only")
        
        test_session.add_all([christian_user, non_christian_user, non_christian_prayer])
        test_session.commit()
        
        compatible_user = find_compatible_prayer_partner(non_christian_prayer, test_session)
        
        assert compatible_user is not None
        assert compatible_user.religious_preference == "non_christian"
        assert compatible_user.id == non_christian_user.id
    
    def test_all_audience_prayer_matches_any_user(self, test_session):
        """'All' audience prayers can be assigned to any user"""
        christian_user = UserFactory.create(religious_preference="christian")
        non_christian_user = UserFactory.create(religious_preference="non_christian")
        unspecified_user = UserFactory.create(religious_preference="unspecified")
        
        all_prayer = PrayerFactory.create(target_audience="all")
        
        test_session.add_all([christian_user, non_christian_user, unspecified_user, all_prayer])
        test_session.commit()
        
        compatible_user = find_compatible_prayer_partner(all_prayer, test_session)
        
        assert compatible_user is not None
        assert compatible_user.id in [christian_user.id, non_christian_user.id, unspecified_user.id]
    
    def test_excludes_users_who_already_have_prayer(self, test_session):
        """Prayer partner matching should exclude users who already have the prayer"""
        christian_user1 = UserFactory.create(religious_preference="christian")
        christian_user2 = UserFactory.create(religious_preference="christian")
        
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        
        # User1 already has this prayer
        existing_mark = PrayerMark(user_id=christian_user1.id, prayer_id=christian_prayer.id)
        
        test_session.add_all([christian_user1, christian_user2, christian_prayer, existing_mark])
        test_session.commit()
        
        compatible_user = find_compatible_prayer_partner(christian_prayer, test_session)
        
        assert compatible_user is not None
        assert compatible_user.id == christian_user2.id
```

#### 2.6 Integration Tests for API (`tests/integration/test_religious_preference_api.py`)
```python
"""Integration tests for religious preference API endpoints"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import app
from models import User, Prayer, engine
from tests.factories import UserFactory, PrayerFactory


@pytest.mark.integration
class TestReligiousPreferenceAPI:
    """Test religious preference API endpoints"""
    
    def test_update_user_religious_preference(self, test_session, test_client):
        """Test updating user religious preferences"""
        user = UserFactory.create(religious_preference="unspecified")
        test_session.add(user)
        test_session.commit()
        
        # Mock authentication
        with test_client.session_transaction() as sess:
            sess['user_id'] = user.id
        
        response = test_client.post("/profile/preferences", data={
            "religious_preference": "christian",
            "prayer_style": "in_jesus_name"
        })
        
        assert response.status_code == 303  # Redirect
        
        # Verify user was updated
        updated_user = test_session.get(User, user.id)
        assert updated_user.religious_preference == "christian"
        assert updated_user.prayer_style == "in_jesus_name"
    
    def test_create_prayer_with_target_audience(self, test_session, test_client):
        """Test creating prayer with target audience"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        # Mock authentication
        with test_client.session_transaction() as sess:
            sess['user_id'] = user.id
        
        response = test_client.post("/prayers", data={
            "text": "Please pray for my family",
            "target_audience": "christians_only",
            "prayer_context": "specific_need"
        })
        
        assert response.status_code == 303  # Redirect
        
        # Verify prayer was created with correct targeting
        prayer = test_session.exec(
            select(Prayer).where(Prayer.author_id == user.id)
        ).first()
        
        assert prayer is not None
        assert prayer.target_audience == "christians_only"
        assert prayer.prayer_context == "specific_need"
    
    def test_feed_filters_by_religious_preference(self, test_session, test_client):
        """Test that feed respects religious preference filtering"""
        christian_user = UserFactory.create(religious_preference="christian")
        
        all_prayer = PrayerFactory.create(target_audience="all")
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        non_christian_prayer = PrayerFactory.create(target_audience="non_christians_only")
        
        test_session.add_all([christian_user, all_prayer, christian_prayer, non_christian_prayer])
        test_session.commit()
        
        # Mock authentication
        with test_client.session_transaction() as sess:
            sess['user_id'] = christian_user.id
        
        response = test_client.get("/feed")
        assert response.status_code == 200
        
        # Check that response contains correct prayers
        content = response.content.decode()
        assert all_prayer.text in content
        assert christian_prayer.text in content
        assert non_christian_prayer.text not in content
```

### Success Criteria
- ✅ Prayer filtering works correctly for all user types
- ✅ Prayer partner matching respects religious compatibility
- ✅ API endpoints handle preference updates securely
- ✅ Enhanced prayer creation includes targeting options
- ✅ Feed displays correctly filtered content
- ✅ All unit and integration tests pass
- ✅ Existing functionality remains unaffected

---

## Stage 3: Frontend Interface and User Experience (Week 3)

### Objectives
- Create intuitive user interfaces for religious preference settings
- Update prayer submission forms with targeting options
- Ensure respectful and inclusive design language
- Conduct user acceptance testing

### Deliverables

#### 3.1 User Preference Settings Page (`templates/preferences.html`)
```html
{% extends "base.html" %}

{% block title %}Prayer Preferences{% endblock %}

{% block content %}
<div class="container max-w-2xl mx-auto p-6">
    <div class="bg-white rounded-lg shadow-md p-6">
        <h1 class="text-2xl font-bold text-gray-800 mb-6">Prayer Preferences</h1>
        
        <form method="POST" action="/profile/preferences" class="space-y-6">
            <div class="preference-section">
                <h3 class="text-lg font-semibold text-gray-700 mb-4">Religious Background</h3>
                <p class="text-sm text-gray-600 mb-4">
                    This helps us match you with prayers that align with your beliefs and prayer style. 
                    This setting is optional and can be changed at any time.
                </p>
                
                <div class="space-y-3">
                    <label class="flex items-center space-x-3 cursor-pointer">
                        <input type="radio" name="religious_preference" value="unspecified" 
                               {% if user.religious_preference == "unspecified" %}checked{% endif %}
                               class="w-4 h-4 text-blue-600">
                        <div>
                            <div class="font-medium">Prefer not to specify</div>
                            <div class="text-sm text-gray-500">You'll see prayers from all backgrounds</div>
                        </div>
                    </label>
                    
                    <label class="flex items-center space-x-3 cursor-pointer">
                        <input type="radio" name="religious_preference" value="christian" 
                               {% if user.religious_preference == "christian" %}checked{% endif %}
                               class="w-4 h-4 text-blue-600" id="christian_option">
                        <div>
                            <div class="font-medium">Christian</div>
                            <div class="text-sm text-gray-500">You'll see all prayers plus those specifically for Christians</div>
                        </div>
                    </label>
                    
                    <label class="flex items-center space-x-3 cursor-pointer">
                        <input type="radio" name="religious_preference" value="non_christian" 
                               {% if user.religious_preference == "non_christian" %}checked{% endif %}
                               class="w-4 h-4 text-blue-600">
                        <div>
                            <div class="font-medium">Non-Christian</div>
                            <div class="text-sm text-gray-500">You'll see general prayers and those open to all faiths</div>
                        </div>
                    </label>
                </div>
            </div>
            
            <div class="prayer-style-section" id="prayer_style_group" 
                 style="{% if user.religious_preference != 'christian' %}display: none;{% endif %}">
                <h3 class="text-lg font-semibold text-gray-700 mb-4">Prayer Style</h3>
                <p class="text-sm text-gray-600 mb-4">
                    How would you like to approach prayer for others?
                </p>
                
                <div class="space-y-3">
                    <label class="flex items-center space-x-3 cursor-pointer">
                        <input type="radio" name="prayer_style" value="" 
                               {% if not user.prayer_style %}checked{% endif %}
                               class="w-4 h-4 text-blue-600">
                        <div>
                            <div class="font-medium">Default approach</div>
                            <div class="text-sm text-gray-500">General Christian prayer style</div>
                        </div>
                    </label>
                    
                    <label class="flex items-center space-x-3 cursor-pointer">
                        <input type="radio" name="prayer_style" value="in_jesus_name" 
                               {% if user.prayer_style == "in_jesus_name" %}checked{% endif %}
                               class="w-4 h-4 text-blue-600">
                        <div>
                            <div class="font-medium">Pray in Jesus' name</div>
                            <div class="text-sm text-gray-500">Specifically pray through Jesus Christ</div>
                        </div>
                    </label>
                    
                    <label class="flex items-center space-x-3 cursor-pointer">
                        <input type="radio" name="prayer_style" value="interfaith" 
                               {% if user.prayer_style == "interfaith" %}checked{% endif %}
                               class="w-4 h-4 text-blue-600">
                        <div>
                            <div class="font-medium">Interfaith approach</div>
                            <div class="text-sm text-gray-500">Open to various Christian traditions</div>
                        </div>
                    </label>
                </div>
            </div>
            
            <div class="flex space-x-4 pt-6">
                <button type="submit" class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                    Save Preferences
                </button>
                <a href="/profile" class="bg-gray-300 text-gray-700 px-6 py-2 rounded-lg hover:bg-gray-400 transition-colors">
                    Cancel
                </a>
            </div>
        </form>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const religiousPreferenceInputs = document.querySelectorAll('input[name="religious_preference"]');
    const prayerStyleGroup = document.getElementById('prayer_style_group');
    
    religiousPreferenceInputs.forEach(input => {
        input.addEventListener('change', function() {
            if (this.value === 'christian') {
                prayerStyleGroup.style.display = 'block';
            } else {
                prayerStyleGroup.style.display = 'none';
                // Clear prayer style selection for non-Christians
                const prayerStyleInputs = document.querySelectorAll('input[name="prayer_style"]');
                prayerStyleInputs[0].checked = true; // Select default
            }
        });
    });
});
</script>
{% endblock %}
```

#### 3.2 Enhanced Prayer Form (`templates/components/prayer_form.html`)
```html
<form method="POST" action="/prayers" class="space-y-4">
    <div class="form-group">
        <label for="text" class="block text-sm font-medium text-gray-700 mb-2">
            Prayer Request
        </label>
        <textarea 
            name="text" 
            id="text" 
            rows="4" 
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Share what you'd like prayer for..."
        ></textarea>
    </div>
    
    <div class="form-group">
        <label for="target_audience" class="block text-sm font-medium text-gray-700 mb-2">
            Who should see this prayer request?
        </label>
        <select name="target_audience" id="target_audience" 
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
            <option value="all">Everyone in the community</option>
            <option value="christians_only">Christians only</option>
            <option value="non_christians_only">Non-Christians only</option>
        </select>
        
        <div class="help-text mt-2 text-sm text-gray-600">
            <div id="help_all" class="help-option">
                Your prayer will be visible to all community members regardless of their religious background.
            </div>
            <div id="help_christians" class="help-option" style="display: none;">
                Your prayer will only be shown to users who identify as Christian. This is useful when you'd like prayer specifically through Jesus Christ.
            </div>
            <div id="help_non_christians" class="help-option" style="display: none;">
                Your prayer will only be shown to users who identify as non-Christian or prefer not to specify their faith.
            </div>
        </div>
    </div>
    
    <div class="form-group">
        <label for="prayer_context" class="block text-sm font-medium text-gray-700 mb-2">
            Additional Context <span class="text-gray-500">(optional)</span>
        </label>
        <input 
            type="text" 
            name="prayer_context" 
            id="prayer_context"
            maxlength="100"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., urgent need, ongoing situation..."
        >
        <div class="text-xs text-gray-500 mt-1">Helps others understand how to pray for your request</div>
    </div>
    
    <div class="form-group">
        <label for="project_tag" class="block text-sm font-medium text-gray-700 mb-2">
            Project Tag <span class="text-gray-500">(optional)</span>
        </label>
        <input 
            type="text" 
            name="project_tag" 
            id="project_tag"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., family, health, work..."
        >
    </div>
    
    <button type="submit" class="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors">
        Submit Prayer Request
    </button>
</form>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const targetAudienceSelect = document.getElementById('target_audience');
    const helpTexts = {
        'all': document.getElementById('help_all'),
        'christians_only': document.getElementById('help_christians'),
        'non_christians_only': document.getElementById('help_non_christians')
    };
    
    targetAudienceSelect.addEventListener('change', function() {
        // Hide all help texts
        Object.values(helpTexts).forEach(help => help.style.display = 'none');
        
        // Show relevant help text
        const selectedHelp = helpTexts[this.value];
        if (selectedHelp) {
            selectedHelp.style.display = 'block';
        }
    });
});
</script>
```

#### 3.3 Enhanced Profile Page Link (`templates/profile.html` additions)
```html
<!-- Add this section to the existing profile.html -->
<div class="preference-link-section mt-6">
    <div class="bg-gray-50 rounded-lg p-4">
        <h3 class="text-lg font-semibold text-gray-800 mb-2">Prayer Preferences</h3>
        <p class="text-sm text-gray-600 mb-3">
            Current setting: 
            <span class="font-medium">
                {% if user.religious_preference == "christian" %}
                    Christian
                    {% if user.prayer_style == "in_jesus_name" %} - Pray in Jesus' name{% endif %}
                {% elif user.religious_preference == "non_christian" %}
                    Non-Christian
                {% else %}
                    Prefer not to specify
                {% endif %}
            </span>
        </p>
        <a href="/profile/preferences" class="text-blue-600 hover:text-blue-800 text-sm font-medium">
            Update Prayer Preferences →
        </a>
    </div>
</div>
```

#### 3.4 Prayer Card Display Enhancements (`templates/components/prayer_card.html`)
```html
<!-- Add targeting indicator to prayer cards -->
<div class="prayer-card bg-white rounded-lg shadow-sm border p-4 mb-4">
    <div class="prayer-header flex justify-between items-start mb-3">
        <div class="prayer-meta">
            <span class="text-sm text-gray-500">
                {{ prayer.created_at.strftime('%B %d, %Y at %I:%M %p') }}
            </span>
            {% if prayer.target_audience != "all" %}
                <span class="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                    {% if prayer.target_audience == "christians_only" %}
                        Christians
                    {% elif prayer.target_audience == "non_christians_only" %}
                        Open to all faiths
                    {% endif %}
                </span>
            {% endif %}
            {% if prayer.prayer_context %}
                <span class="ml-2 text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">
                    {{ prayer.prayer_context }}
                </span>
            {% endif %}
        </div>
    </div>
    
    <div class="prayer-content">
        <p class="text-gray-800 leading-relaxed">{{ prayer.text }}</p>
    </div>
    
    <!-- Rest of existing prayer card content -->
    <!-- ... existing buttons and actions ... -->
</div>
```

#### 3.5 Onboarding Enhancement for New Users
```html
<!-- Add to new user registration flow -->
<div class="welcome-preferences" id="religious_preference_onboarding">
    <h2 class="text-xl font-semibold text-gray-800 mb-4">Welcome to ThyWill!</h2>
    <p class="text-gray-600 mb-6">
        To help us provide the most meaningful prayer experience, you can optionally share your religious background. 
        This helps us match you with prayers that align with your beliefs.
    </p>
    
    <div class="space-y-3 mb-6">
        <label class="flex items-center space-x-3 cursor-pointer">
            <input type="radio" name="initial_religious_preference" value="unspecified" checked
                   class="w-4 h-4 text-blue-600">
            <span>I'll decide later</span>
        </label>
        
        <label class="flex items-center space-x-3 cursor-pointer">
            <input type="radio" name="initial_religious_preference" value="christian"
                   class="w-4 h-4 text-blue-600">
            <span>I'm Christian</span>
        </label>
        
        <label class="flex items-center space-x-3 cursor-pointer">
            <input type="radio" name="initial_religious_preference" value="non_christian"
                   class="w-4 h-4 text-blue-600">
            <span>I'm not Christian</span>
        </label>
    </div>
    
    <p class="text-sm text-gray-500 mb-4">
        Don't worry - you can always change this later in your profile settings, and all preferences are completely optional.
    </p>
    
    <button onclick="completeOnboarding()" class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">
        Continue to Prayer Community
    </button>
</div>
```

### Testing Requirements

#### 3.6 Frontend Tests (`tests/unit/test_religious_preference_frontend.py`)
```python
"""Tests for religious preference frontend functionality"""
import pytest
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup

from app import app
from tests.factories import UserFactory


@pytest.mark.unit
class TestReligiousPreferenceFrontend:
    """Test religious preference frontend components"""
    
    def test_preferences_page_displays_current_settings(self, test_client, test_user):
        """Test that preferences page shows current user settings"""
        test_user.religious_preference = "christian"
        test_user.prayer_style = "in_jesus_name"
        
        response = test_client.get("/profile/preferences")
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check that Christian option is selected
        christian_radio = soup.find('input', {'name': 'religious_preference', 'value': 'christian'})
        assert christian_radio.get('checked') is not None
        
        # Check that prayer style is shown
        prayer_style_radio = soup.find('input', {'name': 'prayer_style', 'value': 'in_jesus_name'})
        assert prayer_style_radio.get('checked') is not None
    
    def test_prayer_form_includes_targeting_options(self, test_client, test_user):
        """Test that prayer submission form includes target audience options"""
        response = test_client.get("/feed")  # Page that includes prayer form
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for target audience select
        target_select = soup.find('select', {'name': 'target_audience'})
        assert target_select is not None
        
        # Check for all options
        options = target_select.find_all('option')
        option_values = [opt.get('value') for opt in options]
        
        assert 'all' in option_values
        assert 'christians_only' in option_values
        assert 'non_christians_only' in option_values
    
    def test_prayer_cards_show_targeting_indicators(self, test_client, test_user):
        """Test that prayer cards show appropriate targeting indicators"""
        # This would test the prayer card display with targeting indicators
        pass


@pytest.mark.integration
class TestReligiousPreferenceUX:
    """Integration tests for religious preference user experience"""
    
    def test_complete_preference_update_workflow(self, test_client, test_user):
        """Test complete workflow of updating religious preferences"""
        # Navigate to preferences
        response = test_client.get("/profile/preferences")
        assert response.status_code == 200
        
        # Update preferences
        response = test_client.post("/profile/preferences", data={
            "religious_preference": "christian",
            "prayer_style": "in_jesus_name"
        })
        assert response.status_code == 303  # Redirect
        
        # Verify updated preferences are reflected
        response = test_client.get("/profile")
        assert response.status_code == 200
        assert "Christian" in response.content.decode()
    
    def test_prayer_submission_with_targeting_workflow(self, test_client, test_user):
        """Test complete workflow of submitting prayer with targeting"""
        response = test_client.post("/prayers", data={
            "text": "Please pray for my family",
            "target_audience": "christians_only",
            "prayer_context": "urgent"
        })
        assert response.status_code == 303  # Redirect
        
        # Verify prayer appears in feed with correct indicators
        response = test_client.get("/feed")
        content = response.content.decode()
        assert "Please pray for my family" in content
        assert "Christians" in content  # Targeting indicator
        assert "urgent" in content  # Context indicator
```

#### 3.7 User Acceptance Test Plan
```markdown
# User Acceptance Test Plan - Religious Preferences

## Test Scenarios

### Scenario 1: New User Onboarding
1. **As a new user**, I want to understand the religious preference options
2. **Given** I'm registering for the first time
3. **When** I see the religious preference options
4. **Then** I should see clear, respectful language explaining each option
5. **And** I should understand that preferences are optional
6. **And** I should be able to skip this step if desired

### Scenario 2: Christian User Experience  
1. **As a Christian user**, I want to specify that I pray in Jesus' name
2. **Given** I select "Christian" as my religious preference
3. **When** I choose "Pray in Jesus' name" as my prayer style
4. **Then** I should see prayers targeted to Christians
5. **And** I should see general prayers open to everyone
6. **But** I should not see prayers targeted only to non-Christians

### Scenario 3: Prayer Request Targeting
1. **As a prayer requestor**, I want to target my request to Christians only
2. **Given** I'm submitting a prayer request
3. **When** I select "Christians only" as the target audience
4. **Then** my prayer should only be visible to Christian users
5. **And** the targeting should be clearly indicated on the prayer card

### Scenario 4: Preference Changes
1. **As an existing user**, I want to change my religious preferences
2. **Given** I have existing religious preferences set
3. **When** I update my preferences
4. **Then** my prayer feed should immediately reflect the new filtering
5. **And** my existing prayers should not be affected

## Acceptance Criteria

### Usability
- [ ] All religious preference language is respectful and inclusive
- [ ] Help text clearly explains the purpose of each option
- [ ] Users can easily find and update their preferences
- [ ] Prayer targeting options are intuitive and well-explained

### Functionality  
- [ ] Prayer filtering works correctly for all user types
- [ ] Prayer targeting is accurately displayed
- [ ] Preference updates take effect immediately
- [ ] No existing functionality is broken

### Accessibility
- [ ] All forms are keyboard navigable
- [ ] Screen readers can access all preference options
- [ ] Color contrast meets accessibility standards
- [ ] Form validation provides clear error messages

### Performance
- [ ] Preference updates complete within 2 seconds
- [ ] Prayer feed loading time is not significantly impacted
- [ ] Database queries are optimized for filtering

## Test Data Requirements
- Users with each type of religious preference
- Prayers with each type of target audience
- Mixed scenarios with multiple users and prayers
```

### Success Criteria
- ✅ Religious preference settings are intuitive and respectful
- ✅ Prayer submission form clearly explains targeting options
- ✅ Prayer cards appropriately display targeting information
- ✅ User workflows are smooth and error-free
- ✅ All accessibility requirements are met
- ✅ User acceptance testing passes with positive feedback
- ✅ Performance impact is minimal
- ✅ Design language promotes inclusivity and respect

---

## Summary and Next Steps

### Implementation Timeline
- **Week 1**: Database schema and migration (Stage 1)
- **Week 2**: Backend logic and API development (Stage 2)  
- **Week 3**: Frontend interface and user testing (Stage 3)

### Success Metrics
1. **Technical**: All tests pass, no performance regression
2. **User Experience**: Positive feedback from diverse user base
3. **Adoption**: Users actively set religious preferences
4. **Engagement**: Prayer targeting is used appropriately

### Risk Mitigation
- **Sensitivity Review**: Have religious leaders review language and approach
- **Gradual Rollout**: Test with small user group before full deployment
- **Rollback Plan**: Ability to disable feature if issues arise
- **Monitoring**: Track usage patterns and user feedback closely

### Post-Implementation
- Monitor religious preference adoption rates
- Gather user feedback on prayer relevance and satisfaction
- Analyze prayer targeting usage patterns  
- Consider additional religious traditions if user base grows

This 3-stage implementation plan ensures careful development, thorough testing, and respectful user experience while maintaining the inclusive nature of the prayer community.