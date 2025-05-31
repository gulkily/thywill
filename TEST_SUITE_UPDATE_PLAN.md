# Test Suite Update Plan for Prayer Archive & Answered System

## Overview
This plan outlines the comprehensive updates needed to the test suite to cover the new prayer archive and answered functionality implemented across Stages 1-3.

## Current Test Structure Analysis

### Existing Test Files
- `tests/unit/test_prayer_management.py` - Prayer submission and basic management
- `tests/unit/test_models.py` - Database model tests
- `tests/unit/test_database_operations.py` - Database operation tests
- `tests/unit/test_auth_helpers.py` - Authentication helper tests
- `tests/unit/test_advanced_features.py` - Advanced feature tests
- `tests/conftest.py` - Test configuration and fixtures
- `tests/factories.py` - Test data factories

### Missing Test Coverage
Based on the implementation, we need to add tests for:
- Prayer attributes system
- Archive/restore functionality
- Answered prayer workflow
- Activity logging
- Feed filtering with attributes
- Permission controls for prayer management

## Test Suite Updates

### 1. New Test Files Needed

#### `tests/unit/test_prayer_attributes.py`
**Purpose**: Test the core prayer attributes system
**Test Classes:**
- `TestPrayerAttributeModel` - Test PrayerAttribute model methods
- `TestPrayerAttributeOperations` - Test set/get/remove attribute operations
- `TestMultipleStatusSupport` - Test simultaneous statuses (archived + answered)
- `TestAttributePermissions` - Test who can modify attributes

#### `tests/unit/test_prayer_lifecycle.py`
**Purpose**: Test complete prayer lifecycle management
**Test Classes:**
- `TestArchiveWorkflow` - Test archive/restore functionality
- `TestAnsweredWorkflow` - Test answered prayer marking with testimony
- `TestStatusTransitions` - Test valid/invalid status transitions
- `TestActivityLogging` - Test activity log creation for status changes

#### `tests/unit/test_feed_filtering.py`
**Purpose**: Test enhanced feed system with attribute filtering
**Test Classes:**
- `TestFeedCounts` - Test feed count calculations with attributes
- `TestFeedQueries` - Test feed query filtering (archived, answered)
- `TestFeedPermissions` - Test personal vs public feed access
- `TestNewFeedTypes` - Test answered and archived feed types

#### `tests/integration/test_prayer_status_api.py`
**Purpose**: Test API endpoints for prayer status management
**Test Classes:**
- `TestArchiveEndpoints` - Test /prayer/{id}/archive and /prayer/{id}/restore
- `TestAnsweredEndpoints` - Test /prayer/{id}/answered with testimony
- `TestPermissionChecks` - Test authorization for status changes
- `TestHTMXResponses` - Test HTMX-specific response formats

### 2. Updates to Existing Test Files

#### `tests/unit/test_models.py`
**Add Test Classes:**
- `TestPrayerAttributeModel` - Test new PrayerAttribute model
- `TestPrayerActivityLogModel` - Test activity logging model
- `TestPrayerHelperMethods` - Test new Prayer model helper methods

**New Test Methods:**
```python
def test_prayer_has_attribute()
def test_prayer_get_attribute() 
def test_prayer_set_attribute()
def test_prayer_remove_attribute()
def test_prayer_convenience_properties()  # is_archived, is_answered, etc.
def test_prayer_activity_log_creation()
```

#### `tests/unit/test_prayer_management.py`
**Add Test Classes:**
- `TestPrayerStatusManagement` - Test prayer author permissions
- `TestTestimonyHandling` - Test answered prayer testimonies

**New Test Methods:**
```python
def test_only_author_can_archive()
def test_only_author_can_mark_answered()
def test_testimony_field_handling()
def test_answer_date_tracking()
def test_status_validation()
```

#### `tests/factories.py`
**Add New Factories:**
```python
class PrayerAttributeFactory(factory.Factory):
    class Meta:
        model = PrayerAttribute
    
    prayer_id = factory.LazyAttribute(lambda obj: PrayerFactory().id)
    attribute_name = "test_attribute"
    attribute_value = "true"
    created_by = factory.LazyAttribute(lambda obj: UserFactory().id)

class PrayerActivityLogFactory(factory.Factory):
    class Meta:
        model = PrayerActivityLog
    
    prayer_id = factory.LazyAttribute(lambda obj: PrayerFactory().id)
    user_id = factory.LazyAttribute(lambda obj: UserFactory().id)
    action = "set_archived"
    new_value = "true"
```

### 3. Functional Tests

#### `tests/functional/test_prayer_workflow.py`
**Purpose**: End-to-end testing of prayer lifecycle
**Test Scenarios:**
- Complete archive workflow (author perspective)
- Complete answered workflow with testimony
- Community interaction with archived/answered prayers
- Feed navigation and filtering
- Permission boundaries

### 4. Performance Tests

#### `tests/performance/test_attribute_queries.py`
**Purpose**: Test query performance with attributes system
**Test Scenarios:**
- Feed query performance with attribute filtering
- Index effectiveness for prayer attributes
- Large dataset performance (1000+ prayers with attributes)

## Detailed Test Implementation

### Test Case Examples

