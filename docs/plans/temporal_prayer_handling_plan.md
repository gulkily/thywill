# Temporal Prayer Handling Implementation Plan

## Overview
Implement intelligent handling of time-sensitive prayers to solve the "this Thursday" problem. This system will extract dates from prayer requests, manage prayer lifecycles around events, and provide timely community engagement through countdown indicators and follow-up prompts.

## Problem Statement

### Current Challenges
- **Stale Relative Dates**: "This Thursday" becomes meaningless after Thursday passes
- **Lost Follow-up**: No tracking of prayer outcomes after events occur
- **Poor Prioritization**: Time-sensitive prayers don't get urgency-appropriate visibility
- **Missed Engagement**: Community loses connection to prayer outcomes

### Examples of Time-Sensitive Prayers
- **Specific Dates**: "tomorrow's surgery", "this Thursday's job interview"
- **Relative Times**: "next week's wedding", "in two days"
- **Event-Driven**: "upcoming surgery" (date TBD), "when results come in"
- **Recurring**: "every Sunday service", "daily prayers for..."

## System Design

### Core Components

#### 1. Temporal Parser Service
**Purpose**: Extract date and event information from prayer text

**Capabilities**:
- Parse absolute dates: "July 24th", "tomorrow", "next Friday"
- Understand relative references: "this week", "in 3 days"
- Extract event context: "surgery", "interview", "wedding", "test results"
- Handle recurring patterns: "every Sunday", "daily", "weekly"

**Implementation**:
```python
class TemporalParser:
    def extract_temporal_data(self, text: str) -> dict:
        """
        Returns: {
            'target_date': date | None,
            'event_type': str | None, 
            'temporal_type': 'specific' | 'event_driven' | 'recurring' | 'open_ended',
            'confidence': float,
            'recurring_pattern': str | None
        }
        """
```

#### 2. Prayer Lifecycle Manager
**Purpose**: Handle prayers through temporal phases

**Phases**:
- **Pre-Event**: Active prayer with countdown display
- **Event Day**: Special prominence and community reminders  
- **Post-Event**: Grace period for outcome updates
- **Follow-up**: Prompts for praise reports or continued prayer
- **Archived**: Completed temporal prayers

#### 3. Dynamic Content Generator
**Purpose**: Convert relative dates to absolute dates in generated prayers

**Transformations**:
- "this Thursday" → "Thursday, July 24th"
- "tomorrow's surgery" → "surgery on July 22nd"
- "next week" → "the week of July 28th"

## Database Schema

```sql
-- Add temporal columns to Prayer table
ALTER TABLE prayer ADD COLUMN temporal_type VARCHAR(20) DEFAULT 'open_ended';
-- Values: 'specific', 'event_driven', 'recurring', 'open_ended'

ALTER TABLE prayer ADD COLUMN target_date DATE; 
-- Extracted/calculated target date for the event

ALTER TABLE prayer ADD COLUMN event_description VARCHAR(255);
-- Extracted event context: 'surgery', 'interview', 'wedding'

ALTER TABLE prayer ADD COLUMN expires_at TIMESTAMP;
-- Auto-calculated end of relevance (target_date + grace_period)

ALTER TABLE prayer ADD COLUMN lifecycle_stage VARCHAR(20) DEFAULT 'active';
-- Values: 'pre_event', 'event_day', 'post_event', 'follow_up', 'completed'

ALTER TABLE prayer ADD COLUMN recurring_pattern VARCHAR(100);
-- For recurring prayers: 'weekly', 'daily', 'monthly_first_sunday'

ALTER TABLE prayer ADD COLUMN confidence_score REAL DEFAULT 0.0;
-- AI confidence in temporal extraction (0.0-1.0)

-- Indexing for temporal queries
CREATE INDEX idx_prayer_temporal ON prayer(temporal_type, target_date, lifecycle_stage);
CREATE INDEX idx_prayer_expiry ON prayer(expires_at, lifecycle_stage);
```

## Implementation Phases

### Phase 1: Basic Temporal Extraction (Week 1-2)
**Goal**: Extract and store temporal information from prayers

