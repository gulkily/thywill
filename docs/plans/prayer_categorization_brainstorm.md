# Prayer Categorization System Design - SPLIT INTO FOCUSED PLANS

## 📋 This Document Has Been Split
This original brainstorm has been divided into two focused implementation plans:

- **[Prayer Categorization Plan](prayer_categorization_plan.md)** - Safety filtering, specificity classification, and subject matter categories
- **[Temporal Prayer Handling Plan](temporal_prayer_handling_plan.md)** - Time-sensitive prayer lifecycle management

## Original Brainstorm Content
This document outlines a comprehensive categorization system for prayers during the generation process, focusing on content filtering, specificity classification, and additional meaningful categories.

## Current System Analysis

### Existing Data Model
- **Prayer Model**: Contains `text` (user request) and `generated_prayer` (AI-generated prayer)
- **PrayerAttribute System**: Flexible key-value attributes for prayers (currently used for: archived, answered, flagged)
- **Generation Process**: Uses Claude 3.5 Sonnet with community-focused system prompt
- **Current Filtering**: Basic flagging system (boolean), archived status, answered status

### Sample Content Patterns
Based on database analysis of 54 prayers:
- **Health & Wellbeing**: "Pete's continued health and wellbeing"
- **Life Transitions**: "Nevin's daughter's journey to college" 
- **Daily Needs**: "Please pray for our dinner"
- **Work & Purpose**: "Help me test new features for this prayer application"
- **Extended Requests**: Complex, detailed prayer requests

## Proposed Categorization System

### 1. Negativity Detection & Filtering

#### Implementation Approach
```python
# New field in Prayer model
prayer_safety_score: float = Field(default=1.0)  # 0.0 = definitely negative, 1.0 = positive
prayer_safety_flags: str | None = Field(default=None)  # JSON array of safety concerns
```

#### Safety Categories
- **Harmful Intent**: Wishing harm, violence, or negative outcomes
- **Vindictive**: Prayers for revenge or punishment of others
- **Manipulative**: Attempting to control others against their will
- **Destructive**: Prayers for destruction of property/relationships

#### Default Behavior
- Prayers with safety_score < 0.7 hidden from public feeds by default
- Users can opt-in to see filtered content in settings
- All negative prayers still transformed positively during generation
- Moderation queue for manual review of flagged content

### 2. Specificity Classification

#### Primary Categories

**SPECIFIC (Personal/Individual)**
- Named individuals or specific relationships
- Personal circumstances and situations  
- Individual health concerns
- Personal life decisions and transitions
- Family-specific requests

*Examples*:
- "Pete's continued health"
- "Nevin's daughter's college journey"
- "My job interview tomorrow"
- "Sarah's recovery from surgery"

**GENERAL (Broad/Community)**
- World events and global concerns
- Community-wide issues
- Natural disasters and crises
- Societal problems and healing
- Abstract concepts (peace, justice, etc.)

*Examples*:
- "World peace"
- "Our nation's leaders" 
- "End to hunger worldwide"
- "Healing for our community"
- "Wisdom for church leadership"

#### Implementation
```python
# New fields in Prayer model
specificity_type: str = Field(default="unknown")  # "specific", "general", "mixed"
specificity_confidence: float = Field(default=0.0)  # AI confidence in classification
```

### 3. Additional Category Dimensions

#### Subject Matter Categories
- **Health & Healing**: Physical, mental, emotional wellbeing
- **Relationships**: Family, friendships, romantic, community
- **Work & Purpose**: Career, calling, ministry, service
- **Spiritual Growth**: Faith development, discipleship, spiritual battles
- **Provision & Resources**: Financial, material needs, basic necessities
- **Protection & Safety**: Physical safety, spiritual protection, travel
- **Guidance & Wisdom**: Decision-making, life direction, understanding
- **Gratitude & Praise**: Thanksgiving, celebration, recognition
- **Life Transitions**: Birth, death, marriage, moves, graduations
- **Crisis & Emergency**: Immediate urgent needs, disasters, trauma

#### Urgency Levels
- **Immediate**: Crisis situations requiring urgent prayer
- **Ongoing**: Long-term situations and chronic needs
- **Future**: Upcoming events and anticipated needs
- **Maintenance**: General wellbeing and spiritual growth

