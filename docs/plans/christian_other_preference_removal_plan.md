# Christian/Other Preference System Removal Plan

## Overview
Remove the religious preference system (Christian/Other) from ThyWill to simplify the codebase and reduce maintenance overhead. This system appears underutilized and adds significant complexity.

## Impact Assessment
- **Database Fields**: 3 fields across 2 models
- **Code Files**: 15+ files affected
- **Routes**: 4 preference-related endpoints  
- **Templates**: 3 frontend interfaces
- **Tests**: 2 dedicated test files + factory support
- **Migration**: 1 migration script (needs reversal)

## Removal Strategy

### Phase 1: Database Schema Changes
**Priority: HIGH - Data Loss Risk**

1. **Create Rollback Migration**
   - File: `rollback_religious_preferences.py`
   - Remove columns: `religious_preference`, `prayer_style` from User
   - Remove column: `target_audience` from Prayer
   - Backup database before migration

2. **Update Core Models** (`models.py`)
   - Remove `religious_preference` field from User model
   - Remove `prayer_style` field from User model  
   - Remove `target_audience` field from Prayer model
   - Update any model validators/constraints

### Phase 2: Backend Service Cleanup
**Priority: HIGH - Core Functionality**

3. **Prayer Services** (`app_helpers/services/prayer_helpers.py`)
   - Remove `get_filtered_prayers_for_user()` function
   - Remove `find_compatible_prayer_partner()` function
   - Simplify `get_feed_counts()` - remove filtering logic
   - Remove `apply_religious_filter()` function
   - Remove `get_religious_preference_stats()` function

4. **Feed Operations** (`app_helpers/routes/prayer/feed_operations.py`)
   - Remove `apply_religious_filter()` calls from all feeds
   - Simplify feed queries to show all prayers to all users
   - Update feed count calculations

5. **Prayer CRUD** (`app_helpers/routes/prayer/prayer_operations.py`)
   - Remove `target_audience` parameter from prayer creation
   - Simplify prayer partner assignment (random or sequential)
   - Remove preference-based preview filtering

### Phase 3: Route Cleanup
**Priority: MEDIUM - User-Facing**

6. **User Routes** (`app_helpers/routes/user_routes.py`)
   - Remove `/preferences` endpoints (GET/POST)
   - Remove `/profile/preferences` endpoints (GET/POST)
   - Remove preference validation logic
   - Update user profile to remove preference references

### Phase 4: Frontend Cleanup
**Priority: MEDIUM - User Interface**

7. **Template Updates**
   - **Remove**: `templates/preferences.html` (entire file)
   - **Update**: `templates/profile.html` - remove preference display/links
   - **Update**: `templates/components/prayer_form.html` - remove target audience selector
   - **Update**: `templates/components/prayer_card.html` - remove targeting indicators
   - **Update**: Navigation/menu items referencing preferences

### Phase 5: Test Cleanup
**Priority: LOW - Quality Assurance**

8. **Test Removal**
   - Remove: `tests/unit/test_religious_preference_filtering.py`
   - Remove: `tests/unit/test_religious_preference_schema.py`
   - Update: `tests/factories.py` - remove preference fields
   - Update any integration tests using preferences

### Phase 6: Documentation Cleanup
**Priority: LOW - Maintenance**

9. **Documentation Updates**
   - Update `CLAUDE.md` - remove preference references
   - Update `README.md` if applicable
   - Archive planning documents in `docs/plans/archived/`

## Implementation Order

### Step 1: Preparation
- [ ] Full database backup
- [ ] Create rollback migration script
- [ ] Document current preference usage statistics
- [ ] Test rollback migration on copy of production data

### Step 2: Backend Core (High Risk)
- [ ] Update models.py (remove fields)
- [ ] Run rollback migration
- [ ] Update prayer_helpers.py (remove filtering)
- [ ] Update feed_operations.py (simplify feeds)
- [ ] Update prayer_operations.py (simplify creation)

### Step 3: Routes & API (Medium Risk)
- [ ] Remove preference routes from user_routes.py
- [ ] Test API functionality

### Step 4: Frontend (Low Risk)
- [ ] Remove/update templates
- [ ] Test user interface flows
- [ ] Remove JavaScript preference logic

### Step 5: Testing & Cleanup (Low Risk)
- [ ] Remove test files
- [ ] Update remaining tests
- [ ] Update documentation

## Risk Mitigation

### Data Safety
- **Full backup** before any database changes
- **Staged rollout** - test on copy first
- **Rollback plan** ready if issues arise

### User Experience
- **Gradual removal** - backend first, frontend last
- **No breaking changes** - maintain existing prayer functionality
- **User communication** if preference settings were visible

### Code Quality
- **Test all feeds** after filtering removal
- **Verify prayer creation** works without target audience
- **Check user registration/profile** flows

## Post-Removal Benefits

### Code Simplification
- Remove 200+ lines of filtering logic
- Eliminate 4 database queries per feed load
- Simplify prayer partner assignment
- Remove complex conditional UI logic

### Performance Improvements
- Faster feed loading (no filtering overhead)
- Simpler database queries
- Reduced template complexity

### Maintenance Reduction
- Fewer edge cases to test
- No preference migration concerns
- Simplified user onboarding

## Testing Strategy

### Critical Tests
1. **Prayer feeds load correctly** for all users
2. **Prayer creation works** without target audience
3. **User registration/login** flows unaffected
4. **Archive/import functions** work without preference data

### Regression Tests
1. All existing prayer functionality preserved
2. User profiles display correctly
3. No broken links or references
4. Database integrity maintained

## Rollback Plan

If issues arise:
1. **Restore database** from pre-migration backup
2. **Revert code changes** using git
3. **Re-run original migration** to restore fields
4. **Verify system functionality**

## Timeline Estimate
- **Preparation**: 2-4 hours
- **Backend changes**: 4-6 hours  
- **Frontend changes**: 2-3 hours
- **Testing**: 3-4 hours
- **Total**: 11-17 hours

## Success Criteria
- [ ] All database preference fields removed
- [ ] No preference-related code remains
- [ ] All tests pass
- [ ] Prayer functionality unchanged for users
- [ ] Performance improved (measurable)
- [ ] No broken links or errors