**Tasks**:
1. Create `TemporalParser` class with date extraction logic
2. Add temporal columns to Prayer model and database
3. Integrate temporal parsing into `generate_prayer()` function
4. Update system prompt to handle relative date conversion
5. Add temporal indicators to prayer cards in feeds

**Deliverables**:
- Prayers with "tomorrow", "Thursday", etc. get `target_date` populated
- Generated prayers use absolute dates instead of relative dates
- Prayer cards show countdown indicators for upcoming events
- Database migration for new temporal columns

**Acceptance Criteria**:
- 90%+ accuracy on common temporal phrases ("tomorrow", "next week")
- All new time-sensitive prayers receive temporal classification
- Existing prayers remain unaffected (temporal_type = 'open_ended')

### Phase 2: Lifecycle Management (Week 3-4)
**Goal**: Implement prayer lifecycle stages and automatic transitions

**Tasks**:
1. Create `PrayerLifecycleManager` service for stage transitions
2. Implement background job for daily lifecycle updates
3. Add lifecycle stage indicators to UI
4. Create event-day special prominence in feeds
5. Implement automatic expiration/archiving logic

**Deliverables**:
- Daily cron job updates prayer lifecycle stages
- Event-day prayers appear prominently in feeds
- Post-event prayers automatically transition to follow-up stage
- Expired prayers move to archived status

**Acceptance Criteria**:
- Prayers automatically transition between lifecycle stages
- Event-day prayers receive special visibility
- Expired temporal prayers are hidden from active feeds
- Background processing handles stage transitions reliably

### Phase 3: Community Engagement Features (Week 5-6)
**Goal**: Enable community follow-through on prayer outcomes

**Tasks**:
1. Implement follow-up prayer suggestions
2. Create praise report prompts for post-event prayers
3. Add community reminder system for event days
4. Build prayer calendar view (optional)
5. Implement recurring prayer templates

**Deliverables**:
- "Follow-up on Sarah's surgery" prompts appear after events
- Easy conversion from temporal prayer to praise report
- Community members receive reminders about event-day prayers
- Optional calendar interface shows upcoming prayer events

**Acceptance Criteria**:
- Users receive relevant follow-up prompts post-event
- Praise report creation rate increases for temporal prayers
- Community engagement with prayer outcomes improves
- Calendar view displays upcoming events correctly

### Phase 4: Advanced Temporal Features (Week 7-8)
**Goal**: Handle complex temporal patterns and optimize user experience

**Tasks**:
1. Implement recurring prayer pattern recognition
2. Add smart prioritization based on temporal urgency
3. Create temporal prayer analytics and insights
4. Optimize performance for temporal queries
5. Add user preferences for temporal notifications

**Deliverables**:
- Recognition of "every Sunday", "daily" patterns
- Feed algorithms consider temporal urgency in ranking
- Analytics on temporal prayer patterns and outcomes
- Performance-optimized temporal feed queries

**Acceptance Criteria**:
- Recurring prayers handled without creating duplicate entries
- Time-sensitive prayers surface appropriately in feeds
- Temporal analytics provide meaningful community insights
- System performance maintained with temporal features enabled

## AI Integration

### Enhanced System Prompt for Temporal Handling
```
When generating prayers, handle temporal references intelligently:

1. CONVERT RELATIVE DATES to absolute dates:
   - "tomorrow" → "Tuesday, July 22nd" 
   - "this Thursday" → "Thursday, July 24th"
   - "next week" → "the week of July 28th"

2. EXTRACT EVENT INFORMATION:
   - Identify specific events: surgery, interview, wedding, exam, etc.
   - Note any time-sensitive urgency or preparation needs

3. MAINTAIN COMMUNITY FOCUS:
   - Keep third-person perspective for community prayer
   - Include absolute dates so prayers remain relevant over time
   - Add context that helps community understand timing importance

4. TEMPORAL ANALYSIS:
   Return structured temporal data:
   TARGET_DATE: 2025-07-24
   EVENT: surgery
   TEMPORAL_TYPE: specific
   CONFIDENCE: 0.92
```

