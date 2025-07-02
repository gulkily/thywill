# Archive Operations Idempotency Plan

## Current Status

### ✅ text-archives import - FULLY IDEMPOTENT
- Users, prayers, prayer marks, prayer attributes, activity logs
- Comprehensive duplicate checking implemented
- **Verified working** via test suite and manual testing

### 🔄 heal-archives - PARTIALLY IDEMPOTENT 
- **✅ Basic idempotency**: Checks `text_file_path` and file existence
- **❌ Data gap**: Only creates base archive files, missing activity data reconstruction

## Problem Statement

Current `heal-archives` only recreates **base archive files** but doesn't rebuild the **full activity data** that `text-archives import` can restore:

**heal-archives creates:**
- Prayer archive files (`.txt` files)
- User registration entries

**Missing activity data that import can restore:**
- Prayer marks (prayer interactions)
- Prayer attributes (status changes, testimonies)
- Activity logs (audit trail)

## Goal

Make both operations **fully idempotent** and **comprehensive**:
1. `heal-archives` should reconstruct **complete** archive files including all activity data
2. Both operations should be safely repeatable without duplicates

## Implementation Plan

### Phase 1: Enhance heal-archives Data Coverage

#### 1.1 Add Prayer Activity Reconstruction
**Location**: `heal_prayer_archives.py:80-95`

**Current**: Only creates basic prayer archive
```python
# Only basic prayer data
archive_data = {
    'id': prayer.id,
    'author': author_name,
    'text': prayer.text,
    'created_at': prayer.created_at
}
```

**Enhanced**: Include all prayer activities
```python
# Get all prayer marks for this prayer
prayer_marks = session.exec(
    select(PrayerMark).where(PrayerMark.prayer_id == prayer.id)
).all()

# Get all prayer attributes 
prayer_attributes = session.exec(
    select(PrayerAttribute).where(PrayerAttribute.prayer_id == prayer.id)
).all()

# Get all activity logs
activity_logs = session.exec(
    select(PrayerActivityLog).where(PrayerActivityLog.prayer_id == prayer.id)
).all()

# Create comprehensive archive with all activity data
archive_data = {
    'id': prayer.id,
    'author': author_name,
    'text': prayer.text,
    'created_at': prayer.created_at,
    'marks': [mark_to_dict(mark) for mark in prayer_marks],
    'attributes': [attr_to_dict(attr) for attr in prayer_attributes],
    'activities': [log_to_dict(log) for log in activity_logs]
}
```

#### 1.2 Add User Activity Reconstruction
**Location**: `heal_prayer_archives.py:145-155`

**Enhanced**: Include user's prayer interaction history
```python
# Get user's prayer marks and activities
user_marks = session.exec(
    select(PrayerMark).where(PrayerMark.username == user.display_name)
).all()

user_activities = session.exec(
    select(PrayerActivityLog).where(PrayerActivityLog.user_id == user.display_name)
).all()

# Create user archive with activity history
archive_entry = {
    'display_name': user.display_name,
    'invited_by': invite_source,
    'registration_date': user.created_at,
    'activity_summary': {
        'total_marks': len(user_marks),
        'total_activities': len(user_activities)
    }
}
```

### Phase 2: Enhanced Idempotency

#### 2.1 Archive Content Verification
Add content-based duplicate detection:
```python
def verify_archive_completeness(prayer, archive_path):
    """Verify archive contains all current database activity"""
    if not os.path.exists(archive_path):
        return False
    
    # Parse existing archive
    existing_data = parse_archive_file(archive_path)
    
    # Get current database state
    current_marks_count = get_prayer_marks_count(prayer.id)
    current_attributes_count = get_prayer_attributes_count(prayer.id)
    
    # Compare counts
    return (
        existing_data.get('marks_count', 0) == current_marks_count and
        existing_data.get('attributes_count', 0) == current_attributes_count
    )
```

#### 2.2 Smart Healing Logic
```python
if needs_healing:
    # Check if archive exists but is incomplete
    if prayer.text_file_path and os.path.exists(prayer.text_file_path):
        if verify_archive_completeness(prayer, prayer.text_file_path):
            print(f"✅ Prayer {prayer.id} archive is complete")
            continue
        else:
            print(f"🔄 Prayer {prayer.id} archive needs update")
            reason = "Archive missing recent activity data"
    
    # Heal with complete data reconstruction
    heal_prayer_with_full_data(prayer, session)
```

### Phase 3: Unified Testing

#### 3.1 Comprehensive Test Suite
```python
def test_heal_archives_idempotency():
    """Test heal-archives is fully idempotent"""
    # Create prayer with full activity data
    prayer = create_test_prayer_with_activities()
    
    # Run heal twice
    heal_results_1 = run_heal_archives()
    heal_results_2 = run_heal_archives()
    
    # Verify idempotency
    assert heal_results_2['prayers_healed'] == 0
    assert heal_results_2['users_healed'] == 0
    
    # Verify complete data coverage
    assert archive_contains_all_activities(prayer)
```

#### 3.2 Round-trip Verification
```python
def test_heal_import_roundtrip():
    """Test heal-archives creates data that import can fully restore"""
    # Original database state
    original_state = capture_database_state()
    
    # Clear archives, heal, then import
    clear_archive_files()
    run_heal_archives()
    clear_database()
    run_import_archives()
    
    # Verify identical restoration
    restored_state = capture_database_state()
    assert states_identical(original_state, restored_state)
```

### Phase 4: Implementation Steps

#### Step 1: Enhance Archive Data Collection ⏳ PENDING
- Add prayer marks collection to heal-archives
- Add prayer attributes collection to heal-archives  
- Add activity logs collection to heal-archives
- Update archive format to include activity data

#### Step 2: Improve Idempotency Detection ⏳ PENDING
- Add content-based archive verification
- Implement smart healing (update vs skip)
- Add activity count validation

#### Step 3: Comprehensive Testing ⏳ PENDING
- Add heal-archives idempotency tests
- Add heal-import round-trip tests
- Verify complete data coverage

#### Step 4: Documentation Update ⏳ PENDING
- Update CLAUDE.md with enhanced heal-archives capabilities
- Document idempotency guarantees for both operations
- Add troubleshooting guide for archive inconsistencies

## Success Criteria

1. **Complete Data Coverage**: heal-archives recreates ALL data that import can restore
2. **Full Idempotency**: Both operations are safely repeatable with zero duplicates
3. **Round-trip Integrity**: heal → import → heal produces identical results
4. **Performance**: No significant performance degradation
5. **Backward Compatible**: Existing archives remain fully compatible

## Expected Outcome

**After implementation:**
- `heal-archives` becomes a complete disaster recovery tool
- Both operations guarantee full idempotency 
- Archive operations cover 100% of importable data
- Safe to run either operation multiple times
- Complete confidence in archive-based backup/restore workflows

## Testing Checklist

- [ ] heal-archives creates comprehensive activity data
- [ ] heal-archives is fully idempotent (repeated runs = no changes)
- [ ] import-archives remains fully idempotent 
- [ ] heal → import → heal produces identical database state
- [ ] Performance benchmarks meet requirements
- [ ] All edge cases handled (missing files, corrupted data, etc.)
- [ ] Backward compatibility with existing archives maintained

---

**Status**: Planning phase - ready for implementation when approved