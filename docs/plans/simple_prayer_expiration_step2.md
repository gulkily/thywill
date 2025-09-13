# Simple Prayer Expiration System - Step 2: Development Plan

## Implementation Phases

### Phase 1: Core Expiration Logic (1.5 hours)
**Goal**: Implement basic expiration date storage and checking

#### Tasks:
1. **Create expiration helper functions** (30 min)
   - `set_prayer_expiration(prayer_id, expiration_date, user_id, session)`
   - `get_prayer_expiration(prayer_id, session) -> datetime | None`
   - `is_prayer_expired(prayer_id, session) -> bool`
   - `remove_prayer_expiration(prayer_id, user_id, session)`

2. **Add expiration filtering to feed queries** (45 min)
   - Modify `feed_operations.py` to exclude expired prayers by default
   - Add `include_expired=False` parameter to feed functions
   - Update prayer dictionary to include expiration data

3. **Create expiration management CLI command** (15 min)
   - `./thywill expire-prayers` to manually run expiration check
   - Useful for testing and manual management

#### Acceptance Criteria:
- Can set expiration dates on prayers via prayer attributes
- Feed queries exclude expired prayers
- Can check expiration status programmatically

---

### Phase 2: Default Expiration Configuration (1 hour)
**Goal**: Automatic expiration date setting based on environment variable

#### Tasks:
1. **Add environment variable support** (15 min)
   - `PRAYER_EXPIRATION_ENABLED=true/false` (master toggle)
   - `DEFAULT_PRAYER_EXPIRATION_DAYS=30` (default days, 0 = disabled)
   - Update CLAUDE.md with new variables

2. **Integrate into prayer submission** (30 min)
   - Modify `submit_prayer_archive_first()` to set default expiration
   - Only set if no manual expiration provided and default > 0
   - Calculate expiration as `creation_date + DEFAULT_PRAYER_EXPIRATION_DAYS`

3. **Test default expiration** (15 min)
   - Verify prayers get expiration dates when feature enabled
   - Verify no expiration when feature disabled
   - Test with different day values

#### Acceptance Criteria:
- New prayers automatically get expiration dates when configured
- Feature can be disabled via environment variables
- Manual expiration dates override defaults

---

### Phase 3: Manual Expiration Date Setting (1.5 hours)
**Goal**: Allow users to set custom expiration dates during prayer submission

#### Tasks:
1. **Add expiration field to prayer form** (45 min)
   - Add optional date picker to `components/prayer_form.html`
   - JavaScript for date validation (future dates only)
   - Progressive enhancement (works without JavaScript)

2. **Update prayer submission endpoint** (30 min)
   - Modify `/prayers` POST route to accept `expiration_date` parameter
   - Validate expiration date (must be future date)
   - Set expiration attribute when provided

3. **Add form styling and UX** (15 min)
   - Clear labeling: "Prayer Expires On (Optional)"
   - Helper text: "Leave blank for no expiration"
   - Consistent styling with existing form elements

#### Acceptance Criteria:
- Users can optionally set expiration dates when submitting prayers
- Form validates future dates only
- Manual dates override default expiration settings

---

### Phase 4: Expiration UI Indicators (1 hour)  
**Goal**: Show expiration status clearly in the interface

#### Tasks:
1. **Add expiration data to prayer cards** (15 min)
   - Update `feed_operations.py` prayer dictionary with expiration info
   - Include: `expiration_date`, `is_expired`, `days_until_expiration`

2. **Update prayer card template** (30 min)
   - Show "Expires: [date]" for prayers with expiration dates
   - Show "⏰ Expiring Soon" warning for prayers expiring within 7 days
   - Show "📅 Expired" status for expired prayers
   - Style expired prayers with muted appearance

3. **Add expiration indicators to other views** (15 min)
   - Prayer marks page, answered celebration, activity feed
   - Consistent expiration display across all templates

#### Acceptance Criteria:
- Expiration dates are clearly visible on prayer cards
- Expiring soon warnings are prominently displayed  
- Expired prayers are visually distinguished
- Consistent expiration indicators across all views

---

### Phase 5: Expiration Management Actions (1.5 hours)
**Goal**: Allow prayer authors to manage expiration dates

#### Tasks:
1. **Add expiration management routes** (45 min)
   - `POST /prayer/{id}/extend-expiration` (extend by 7/30 days or custom date)
   - `POST /prayer/{id}/remove-expiration` (make prayer permanent)
   - `POST /prayer/{id}/expire-now` (manually expire immediately)
   - Author-only permission checking

2. **Add expiration actions to prayer card dropdown** (30 min)
   - "Extend Expiration" with options (7 days, 30 days, custom date)
   - "Remove Expiration" action
   - "Expire Now" action
   - Show only for prayer authors, only when relevant

3. **HTMX integration** (15 min)
   - Update prayer cards in-place after expiration changes
   - Show loading states during expiration updates
   - Handle errors gracefully

#### Acceptance Criteria:
- Prayer authors can extend, remove, or manually trigger expiration
- Actions are clearly available in prayer card dropdown
- UI updates immediately after expiration changes
- Only prayer authors can manage their own prayer expiration

---

### Phase 6: Expired Prayer Handling (45 min)
**Goal**: Proper handling of expired prayers in feeds and searches

#### Tasks:
1. **Create expired prayers feed** (20 min)
   - New feed type: `expired` showing only expired prayers
   - Author can view their own expired prayers
   - Admin can view all expired prayers

2. **Update feed navigation** (15 min)
   - Add "Expired Requests" to personal feeds section
   - Show count of expired prayers in navigation
   - Clear visual distinction from active feeds

3. **Automatic expiration processing** (10 min)
   - Background job or startup task to mark expired prayers
   - Update prayer status based on expiration dates
   - Log expiration activity for audit trail

#### Acceptance Criteria:
- Expired prayers have dedicated viewing area
- Feed counts include expired prayer statistics
- System automatically processes expiration dates

---

## Testing Strategy

### Unit Tests
- Expiration helper functions
- Date validation and calculation
- Permission checking for expiration management

### Integration Tests  
- Prayer submission with expiration dates
- Feed filtering with expired prayers
- Expiration management workflows

### Manual Testing
- Prayer lifecycle: submit → active → expiring → expired
- Form validation and UX flows
- Cross-browser date picker functionality

## Risk Mitigation

### Technical Risks
- **Date timezone handling**: Use consistent UTC storage, display in user timezone
- **Performance impact**: Index expiration queries, limit feed query complexity
- **Data consistency**: Ensure expiration attributes are properly managed

### UX Risks
- **User confusion**: Clear labeling and help text for expiration features
- **Accidental expiration**: Confirmation dialogs for destructive actions
- **Mobile experience**: Ensure date pickers work well on mobile devices

## Dependencies
- Existing prayer attribute system
- HTMX for dynamic updates
- Current prayer card and form templates

## Deployment Considerations
- Feature flags allow gradual rollout
- Backward compatible (existing prayers remain unchanged)
- No database migrations required (uses existing attribute system)

---
**Next Step**: Review this development plan, then proceed to Step 3 (Implementation) in FEATURE_DEVELOPMENT_PROCESS.md