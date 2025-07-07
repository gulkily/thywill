# Answered Prayers to Praise Reports Implementation Plan

## Overview
Change the language from "answered prayers" to "praise reports" throughout the application, starting with low-impact UI changes that don't break functionality.

## Phase 1: Frontend Text Changes (Low Risk)
These changes only affect user-facing text and don't impact database schema or core functionality.

### Step 1: Template Text Updates
- [ ] Update `templates/` files to replace "answered prayer" with "praise report"
- [ ] Update button text from "Mark as Answered" to "Mark as Praise Report"
- [ ] Update feed section headers and labels
- [ ] Update modal titles and confirmation messages

### Step 2: JavaScript/HTMX Labels
- [ ] Update any client-side text in JavaScript files
- [ ] Update HTMX response messages and notifications
- [ ] Update any hardcoded strings in frontend code

### Step 3: Help Text and Instructions
- [ ] Update user-facing help text and tooltips
- [ ] Update any instructional content about the feature

## Phase 2: Backend Response Messages (Low Risk)
These changes affect API responses but don't change database structure.

### Step 4: Flash Messages and Notifications
- [ ] Update success/error messages in route handlers
- [ ] Update email notification text (if applicable)
- [ ] Update any logging messages visible to users

### Step 5: API Response Labels
- [ ] Update JSON response field labels for frontend consumption
- [ ] Update any API documentation or comments

## Phase 3: Database Schema Updates (Medium Risk)
These changes affect the database but maintain backward compatibility.

### Step 6: Add New Database Fields
- [ ] Add new status field for "praise_report" alongside existing "answered"
- [ ] Create migration script to add new enum values
- [ ] Ensure both old and new values are supported during transition

### Step 7: Backend Logic Updates
- [ ] Update `prayer.set_attribute()` to handle both old and new status values
- [ ] Update feed filtering logic to include both statuses
- [ ] Update any business logic that checks prayer status

## Phase 4: Data Migration (Medium Risk)
Migrate existing data to use new terminology while maintaining functionality.

### Step 8: Data Conversion
- [ ] Create script to convert existing "answered" prayers to "praise_report"
- [ ] Run conversion on development/staging first
- [ ] Verify all existing functionality still works

### Step 9: Remove Legacy Support
- [ ] Remove support for old "answered" status values
- [ ] Update database constraints to only allow new values
- [ ] Clean up any remaining references to old terminology

## Phase 5: Testing and Validation (All Phases)
Continuous testing throughout implementation.

### Step 10: Template Validation
- [ ] Run `./validate_templates.py` after each template change
- [ ] Test all prayer-related workflows
- [ ] Verify HTMX interactions still work

### Step 11: Full System Testing
- [ ] Run complete test suite with `pytest`
- [ ] Test prayer creation, marking, and feed functionality
- [ ] Verify archive functionality with new terminology

## Implementation Notes

### Safety Considerations
- Each phase can be deployed independently
- Phase 1-2 changes are immediately reversible
- Database changes in Phase 3-4 should be thoroughly tested
- Always run `./thywill test` before deploying changes

### Key Files to Update
- Templates: All files in `templates/` directory
- Models: `models.py` (prayer status enums)
- Routes: Prayer-related routes in `app_helpers/`
- Services: Any services that handle prayer status

### Rollback Strategy
- Phase 1-2: Simple text revert in templates
- Phase 3-4: Database migration rollback scripts
- Keep old status values supported during transition period

### Testing Strategy
- Use `./thywill test` for isolated testing
- Test each phase thoroughly before proceeding
- Verify both new and existing prayers work correctly
- Check that archives still generate properly

## Success Criteria
- All user-facing text uses "praise report" terminology
- Existing prayers continue to function normally
- Archive functionality preserves new terminology
- No broken links or missing functionality
- All tests pass with new terminology