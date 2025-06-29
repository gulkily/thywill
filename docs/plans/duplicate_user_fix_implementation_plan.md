# Duplicate User Issue - Implementation Plan

## Problem Statement

Users are experiencing duplicate profile creation when:
1. Attempting to log in with username shows "username not found" 
2. Using invite link creates second profile with same username
3. Both profiles appear in members list

## Root Cause Analysis

### Critical Database Design Flaw
- **No unique constraint on `display_name` field** in User table
- Database allows multiple users with identical usernames
- No application-level duplicate prevention during user creation

### Authentication Flow Issues
1. **Race Conditions**: Simultaneous requests can bypass existence checks
2. **Inconsistent User Lookup**: Different login paths may have timing issues
3. **Archive-First Creation**: User creation process doesn't validate uniqueness before committing

### Specific Scenarios Causing Duplicates
- **Scenario A**: User exists but login lookup fails (timing/database issue)
- **Scenario B**: Multiple invite tokens claimed simultaneously with same username
- **Scenario C**: Existing user uses invite link, system creates new user instead of recognizing existing

## Implementation Solution

### Automated Migration Approach
Integration with ThyWill's existing migration system for seamless production deployment.

### Phase 1: Database Migration (Automatic on Startup)

#### 1.1 Migration Script Creation
Create `migrations/add_unique_display_name.py` that:
- Detects and merges duplicate usernames automatically
- Adds unique constraint to prevent future duplicates
- Runs automatically when application starts
- Logs all actions for audit trail

#### 1.2 Smart Duplicate Resolution
```python
def merge_duplicate_users(session):
    # Find duplicates
    duplicates = find_duplicate_usernames(session)
    for username, user_ids in duplicates.items():
        # Merge users preserving all data
        primary_user = select_primary_user(user_ids, session)
        for duplicate_id in user_ids:
            if duplicate_id != primary_user.id:
                merge_user_data(primary_user, duplicate_id, session)
```

#### 1.3 Application-Level Prevention
Add username uniqueness validation in user creation functions:
```python
def create_user_safely(display_name: str, session) -> User:
    # Atomic check-and-create with database constraint
    try:
        user = User(display_name=display_name)
        session.add(user)
        session.commit()
        return user
    except IntegrityError:
        session.rollback()
        # Return existing user or raise appropriate error
        return handle_duplicate_username(display_name, session)
```

### Phase 2: Enhanced User Management

#### 2.1 Robust User Lookup
Update all authentication flows to use consistent user lookup:
```python
def find_user_by_username(display_name: str, session) -> Optional[User]:
    return session.exec(
        select(User).where(User.display_name == display_name)
    ).first()
```

#### 2.2 Invite Token Safety
Modify invite claim process to:
- Check for existing user before creation
- Handle edge cases gracefully
- Log duplicate prevention events

### Phase 3: Monitoring and Maintenance

#### 3.1 Built-in Health Checks
Add duplicate detection to existing status checks:
```python
def check_database_integrity():
    # Called by ./thywill status
    duplicates = scan_for_duplicates()
    if duplicates:
        log_warning("Duplicate users detected", duplicates)
```

#### 3.2 CLI Integration
Extend existing CLI commands:
```bash
./thywill status          # Now includes duplicate check
./thywill migrate         # Runs duplicate fix migration
```

## Implementation Steps

### Step 1: Migration System Setup (1 hour)
1. Create migration script with duplicate detection and merge logic
2. Integrate with existing application startup sequence
3. Add migration tracking to prevent re-runs

### Step 2: User Creation Safety (1 hour)
1. Add unique constraint to User model
2. Update user creation functions with proper error handling
3. Implement safe user lookup functions

### Step 3: Authentication Flow Updates (1 hour)
1. Update invite claim process to check for existing users
2. Modify login flows to use consistent user lookup
3. Add logging for duplicate prevention events

### Step 4: Testing and Validation (1 hour)
1. Test migration with duplicate test data
2. Verify invite flows don't create duplicates
3. Test constraint enforcement
4. Validate automatic deployment process

## Database Migration Script

```sql
-- Step 1: Identify duplicates before applying constraint
SELECT display_name, COUNT(*) as duplicate_count 
FROM user 
GROUP BY display_name 
HAVING COUNT(*) > 1;

-- Step 2: Create temporary resolution table
CREATE TABLE user_merge_log (
    merge_id VARCHAR PRIMARY KEY,
    original_user_id VARCHAR,
    duplicate_user_id VARCHAR,
    merge_timestamp DATETIME,
    data_preserved TEXT
);

-- Step 3: After merging duplicates, add constraint
ALTER TABLE user ADD CONSTRAINT unique_display_name UNIQUE (display_name);
```

## Risk Mitigation

### Data Loss Prevention
- Complete database backup before any changes
- Reversible merge process with detailed logging
- Gradual rollout with monitoring

### Service Availability
- Apply changes during low-traffic periods
- Database changes can be applied with minimal downtime
- Rollback plan for each migration step

### User Experience
- Inform affected users about account consolidation
- Preserve all prayer data and history
- Maintain session continuity where possible

## Success Criteria

1. **No duplicate usernames** in database after migration
2. **All authentication flows** prevent duplicate creation
3. **Zero data loss** during duplicate merging
4. **Monitoring system** detects future duplicate attempts
5. **Performance impact** < 5% on authentication flows

## Long-term Maintenance

- Regular duplicate detection scans (weekly)
- Database integrity checks in backup routine
- User creation audit logging
- Performance monitoring of uniqueness constraints

## Deployment Strategy

### Automatic Migration on Production
1. **Code Deploy**: Push changes to production repository
2. **Auto-Migration**: Application startup runs migration automatically
3. **Zero Downtime**: Migration runs before server starts accepting requests
4. **Audit Trail**: All actions logged for review

### Rollback Safety
- Migration is idempotent (safe to run multiple times)
- Database constraint can be removed if needed
- User merge actions are logged for potential reversal
- No data loss during merge process

## Immediate Action Items

1. **Create Migration**: Implement automatic duplicate detection and merge
2. **Update Models**: Add unique constraint to User table
3. **Harden Auth**: Update user creation and lookup functions
4. **Deploy**: Push to production for automatic migration

This fix runs automatically on production deployment with zero manual intervention required.