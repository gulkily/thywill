# Text Archives Import Idempotency Implementation Plan

## Problem Statement

The text archives import system is currently **partially idempotent**:
- ✅ Users and Prayers: Properly checked for duplicates
- ❌ Activity Logs: Always created, causing duplicates on re-import
- ❌ Prayer Attributes: Always created, causing duplicates on re-import  
- ❌ Prayer Marks: Always created, causing duplicates on re-import

## Goal

Make text archives import fully idempotent so multiple import runs produce identical database state without duplicates.

## Implementation Strategy

### Phase 1: Add Duplicate Detection for Activity Data

#### 1.1 Activity Logs Idempotency
**Location**: `text_importer_service.py:442-453`

**Current Issue**: Always creates `PrayerActivityLog` entries
```python
# Always creates - NOT idempotent
activity_log = PrayerActivityLog(...)
session.add(activity_log)
```

**Solution**: Check for existing activity log before creation
```python
# Check for existing activity log
existing_log = session.exec(
    select(PrayerActivityLog).where(
        PrayerActivityLog.prayer_id == prayer.id,
        PrayerActivityLog.user_id == user.display_name,
        PrayerActivityLog.action == action,
        PrayerActivityLog.created_at == activity_time
    )
).first()

if not existing_log:
    activity_log = PrayerActivityLog(...)
    session.add(activity_log)
    self.import_stats['activity_logs_imported'] += 1
```

#### 1.2 Prayer Attributes Idempotency  
**Location**: `text_importer_service.py:432-440`

**Current Issue**: Always creates `PrayerAttribute` entries

**Solution**: Check for existing attribute before creation
```python
# Check for existing attribute
existing_attr = session.exec(
    select(PrayerAttribute).where(
        PrayerAttribute.prayer_id == prayer.id,
        PrayerAttribute.attribute_name == 'answer_testimony'
    )
).first()

if not existing_attr:
    testimony_attr = PrayerAttribute(...)
    session.add(testimony_attr)
    self.import_stats['prayer_attributes_imported'] += 1
```

#### 1.3 Prayer Marks Idempotency
**Location**: Similar pattern in `_import_prayer_activities`

**Solution**: Check for existing marks before creation
```python
# Check for existing mark
existing_mark = session.exec(
    select(PrayerMark).where(
        PrayerMark.prayer_id == prayer.id,
        PrayerMark.username == user.display_name
    )
).first()

if not existing_mark:
    prayer_mark = PrayerMark(...)
    session.add(prayer_mark)
    self.import_stats['prayer_marks_imported'] += 1
```

### Phase 2: Enhanced Safety Measures

#### 2.1 Import Transaction Safety
- Wrap entire prayer import in single transaction
- Rollback on any error to maintain consistency
- Add detailed logging for duplicate detection

#### 2.2 Statistics Accuracy
- Only increment counters for actually imported items
- Add new counters: `*_skipped_existing` for transparency
- Report both imported and skipped counts

#### 2.3 Validation Enhancement
```python
def validate_import_idempotency(self, archive_path: Path) -> dict:
    """Validate that repeated imports produce identical results"""
    # Run import twice, compare final database state
    # Ensure no duplicates created on second run
```

### Phase 3: Testing Strategy

#### 3.1 Idempotency Tests
```python
def test_import_idempotency():
    """Test that running import twice produces same result"""
    # Import once
    stats1 = import_text_archives(archive_path)
    
    # Import again
    stats2 = import_text_archives(archive_path)
    
    # Verify no new records created
    assert stats2['prayers_imported'] == 0
    assert stats2['activity_logs_imported'] == 0
    assert stats2['prayer_attributes_imported'] == 0
```

#### 3.2 Edge Case Tests
- Concurrent imports (race conditions)
- Partial imports (interrupted processes)
- Corrupted archives (malformed data)
- Mixed existing/new data scenarios

### Phase 4: Implementation Steps

#### Step 1: Backup Current System
```bash
./thywill backup  # Create safety backup
```

#### Step 2: Implement Activity Log Idempotency
- Add duplicate checking to `_import_prayer_activities`
- Update statistics tracking
- Test with small archive subset

#### Step 3: Implement Prayer Attributes Idempotency  
- Add duplicate checking for attributes
- Handle multiple attribute types safely
- Test attribute-heavy archives

#### Step 4: Implement Prayer Marks Idempotency
- Add duplicate checking for marks
- Ensure mark type consistency
- Test mark-heavy archives

#### Step 5: Add Comprehensive Testing
- Create idempotency test suite
- Test with real archive data
- Validate statistics accuracy

#### Step 6: Enhanced Validation
- Add post-import consistency checks
- Implement idempotency validation tool
- Update CLI with new validation options

## Safety Considerations

### Backward Compatibility
- Existing archives remain fully compatible
- No changes to archive file formats
- Graceful handling of legacy data

### Performance Impact
- Minimal: Only add SELECT queries before INSERTs
- Use database indexes on commonly queried fields
- Consider batching for large imports

### Error Handling
- Preserve existing error recovery mechanisms
- Add specific handling for idempotency edge cases
- Maintain detailed logging for debugging

## Success Criteria

1. **Multiple Import Runs**: Identical database state after repeated imports
2. **No Duplicates**: Zero duplicate activity logs, attributes, or marks
3. **Accurate Statistics**: Import counters reflect actual new records
4. **Backward Compatible**: Existing workflows unchanged
5. **Performance**: No significant import speed degradation

## Testing Checklist

- [ ] Single archive imported twice = identical results
- [ ] Mixed existing/new data handled correctly
- [ ] Statistics accurately reflect actual imports
- [ ] Large archives import without performance issues
- [ ] Concurrent imports don't create duplicates
- [ ] Validation tools detect idempotency violations

## Implementation Timeline

**Week 1**: Activity logs idempotency + basic testing
**Week 2**: Prayer attributes + marks idempotency  
**Week 3**: Enhanced validation + comprehensive testing
**Week 4**: Performance optimization + documentation

This plan ensures text archives import becomes fully idempotent while maintaining safety, performance, and backward compatibility.