# Prayer Expiration Date MVP Specification

## Problem Statement
Prayer requests often have natural time boundaries (events, situations with expected resolution dates), but currently require manual archiving. Users forget to archive resolved prayers, leading to stale content in feeds.

## MVP Solution
Add a simple **optional expiration date** field to prayer submission that automatically archives the prayer when the date passes.

## Core Features

### 1. Prayer Submission Enhancement
- Add optional "Expiration Date" field to prayer form
- Default suggestions based on common prayer types:
  - **30 days** (general situations)
  - **7 days** (upcoming events)
  - **90 days** (long-term situations)
- User can select from defaults or set custom date
- Field is completely optional - prayers without dates work as before

### 2. Database Schema
Add single field to Prayer model:
```python
expires_at: datetime | None = Field(default=None)
```

### 3. Automatic Processing
- Daily background job checks for expired prayers
- Automatically sets `archived` attribute on expired prayers
- No notifications, no dismissals - just clean automatic archiving

### 4. UI Indicators
- Show expiration date on prayer cards (author only)
- Simple text: "Expires: Dec 15, 2024"
- No special styling or alerts - just information

## User Stories

**As a prayer author**, I want to set when my prayer should automatically archive so I don't need to remember to do it manually.

**As a prayer author**, I want suggested expiration dates for common situations so I don't have to think about timeframes.

**As a community member**, I want to see current, relevant prayers without outdated requests cluttering the feed.

## Implementation Details

### Prayer Form Changes
```html
<div class="optional-field">
  <label>Prayer expires (optional):</label>
  <select name="expires_preset">
    <option value="">Never expires</option>
    <option value="7">Next week</option>
    <option value="30">Next month</option>
    <option value="90">In 3 months</option>
    <option value="custom">Custom date...</option>
  </select>
  <input type="date" name="expires_at" style="display:none" />
</div>
```

### Background Processing
```python
def expire_prayers():
    """Daily job to archive expired prayers"""
    with Session(engine) as session:
        expired_prayers = session.exec(
            select(Prayer)
            .where(Prayer.expires_at <= datetime.utcnow())
            .where(~Prayer.id.in_(
                select(PrayerAttribute.prayer_id)
                .where(PrayerAttribute.attribute_name == 'archived')
            ))
        ).all()
        
        for prayer in expired_prayers:
            prayer.set_attribute('archived', 'true', 'system', session)
```

### Prayer Card Display
```html
{% if p.expires_at and p.author_id == me.display_name %}
  <div class="text-xs text-gray-500">
    Expires: {{ p.expires_at.strftime('%b %d, %Y') }}
  </div>
{% endif %}
```

## Technical Requirements

1. **Database Migration**: Add `expires_at` column to Prayer table
2. **Form Enhancement**: Add expiration date selection to submission form
3. **Display Update**: Show expiration date on prayer cards (author only)
4. **Background Job**: Add expiration check to existing daily maintenance
5. **Feature Flag**: `PRAYER_EXPIRATION_ENABLED=true/false`

## Success Metrics

- Reduced manually archived prayers (users rely on automatic expiration)
- Improved feed relevance (fewer stale prayers)
- User adoption of expiration dates on new prayers

## Non-Goals (Future Iterations)

- AI-suggested expiration dates
- Expiration notifications or warnings
- User dismissal of expiration
- Postponing expiration dates
- Complex UI for expiration management

## Implementation Estimate

- **2 hours**: Database schema + migration
- **2 hours**: Form updates + submission handling  
- **1 hour**: Prayer card display updates
- **1 hour**: Background processing integration
- **1 hour**: Testing and edge cases

**Total: ~7 hours for complete MVP**

This simple approach provides 80% of the value with 20% of the complexity, and creates a solid foundation for future enhancements.