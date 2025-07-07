# AI_PROJECT_GUIDE.md Update Plan

## Overview
This plan outlines the comprehensive updates needed to the `AI_PROJECT_GUIDE.md` file to document the new prayer archive and answered functionality implemented across Stages 1-3.

## Current Documentation Analysis

### What's Currently Documented
- Basic prayer system (submission, marking, feeds)
- Community moderation with flagging
- Multi-device authentication system
- Core database schema
- API endpoints and routes
- HTMX integration patterns

### Missing Documentation
The guide needs updates for:
- Prayer attributes system architecture
- Archive and answered prayer workflows
- New database models (PrayerAttribute, PrayerActivityLog)
- Enhanced feed system with status filtering
- New API endpoints for prayer management
- Prayer lifecycle management features

## Detailed Update Plan

### 1. Database Schema Updates

#### Add to "Database Schema" section:

**New Core Models:**
```markdown
### Enhanced Prayer Management Models (New)
10. **PrayerAttribute**: Flexible prayer status system (id, prayer_id, attribute_name, attribute_value, created_at, created_by)
11. **PrayerActivityLog**: Audit trail for prayer status changes (id, prayer_id, user_id, action, old_value, new_value, created_at)

### Prayer Attributes System
The prayer system now uses a flexible attributes approach instead of simple boolean flags:
- **Multiple simultaneous statuses**: Prayers can be archived AND answered AND flagged
- **Extensible design**: New attributes can be added without schema changes
- **Audit trail**: All status changes are logged for accountability
- **Efficient querying**: Proper indexing for performance with attribute filtering

### Prayer Status Attributes
- **archived**: Prayer hidden from public feeds but preserved with history
- **answered**: Prayer marked as resolved, with optional answer_date and answer_testimony
- **flagged**: Prayer requires moderation (migrated from boolean)
- **answer_date**: ISO timestamp when prayer was answered
- **answer_testimony**: User's testimony of how prayer was answered
```

### 2. Key Features Updates

#### Add new section: "Prayer Lifecycle Management"
```markdown
### Prayer Lifecycle Management (New)
- **Prayer Author Controls**: Authors can manage their own prayer requests
- **Archive System**: Hide prayers from public feeds while preserving history
- **Answered Prayers**: Mark prayers as resolved with optional testimony sharing
- **Status Combinations**: Prayers can have multiple statuses simultaneously
- **Activity Logging**: Complete audit trail of all status changes
- **Community Celebration**: Dedicated feeds for celebrating answered prayers

### Prayer Status Management
- **Archive/Restore**: Prayer authors can archive prayers (hide from public) and restore them
- **Mark as Answered**: Authors can mark prayers as answered with optional testimony
- **Testimony Sharing**: Community can see how God moved in answered prayers
- **Status Preservation**: Prayer marks and community engagement preserved across status changes

### Enhanced Community Features
- **Answered Prayers Feed**: Public celebration of resolved prayer requests
- **Personal Archive**: Private view of author's archived prayers
- **Prayer Statistics**: Answer rates, community engagement metrics
- **Testimony Collection**: Stories of how prayers were answered for community encouragement
```

### 3. Feed Types Updates

#### Update "Feed Types" section:
```markdown
### Feed Types (Updated)
1. **All**: All unflagged, non-archived prayers
2. **New & Unprayed**: Active prayers with zero prayer marks
3. **Most Prayed**: Active prayers sorted by prayer count
4. **My Prayers**: Prayers the user has marked as prayed (all statuses)
5. **My Requests**: Prayers submitted by the user (all statuses with management controls)
6. **Recent Activity**: Active prayers with marks in last 7 days
7. **Answered Prayers** (New): Public celebration feed of resolved prayers
8. **Archived** (New): Personal feed of author's archived prayers (private)

### Feed Filtering Logic
- **Public feeds** (All, New, Popular, Recent): Exclude archived prayers
- **Personal feeds** (My Prayers, My Requests): Include all statuses with indicators
- **Celebration feeds** (Answered): Show resolved prayers with testimonies
- **Archive feeds**: Private to prayer authors only
```

