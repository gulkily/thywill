# Prayer Archive and Answered Feature Implementation Plan

## Overview
This plan outlines the implementation of archive and answered prayer functionality, allowing prayer authors to manage the lifecycle of their prayer requests while maintaining community engagement history.

## Current System Analysis

### Existing Prayer States
- **Active** (`flagged = False`): Visible in public feeds
- **Flagged** (`flagged = True`): Hidden from public view, requires moderation

### Limitations
- No comprehensive status system beyond flagging
- Prayer authors cannot manage their own requests
- No way to mark prayers as resolved or answered
- Prayers remain active indefinitely

## Proposed Feature Design

### 1. Enhanced Prayer Attribute System

#### New Prayer Attributes Table
Replace the simple `flagged` boolean with a flexible prayer-attributes relationship:

```python
# New PrayerAttribute model in models.py
class PrayerAttribute(db.Model):
    __tablename__ = 'prayer_attributes'
    
    id = db.Column(db.String(32), primary_key=True, default=lambda: secrets.token_hex(16))
    prayer_id = db.Column(db.String(32), db.ForeignKey('prayer.id'), nullable=False)
    attribute_name = db.Column(db.String(50), nullable=False)
    attribute_value = db.Column(db.String(255), nullable=True, default='true')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(32), db.ForeignKey('user.id'), nullable=True)
    
    # Composite index for efficient querying
    __table_args__ = (
        db.Index('idx_prayer_attribute', 'prayer_id', 'attribute_name'),
        db.Index('idx_attribute_name', 'attribute_name'),
        db.UniqueConstraint('prayer_id', 'attribute_name', name='unique_prayer_attribute')
    )

# Enhanced Prayer model with attribute helpers
class Prayer(db.Model):
    # existing fields...
    
    def has_attribute(self, name):
        return PrayerAttribute.query.filter_by(prayer_id=self.id, attribute_name=name).first() is not None
    
    def get_attribute(self, name):
        attr = PrayerAttribute.query.filter_by(prayer_id=self.id, attribute_name=name).first()
        return attr.attribute_value if attr else None
    
    def set_attribute(self, name, value='true', user_id=None):
        attr = PrayerAttribute.query.filter_by(prayer_id=self.id, attribute_name=name).first()
        if attr:
            attr.attribute_value = value
        else:
            attr = PrayerAttribute(
                prayer_id=self.id, 
                attribute_name=name, 
                attribute_value=value,
                created_by=user_id
            )
            db.session.add(attr)
    
    def remove_attribute(self, name):
        PrayerAttribute.query.filter_by(prayer_id=self.id, attribute_name=name).delete()
    
    # Convenience properties
    @property
    def is_archived(self):
        return self.has_attribute('archived')
    
    @property
    def is_answered(self):
        return self.has_attribute('answered')
    
    @property
    def is_flagged(self):
        return self.has_attribute('flagged')
    
    @property
    def answer_date(self):
        return self.get_attribute('answer_date')
    
    @property
    def answer_testimony(self):
        return self.get_attribute('answer_testimony')
```

#### Attribute Definitions
- **archived**: Prayer hidden from public feeds but preserved with history
- **answered**: Prayer marked as resolved, with optional answer_date and answer_testimony
- **flagged**: Prayer requires moderation, hidden from public view
- **answer_date**: ISO date when prayer was answered
- **answer_testimony**: User's testimony of how prayer was answered
- **archive_reason**: Optional reason for archiving
- **flag_reason**: Reason for flagging (inappropriate content, etc.)

### 2. Database Schema Changes

#### Migration Steps
1. Create new `prayer_attributes` table with proper indexes
2. Migrate existing flagged prayers: `flagged = True` → create 'flagged' attribute
3. Remove deprecated `flagged` column from prayers table after migration
4. Add foreign key constraints and indexes for efficient querying

#### Data Preservation
- All existing prayer marks and activity preserved
- Historical data maintains integrity
- Migration script creates 'flagged' attributes for existing flagged prayers
- Attribute creation timestamps preserve when flags were originally set

#### Query Performance Considerations
```sql
-- Efficient queries using indexes
-- Find all archived prayers
SELECT p.* FROM prayers p 
JOIN prayer_attributes pa ON p.id = pa.prayer_id 
WHERE pa.attribute_name = 'archived';

-- Find active prayers (not archived, not flagged)
SELECT p.* FROM prayers p 
LEFT JOIN prayer_attributes pa1 ON p.id = pa1.prayer_id AND pa1.attribute_name = 'archived'
LEFT JOIN prayer_attributes pa2 ON p.id = pa2.prayer_id AND pa2.attribute_name = 'flagged'
WHERE pa1.id IS NULL AND pa2.id IS NULL;

-- Find answered prayers with testimonies
SELECT p.*, pa1.attribute_value as answer_date, pa2.attribute_value as testimony
FROM prayers p
JOIN prayer_attributes pa1 ON p.id = pa1.prayer_id AND pa1.attribute_name = 'answered'
LEFT JOIN prayer_attributes pa2 ON p.id = pa2.prayer_id AND pa2.attribute_name = 'answer_testimony';
```