#### Temporal Characteristics
- **Time-Specific**: Prayers with explicit dates/times ("this Thursday", "tomorrow's surgery")
- **Event-Driven**: Tied to specific upcoming events regardless of date
- **Open-Ended**: No specific timeframe mentioned
- **Recurring**: Regular/repeated prayer needs

#### Community Scope
- **Individual**: Single person focus
- **Family**: Family unit or household
- **Local Community**: Church, neighborhood, local area
- **Regional**: City, state, region-wide concerns
- **Global**: International, worldwide issues

## Implementation Strategy

### Phase 1: Basic Categorization
1. Add new fields to Prayer model for categories
2. Implement AI-based categorization during prayer generation
3. Update system prompt to include categorization instructions
4. Add category filtering to feed queries

### Phase 2: Safety System
1. Implement negativity detection using Claude analysis
2. Add safety scoring and flagging system
3. Create moderation interface for staff review
4. Add user preference controls for filtered content

### Phase 3: Advanced Features
1. Category-based feed filtering
2. Prayer analytics and trending topics
3. Automated prayer partner matching by category compatibility
4. Category-specific prayer prompts and resources

## Database Schema Changes

```sql
-- Add categorization columns to Prayer table
ALTER TABLE prayer ADD COLUMN specificity_type VARCHAR(20) DEFAULT 'unknown';
ALTER TABLE prayer ADD COLUMN specificity_confidence REAL DEFAULT 0.0;
ALTER TABLE prayer ADD COLUMN subject_category VARCHAR(50);
ALTER TABLE prayer ADD COLUMN urgency_level VARCHAR(20) DEFAULT 'ongoing';
ALTER TABLE prayer ADD COLUMN community_scope VARCHAR(20) DEFAULT 'individual';
ALTER TABLE prayer ADD COLUMN safety_score REAL DEFAULT 1.0;
ALTER TABLE prayer ADD COLUMN safety_flags TEXT; -- JSON array

-- Temporal handling columns
ALTER TABLE prayer ADD COLUMN temporal_type VARCHAR(20) DEFAULT 'open_ended';
ALTER TABLE prayer ADD COLUMN target_date DATE; -- Extracted date for time-specific prayers
ALTER TABLE prayer ADD COLUMN event_description VARCHAR(255); -- "surgery", "interview", "wedding"
ALTER TABLE prayer ADD COLUMN expires_at TIMESTAMP; -- Auto-calculated based on target_date + buffer

-- Index for efficient filtering and temporal queries
CREATE INDEX idx_prayer_categories ON prayer(specificity_type, subject_category, safety_score);
CREATE INDEX idx_prayer_temporal ON prayer(temporal_type, target_date, expires_at);
```

## AI Integration Approach

### Enhanced System Prompt
Extend the existing prayer generation system prompt to include:
1. Categorization analysis instructions
2. Safety evaluation criteria  
3. Structured output format for categories
4. Positive transformation guidelines for negative content

### Sample Enhanced Prompt Addition
```
After generating the prayer, analyze it for categorization:
- Specificity: Is this for a specific person/situation (SPECIFIC) or broader concern (GENERAL)?
- Subject: What is the primary category? (health, relationships, work, spiritual, provision, protection, guidance, gratitude, transitions, crisis)
- Urgency: Is this immediate, ongoing, future, or maintenance?
- Scope: Individual, family, community, regional, or global?
- Safety: Any concerning content requiring moderation? (0.0-1.0 safety score)

Provide categories in structured format at the end.
```

## User Experience Considerations

### Feed Organization
- **Default View**: Show all categories with safety score > 0.7
- **Category Filters**: Allow users to focus on specific types
- **Urgency Indicators**: Visual cues for immediate/crisis prayers
- **Scope Badges**: Show individual vs. community prayer indicators

### Privacy & Sensitivity  
- **Specific prayers**: May need additional privacy controls
- **Sensitive topics**: Health, relationships may require special handling
- **Community guidelines**: Clear expectations for appropriate content

### Matching & Recommendations
- **Prayer Partners**: Match based on category preferences and experience
- **Related Prayers**: Suggest similar prayers for continued intercession
- **Topic Following**: Allow users to subscribe to specific categories

## Migration Strategy