### Temporal Parser Implementation
```python
import re
from datetime import datetime, timedelta, date
from dateutil.parser import parse as date_parse

class TemporalParser:
    def __init__(self):
        self.relative_patterns = {
            r'\btomorrow\b': lambda: datetime.now().date() + timedelta(days=1),
            r'\btoday\b': lambda: datetime.now().date(),
            r'\bthis (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b': self._parse_this_weekday,
            r'\bnext (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b': self._parse_next_weekday,
            r'\bin (\d+) days?\b': self._parse_in_x_days,
            r'\bnext week\b': lambda: datetime.now().date() + timedelta(weeks=1),
        }
        
        self.event_patterns = {
            r'\b(surgery|operation)\b': 'surgery',
            r'\b(interview|job interview)\b': 'interview', 
            r'\b(wedding|marriage)\b': 'wedding',
            r'\b(exam|test)\b': 'exam',
            r'\b(appointment|meeting)\b': 'appointment',
        }
    
    def extract_temporal_data(self, text: str) -> dict:
        """Extract temporal information from prayer text"""
        result = {
            'target_date': None,
            'event_type': None,
            'temporal_type': 'open_ended',
            'confidence': 0.0,
            'recurring_pattern': None
        }
        
        # Try relative date patterns
        for pattern, parser in self.relative_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                try:
                    result['target_date'] = parser()
                    result['temporal_type'] = 'specific'
                    result['confidence'] = 0.85
                    break
                except:
                    continue
        
        # Extract event type
        for pattern, event_type in self.event_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                result['event_type'] = event_type
                result['confidence'] = max(result['confidence'], 0.7)
                break
                
        # Check for recurring patterns
        recurring_matches = re.search(r'\b(every|daily|weekly|monthly)\b', text, re.IGNORECASE)
        if recurring_matches:
            result['temporal_type'] = 'recurring'
            result['recurring_pattern'] = recurring_matches.group(1).lower()
            result['confidence'] = max(result['confidence'], 0.8)
        
        return result
```

## User Experience

### Feed Interface Enhancements
- **Countdown Indicators**: "🕒 2 days until surgery" on prayer cards
- **Event Day Badges**: "📅 TODAY: Interview Day!" prominence
- **Lifecycle Stages**: Visual indicators for pre/during/post event phases
- **Follow-up Prompts**: "Pray for recovery" suggestions post-event

### Prayer Calendar (Optional)
- Month/week view of upcoming prayer events
- Filter by event type (surgeries, interviews, etc.)
- Community prayer reminders for significant events
- Integration with personal calendars (future enhancement)

### Settings & Preferences
- **Temporal Notifications**: Enable/disable event reminders
- **Follow-up Frequency**: How often to suggest outcome prayers
- **Calendar View**: Enable prayer calendar interface
- **Auto-Archive Timing**: Grace period before temporal prayers expire

## Testing Strategy

### Unit Testing
- Temporal parsing accuracy across various date formats
- Lifecycle stage transition logic
- Date calculation and expiration logic
- Event type extraction from various phrasings

### Integration Testing  
- End-to-end temporal prayer creation and lifecycle
- Background job processing of lifecycle transitions
- Feed filtering and prioritization with temporal data
- Follow-up prompt generation and timing

### User Acceptance Testing
- Real-world temporal prayer scenarios
- Community engagement with event-based prayers
- Follow-up and praise report conversion rates
- Performance with large numbers of temporal prayers

## Success Metrics

### Technical Performance
- 95%+ accuracy in temporal extraction for common phrases
- < 5 seconds for daily lifecycle processing job
- No degradation in feed query performance
- 99%+ reliability in background lifecycle management

### User Engagement
- Increased community interaction with event-based prayers
- Higher follow-up prayer creation rate post-events  
- Reduced stale/irrelevant temporal references in feeds
- Improved praise report conversion from temporal prayers

### Business Impact
- Enhanced community connection through prayer outcomes
- Better prayer relevance leading to increased engagement
- Reduced user complaints about outdated prayer requests
- Foundation for advanced prayer matching and recommendations

This temporal prayer handling system transforms time-sensitive prayer requests from a usability problem into a community engagement opportunity, ensuring prayers remain relevant and fostering follow-through on prayer outcomes.