### 3. Authorization System

#### User Permissions
- **Prayer Authors**: Can archive or mark their own prayers as answered
- **Community Members**: Can continue praying for archived/answered prayers via direct links
- **Administrators**: Can moderate any prayer status

#### Access Controls
```python
def can_manage_prayer_status(user, prayer):
    return user.id == prayer.author_id or user.is_admin
```

### 4. User Interface Enhancements

#### Prayer Management Controls
Add status management buttons to prayer cards for authors:
- **Archive Prayer** button (moves to archived status)
- **Mark as Answered** button (moves to answered status) 
- **Restore Prayer** button (returns archived prayers to active)

#### Feed System Updates
Enhance existing feed categories:

**Existing Feeds (Modified)**
- **All**: Only active prayers
- **New/Unprayed**: Only active prayers with zero marks
- **Most Prayed**: Only active prayers ranked by marks
- **My Prayers**: Include all statuses with status indicators
- **My Requests**: Include all statuses with management controls

**New Feed Categories**
- **Answered Prayers**: Community celebration of resolved requests
- **Archived**: Personal view for prayer authors only

#### Visual Status Indicators
- **Active**: Default styling (no special indicator)
- **Archived**: Muted styling with "Archived" badge
- **Answered**: Celebratory styling with "Answered" badge and optional testimony section
- **Flagged**: Hidden from public view (admin only)

### 5. Enhanced Prayer Card Design

#### Status-Aware Display
```html
<!-- Prayer card with status indicator -->
<div class="prayer-card status-{{ prayer.status }}">
    {% if prayer.status == 'answered' %}
        <div class="answered-badge">🙏 Prayer Answered</div>
    {% elif prayer.status == 'archived' %}
        <div class="archived-badge">📁 Archived</div>
    {% endif %}
    
    <!-- Existing prayer content -->
    
    {% if current_user.id == prayer.author_id %}
        <div class="prayer-management">
            {% if prayer.status == 'active' %}
                <button class="archive-btn">Archive Prayer</button>
                <button class="answered-btn">Mark as Answered</button>
            {% elif prayer.status == 'archived' %}
                <button class="restore-btn">Restore Prayer</button>
                <button class="answered-btn">Mark as Answered</button>
            {% endif %}
        </div>
    {% endif %}
</div>
```

### 6. Backend Implementation

#### New Routes
```python
@app.route('/prayer/<prayer_id>/archive', methods=['POST'])
@app.route('/prayer/<prayer_id>/answered', methods=['POST'])
@app.route('/prayer/<prayer_id>/restore', methods=['POST'])
```

#### Database Query Updates
- Update feed queries to filter by status
- Maintain efficient indexing for status-based filtering
- Preserve prayer mark functionality across all statuses

#### API Endpoints
- RESTful status update endpoints
- Validation for status transitions
- Proper error handling and user feedback

### 7. Community Engagement Preservation

#### Continued Prayer Access
- Archived/answered prayers remain accessible via direct links
- Users can still mark archived/answered prayers as prayed
- Prayer history and community engagement preserved

#### Answered Prayer Celebration
- Special "Answered Prayers" feed showcases resolved requests
- Optional testimony/update field for answered prayers
- Community can celebrate answered prayers together

### 8. Implementation Stages

#### Stage 1: Core Infrastructure & Basic Archive Functionality
**Goal**: Establish database foundation and basic archive capability

**Database & Backend Changes:**
1. Create `prayer_attributes` table with proper indexes
2. Add `PrayerAttribute` model with helper methods
3. Implement data migration from flagged boolean to attributes system
4. Update Prayer model with attribute convenience properties
5. Create authorization helper functions

**Basic Archive Routes:**
1. `/prayer/<prayer_id>/archive` endpoint (sets 'archived' attribute)
2. `/prayer/<prayer_id>/restore` endpoint (removes 'archived' attribute)
3. Update existing queries to use attribute JOINs for filtering
4. Basic validation and error handling for attribute operations

**Minimal UI Updates:**
1. Add "Archive" and "Restore" buttons to prayer cards (author only)
2. Update "My Requests" feed to show archived prayers with indicators
3. Filter public feeds to exclude archived prayers