#### Archive Functionality Tests
```python
def test_prayer_archive_workflow(test_session):
    """Test complete archive workflow"""
    user = UserFactory.create()
    prayer = PrayerFactory.create(author_id=user.id)
    test_session.add_all([user, prayer])
    test_session.commit()
    
    # Test archiving
    prayer.set_attribute('archived', 'true', user.id, test_session)
    test_session.commit()
    
    assert prayer.is_archived(test_session) == True
    
    # Test restoration
    prayer.remove_attribute('archived', test_session, user.id)
    test_session.commit()
    
    assert prayer.is_archived(test_session) == False

def test_archive_permission_control(test_session):
    """Test only authors can archive their prayers"""
    author = UserFactory.create()
    other_user = UserFactory.create()
    prayer = PrayerFactory.create(author_id=author.id)
    test_session.add_all([author, other_user, prayer])
    test_session.commit()
    
    # Author should be able to archive
    assert can_manage_prayer_status(author, prayer) == True
    
    # Other users should not
    assert can_manage_prayer_status(other_user, prayer) == False
```

#### Answered Prayer Tests
```python
def test_answered_prayer_with_testimony(test_session):
    """Test marking prayer as answered with testimony"""
    user = UserFactory.create()
    prayer = PrayerFactory.create(author_id=user.id)
    test_session.add_all([user, prayer])
    test_session.commit()
    
    # Mark as answered with testimony
    prayer.set_attribute('answered', 'true', user.id, test_session)
    prayer.set_attribute('answer_testimony', 'God provided a new job!', user.id, test_session)
    test_session.commit()
    
    assert prayer.is_answered(test_session) == True
    assert prayer.answer_testimony(test_session) == 'God provided a new job!'
```

#### Feed Filtering Tests
```python
def test_feed_excludes_archived_prayers(test_session):
    """Test that archived prayers don't appear in public feeds"""
    user = UserFactory.create()
    active_prayer = PrayerFactory.create(author_id=user.id)
    archived_prayer = PrayerFactory.create(author_id=user.id)
    
    test_session.add_all([user, active_prayer, archived_prayer])
    test_session.commit()
    
    # Archive one prayer
    archived_prayer.set_attribute('archived', 'true', user.id, test_session)
    test_session.commit()
    
    # Test feed query (should exclude archived)
    active_prayers = test_session.exec(
        select(Prayer)
        .where(Prayer.flagged == False)
        .where(
            ~Prayer.id.in_(
                select(PrayerAttribute.prayer_id)
                .where(PrayerAttribute.attribute_name == 'archived')
            )
        )
    ).all()
    
    assert len(active_prayers) == 1
    assert active_prayers[0].id == active_prayer.id
```

### Test Data Setup

#### Enhanced Fixtures
```python
@pytest.fixture
def prayer_with_attributes(test_session):
    """Create a prayer with various attributes for testing"""
    user = UserFactory.create()
    prayer = PrayerFactory.create(author_id=user.id)
    
    # Add multiple attributes
    archived_attr = PrayerAttributeFactory.create(
        prayer_id=prayer.id,
        attribute_name='archived',
        created_by=user.id
    )
    answered_attr = PrayerAttributeFactory.create(
        prayer_id=prayer.id, 
        attribute_name='answered',
        created_by=user.id
    )
    
    test_session.add_all([user, prayer, archived_attr, answered_attr])
    test_session.commit()
    return prayer, user
```

## Test Coverage Goals

### Target Coverage Areas
1. **Prayer Attributes System**: 100% coverage of model methods
2. **Archive Workflow**: Complete user journey testing
3. **Answered Prayers**: Full workflow with testimony handling
4. **Feed Filtering**: All feed types with attribute filtering
5. **Permissions**: Authorization for prayer management
6. **Activity Logging**: Complete audit trail testing
7. **Performance**: Query optimization validation
8. **API Endpoints**: All new status management routes

### Test Metrics
- **Unit Tests**: 90%+ code coverage for new functionality
- **Integration Tests**: All API endpoints covered
- **Functional Tests**: Complete user workflows
- **Performance Tests**: Query response times under 50ms

## Implementation Priority

### Phase 1: Core Functionality (Week 1)
1. Create `test_prayer_attributes.py` with core attribute system tests
2. Update `test_models.py` with new model tests
3. Add basic archive/answered workflow tests

### Phase 2: API & Integration (Week 2)
1. Create `test_prayer_status_api.py` with endpoint testing
2. Create `test_feed_filtering.py` with enhanced feed tests
3. Update existing tests for new functionality

### Phase 3: Advanced & Performance (Week 3)
1. Add functional tests for complete workflows
2. Create performance tests for query optimization
3. Add edge case and error condition testing

## Test Execution Strategy

### Continuous Integration
- Run unit tests on every commit
- Run integration tests on PR creation
- Run full test suite before deployment

### Test Organization
- Group tests by functionality (attributes, workflow, feeds)
- Use pytest markers for test categorization
- Separate fast unit tests from slower integration tests

### Test Data Management
- Use factories for consistent test data
- Clean up test data between test runs
- Isolate tests to prevent interference

This comprehensive test suite update will ensure the prayer archive and answered system is thoroughly tested and maintainable for future development.