### Backward Compatibility
- All existing prayers default to "unknown" categories
- Gradual re-categorization through background processing
- Manual categorization tools for staff to review historical content

### Testing & Validation
- A/B test categorization accuracy with manual review
- User feedback on category assignments  
- Monitor for edge cases and refine classification logic

### Rollout Plan
1. **Week 1-2**: Database schema updates and basic categorization
2. **Week 3-4**: Safety system implementation and testing
3. **Week 5-6**: User interface updates for category filtering  
4. **Week 7+**: Advanced features and analytics

## Temporal Prayer Handling

### Time-Sensitive Prayer Challenges
- **"This Thursday"**: Relative dates that become stale quickly
- **"Tomorrow's surgery"**: Events that pass but may need follow-up prayer
- **"Next week's interview"**: Future events needing countdown emphasis
- **"Daily prayers"**: Recurring needs vs. one-time events

### Proposed Solutions

#### 1. Intelligent Date Extraction
```python
# During prayer generation, extract temporal information
temporal_parser = TemporalParser()
result = temporal_parser.extract_date("pray for my surgery this Thursday")
# Returns: {"target_date": "2025-07-24", "event": "surgery", "confidence": 0.95}
```

#### 2. Automatic Prayer Lifecycle Management
- **Pre-Event Phase**: Prayer appears in feeds with countdown ("2 days until surgery")
- **Event Day**: Special prominence with "Today: Sarah's surgery" 
- **Post-Event Grace Period**: 3-7 days for outcome prayers/praise reports
- **Auto-Archive**: Move to "completed events" after grace period

#### 3. Dynamic Prayer Text Updates
```python
# Transform relative dates into absolute dates during generation
"Pray for my surgery this Thursday" 
→ Generated: "...as they prepare for surgery on July 24th..."

# Add temporal context to generated prayers  
"Divine Creator, we lift up [name] as they prepare for surgery on July 24th. 
Give the medical team wisdom and skill, and grant [name] peace and healing..."
```

#### 4. Smart Feed Prioritization  
- **Temporal Urgency Boost**: Time-specific prayers get higher feed ranking as date approaches
- **"Prayer Calendar" View**: Optional calendar interface showing upcoming prayer events
- **Countdown Indicators**: Visual cues like "🕒 2 days" for approaching events

#### 5. Follow-up Prayer Suggestions
- **Day-Of Reminders**: "Today is the day we've been praying for Sarah's surgery"
- **Outcome Prompts**: "It's been 3 days since the surgery - pray for Sarah's recovery"
- **Praise Report Integration**: Easy conversion to answered prayer/testimony

#### 6. Handling Edge Cases
- **Ambiguous Dates**: "next week" → prompt user for clarification or use best guess with low confidence
- **Past Dates**: "yesterday's results" → still valid for ongoing concerns  
- **Recurring Events**: "every Sunday service" → create recurring prayer template

### Implementation Strategy

#### Phase 1: Basic Date Recognition
1. Add temporal parsing to prayer generation
2. Extract explicit dates and events 
3. Set expiration dates automatically
4. Add countdown displays in feeds

#### Phase 2: Lifecycle Management
1. Pre/during/post event prayer states
2. Automatic archiving of completed events
3. Follow-up prayer suggestions
4. Integration with praise reports

#### Phase 3: Advanced Features  
1. Prayer calendar views
2. Recurring prayer templates
3. Community prayer reminders
4. Temporal analytics and insights

### User Experience Benefits
- **Relevance**: No more stale "this Thursday" prayers on Saturday
- **Engagement**: Timely reminders keep community invested in outcomes
- **Organization**: Clear distinction between ongoing and event-based prayers
- **Follow-through**: Natural progression from request → event → outcome → praise

## Conclusion

This categorization system provides:
1. **Safety**: Proactive filtering of potentially harmful content
2. **Organization**: Clear taxonomy for prayer types and focus areas  
3. **Personalization**: User control over feed content and preferences
4. **Community**: Better matching and shared prayer experiences
5. **Temporal Awareness**: Smart handling of time-sensitive prayers and events
6. **Insights**: Analytics on prayer patterns and community needs

The system maintains the reverent, community-focused nature of the platform while adding powerful organizational, safety, and temporal features to support the growing prayer community.