### 4. API Endpoints Updates

#### Add to "API Endpoints" section:
```markdown
### Prayer Management Routes (New)
- `POST /prayer/{prayer_id}/archive` - Archive prayer (author only)
- `POST /prayer/{prayer_id}/restore` - Restore archived prayer (author only)  
- `POST /prayer/{prayer_id}/answered` - Mark prayer as answered with optional testimony (author only)
- `GET /answered` - Enhanced answered prayers celebration page with statistics

### Prayer Status API
All prayer management endpoints:
- Require full authentication
- Include proper authorization (author-only for status changes)
- Support HTMX for seamless UI updates
- Return enhanced feedback messages
- Log all status changes for audit trail

### Enhanced Feed Endpoints
- `GET /?feed_type=answered` - Answered prayers feed
- `GET /?feed_type=archived` - Personal archived prayers feed (author only)
- Updated feed queries with attribute-based filtering for performance
```

### 5. Development Patterns Updates

#### Add new section: "Prayer Management Patterns"
```markdown
### Prayer Status Management
- `prayer.set_attribute(name, value, user_id, session)` - Set prayer attribute with logging
- `prayer.get_attribute(name, session)` - Retrieve attribute value
- `prayer.remove_attribute(name, session, user_id)` - Remove attribute with logging
- `prayer.has_attribute(name, session)` - Check if attribute exists

### Prayer Lifecycle Functions
- `prayer.is_archived(session)` - Check if prayer is archived
- `prayer.is_answered(session)` - Check if prayer is answered
- `prayer.answer_date(session)` - Get answer date
- `prayer.answer_testimony(session)` - Get answer testimony

### Activity Logging
- Automatic logging for all attribute changes
- Tracks user, action, old/new values, timestamps
- Provides complete audit trail for prayer management
- Supports accountability and debugging

### Permission Patterns
```python
def can_manage_prayer_status(user, prayer):
    return user.id == prayer.author_id or is_admin(user)
```

### Database Query Patterns
```python
# Exclude archived prayers from public feeds
def exclude_archived():
    return ~Prayer.id.in_(
        select(PrayerAttribute.prayer_id)
        .where(PrayerAttribute.attribute_name == 'archived')
    )

# Get prayers with specific attribute
stmt = (
    select(Prayer, User.display_name)
    .join(User, Prayer.author_id == User.id)
    .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
    .where(PrayerAttribute.attribute_name == 'answered')
)
```
```

### 6. HTMX Integration Updates

#### Add to "HTMX Integration" section:
```markdown
### Prayer Status Management (New)
- **Prayer Archiving**: Seamless archive/restore with visual feedback
- **Answered Prayer Modal**: Modal-based testimony collection with form handling
- **Status Transitions**: Smooth animations for status changes
- **Auto-hide Messages**: Success messages with fade-out animations
- **Context-Aware Updates**: Different responses based on prayer status

### Enhanced User Feedback
- **Loading States**: Visual indicators during prayer status changes
- **Success Messages**: Contextual feedback with celebration themes for answered prayers
- **Error Handling**: Graceful error display with recovery options
- **Transition Effects**: Smooth CSS animations for status changes
```

### 7. Security Considerations Updates

#### Add to "Security Considerations" section:
```markdown
### Prayer Management Security (New)
- **Author Authorization**: Only prayer authors can change their prayer status
- **Admin Override**: Administrators can manage any prayer for moderation
- **Audit Trail**: Complete logging of all status changes with user attribution
- **Permission Validation**: Server-side checks for all prayer management actions
- **Data Integrity**: Atomic operations for status changes with transaction safety

### Privacy Controls
- **Archived Prayer Privacy**: Archived prayers visible only to authors
- **Testimony Moderation**: Optional testimony content with community visibility
- **Activity Logging**: Transparent audit trail while protecting sensitive information
```

### 8. Performance Considerations