**Testing & Validation:**
- Ensure data migration preserves all existing data
- Test archive/restore functionality
- Verify feed filtering works correctly

#### Stage 2: Answered Prayers & Enhanced UI
**Goal**: Add answered prayer functionality and improve user experience

**Answered Prayer Features:**
1. `/prayer/<prayer_id>/answered` endpoint (sets 'answered' attribute with date)
2. "Mark as Answered" button for prayer authors
3. Optional testimony field for answered prayers ('answer_testimony' attribute)
4. Enhanced prayer card styling for prayers with 'answered' attribute

**Feed System Enhancements:**
1. Create "Answered Prayers" public feed
2. Add "Archived" personal feed for prayer authors
3. Update feed navigation with new categories
4. Implement status-aware styling and badges

**User Experience Improvements:**
1. Enhanced prayer card design with status indicators
2. Proper visual feedback for status changes
3. Improved management controls layout
4. Mobile-responsive status management

**Community Features:**
- Preserve prayer marking functionality for all statuses
- Ensure answered prayers remain accessible via direct links
- Add celebratory styling for answered prayers feed

#### Stage 3: Advanced Features & Polish
**Goal**: Add sophisticated features and optimize the complete system

**Advanced Answered Prayer Features:**
1. Optional testimony/update field for answered prayers
2. Answer date tracking and display
3. "How this prayer was answered" section
4. Enhanced answered prayers celebration page

**System Enhancements:**
1. Activity logging for all status changes
2. Advanced error handling and user feedback
3. Performance optimization for status-based queries
4. Comprehensive testing suite

**User Experience Polish:**
1. Smooth animations for status transitions
2. Advanced filtering options in feeds
3. Prayer statistics including status breakdown
4. Improved accessibility features

**Administrative Features:**
1. Admin dashboard for prayer status overview
2. Bulk status management tools
3. Analytics for prayer lifecycle patterns
4. Enhanced moderation capabilities

**Final Testing & Deployment:**
- Load testing with status-based queries
- User acceptance testing for all workflows
- Performance monitoring and optimization
- Documentation and user guides

### 9. Technical Considerations

#### Database Performance
- Utilize composite indexes on `(prayer_id, attribute_name)` for efficient attribute lookups
- Index `attribute_name` for cross-prayer attribute queries
- Monitor query performance with JOIN operations for feed filtering
- Consider materialized views for complex multi-attribute queries if needed

#### Data Migration Strategy
```python
# Migration script for prayer attributes
def migrate_to_prayer_attributes():
    from app import db
    from models import Prayer, PrayerAttribute
    
    # Create new table
    db.create_all()
    
    # Migrate existing flagged prayers
    flagged_prayers = Prayer.query.filter_by(flagged=True).all()
    for prayer in flagged_prayers:
        flagged_attr = PrayerAttribute(
            prayer_id=prayer.id,
            attribute_name='flagged',
            attribute_value='true',
            created_at=prayer.created_at  # Preserve original timestamp
        )
        db.session.add(flagged_attr)
    
    db.session.commit()
    
    # Verify migration success
    assert PrayerAttribute.query.filter_by(attribute_name='flagged').count() == len(flagged_prayers)
    
    # Drop old flagged column (manual SQL after verification)
    # ALTER TABLE prayers DROP COLUMN flagged;
```

#### Backward Compatibility
- Maintain existing API endpoints during transition
- Gradual rollout with feature flags
- Preserve all existing functionality

### 10. User Experience Flow

#### Prayer Author Experience
1. **Create Prayer**: Standard flow, prayer starts as 'active'
2. **Manage Prayer**: Author sees management controls on their prayers
3. **Archive Prayer**: Prayer moves to personal archive, hidden from public feeds
4. **Mark Answered**: Prayer moves to answered status, appears in celebration feed
5. **Restore Prayer**: Archived prayers can return to active status

#### Community Member Experience
- Public feeds show only active prayers
- "Answered Prayers" feed shows resolved requests for celebration
- Can still pray for archived/answered prayers if they have direct links
- Prayer history preserved regardless of status changes

### 11. Success Metrics

#### User Engagement
- Percentage of prayer authors using status management
- Community engagement with answered prayers feed
- Retention of prayer marking activity across status changes

#### System Health
- Performance impact of status-based filtering
- Data integrity during migration
- User feedback on new functionality

## Conclusion

This implementation provides prayer authors with meaningful control over their requests while preserving the community aspect of the prayer platform. The phased approach ensures stable deployment with minimal disruption to existing functionality.

The enhanced status system creates opportunities for celebrating answered prayers while allowing natural archival of completed requests, improving the overall user experience and platform engagement.