#### Add new section: "Performance Optimizations"
```markdown
### Database Performance (New)
- **Optimized Indexes**: Composite indexes on prayer attributes for efficient filtering
- **WAL Mode**: SQLite Write-Ahead Logging for better concurrency
- **Query Optimization**: Attribute-based filtering with proper JOIN optimization
- **Connection Pooling**: Enhanced database connection management

### Query Performance
```sql
-- Efficient indexes created
CREATE INDEX idx_prayer_attributes_prayer_attr ON prayer_attributes(prayer_id, attribute_name);
CREATE INDEX idx_prayer_attributes_attr_name ON prayer_attributes(attribute_name);
CREATE INDEX idx_prayers_created_at ON prayer(created_at);
CREATE INDEX idx_prayers_author_id ON prayer(author_id);
```

### Feed Performance
- **Attribute filtering** optimized with proper indexing
- **Count queries** use efficient aggregations
- **Status combinations** handled without N+1 query problems
- **Pagination ready** for large prayer datasets
```

### 9. UI/UX Design Updates

#### Update "UI/UX Design Patterns" section:
```markdown
### Prayer Status Management UI (New)
- **Author Controls**: Management buttons visible only to prayer authors
- **Status Indicators**: Visual badges for archived and answered prayers
- **Celebration Design**: Special styling for answered prayers with testimonies
- **Modal Interactions**: Testimony collection with accessible modal design

### Enhanced Visual Hierarchy
- **Status-Aware Styling**: Different background colors for prayer statuses
- **Answered Prayer Celebration**: Prominent celebration styling with testimonies
- **Archive Indicators**: Subtle styling for archived prayer visibility
- **Management Controls**: Contextual buttons based on prayer status and user permissions

### Feed Navigation Enhancements
- **New Feed Tabs**: Answered Prayers and Archived feeds with appropriate counts
- **Conditional Visibility**: Archived tab only appears when user has archived prayers
- **Status Counts**: Real-time counts for each feed type including new categories
- **Celebration Access**: Special handling for answered prayers celebration page
```

### 10. Common Development Tasks Updates

#### Add to "Common Development Tasks" section:
```markdown
### Adding Prayer Status Attributes
1. Define new attribute name in attribute system
2. Add helper methods to Prayer model if needed
3. Update feed queries if attribute affects visibility
4. Add UI controls for managing the attribute
5. Ensure proper permission checks

### Creating Prayer Management Features
1. Add new route with proper authorization
2. Implement attribute operations with logging
3. Update UI with appropriate controls
4. Test permission boundaries
5. Add HTMX integration for seamless updates

### Prayer Lifecycle Modifications
- Use flexible attribute system instead of database columns
- Implement proper activity logging for audit trail
- Consider feed visibility impacts
- Maintain backward compatibility with existing prayers
```

## Implementation Priority

### Phase 1: Core Architecture Documentation
1. Update database schema section with new models
2. Add prayer lifecycle management overview
3. Document the attributes system architecture

### Phase 2: Feature Documentation
1. Update feed types and API endpoints
2. Add prayer management patterns and examples
3. Document security and permission model

### Phase 3: Development Guidelines
1. Add development patterns for attributes system
2. Update HTMX integration examples
3. Add performance considerations and optimization notes

## Migration Notes

### Backward Compatibility
```markdown
### Migration Considerations (New Section)
- **Automatic Migration**: Existing flagged prayers automatically migrated to attributes system
- **Preserved Functionality**: All existing features continue to work unchanged
- **Data Integrity**: No data loss during migration from boolean flags to attributes
- **Performance**: Enhanced query performance with proper indexing
- **Future-Proof**: Extensible system for future prayer status needs

### Upgrade Path
1. **Automatic Database Migration**: New tables created on first run
2. **Existing Data Preservation**: All prayer data and marks preserved
3. **Flag Migration**: Boolean flags converted to attribute system
4. **Index Creation**: Performance indexes created automatically
5. **Backward Compatibility**: Existing API endpoints continue to work
```

This comprehensive update will ensure the AI_PROJECT_GUIDE.md accurately reflects the new prayer archive and answered system while maintaining clarity for future development and AI assistance.