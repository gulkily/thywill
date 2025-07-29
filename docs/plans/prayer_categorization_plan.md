# Prayer Categorization System Implementation Plan

## Overview
Implement AI-powered categorization during prayer generation to enable content filtering, feed organization, and improved community matching. This implementation integrates with ThyWill's **archive-first architecture** where text files serve as the authoritative source of truth, ensuring categorization data is preserved in human-readable format and survives database reconstruction.

## Current System Analysis

### Existing Architecture
- **Archive-First System**: Text files are written BEFORE database records (see `TEXT_ARCHIVE_DOCUMENTATION.md`)
- **Prayer Model**: `text` (user request), `generated_prayer` (AI-generated prayer), `text_file_path` (archive reference)
- **PrayerAttribute System**: Flexible key-value attributes (archived, answered, flagged)
- **Generation Process**: Claude 3.5 Sonnet with community-focused system prompt
- **Import/Export**: Fully idempotent text archive import system
- **Sample Content**: 54 prayers ranging from health/wellbeing to work/purpose requests

## Categorization Dimensions

### 1. Safety Filtering (Phase 1 Priority)
**Purpose**: Identify and filter potentially harmful content

**Categories**:
- **Harmful Intent**: Wishing harm, violence, or negative outcomes
- **Vindictive**: Prayers for revenge or punishment
- **Manipulative**: Attempting to control others against their will
- **Destructive**: Prayers for destruction of property/relationships

**Implementation**:
- Safety score: 0.0 (definitely negative) to 1.0 (positive)
- Default hide prayers with score < 0.7 from public feeds
- All negative content still transformed positively during generation
- User opt-in setting to view filtered content

### 2. Specificity Classification
**Purpose**: Distinguish personal vs. community-wide prayers

**Categories**:
- **SPECIFIC**: Named individuals, personal circumstances, family requests
  - Examples: "Pete's health", "Nevin's daughter's college journey"
- **GENERAL**: World events, community issues, abstract concepts  
  - Examples: "World peace", "Our nation's leaders", "Community healing"
- **MIXED**: Prayers containing both specific and general elements

### 3. Subject Matter Categories  
**Purpose**: Topical organization for feed filtering and matching

**Primary Categories**:
- **Health & Healing**: Physical, mental, emotional wellbeing
- **Relationships**: Family, friendships, romantic, community
- **Work & Purpose**: Career, calling, ministry, service
- **Spiritual Growth**: Faith development, discipleship, spiritual battles
- **Provision & Resources**: Financial, material needs, necessities
- **Protection & Safety**: Physical safety, spiritual protection, travel
- **Guidance & Wisdom**: Decision-making, life direction, understanding
- **Gratitude & Praise**: Thanksgiving, celebration, recognition
- **Life Transitions**: Birth, death, marriage, moves, graduations
- **Crisis & Emergency**: Immediate urgent needs, disasters, trauma

## Archive-First Implementation Strategy

### Text Archive Format Enhancement

**Enhanced Prayer Archive Format**:
```
Prayer 123 by John_Smith
Submitted January 15 2024 at 14:30
Project: healing
Audience: all
Safety Score: 0.95
Safety Flags: []
Category: health
Specificity: specific
Categorization Method: ai_full
Categorization Confidence: 0.88

Please pray for my grandmother's recovery from surgery.

Generated Prayer:
Heavenly Father, we lift up John's grandmother in prayer...

Activity:
January 15 2024 at 14:35 - Mary_Johnson prayed this prayer
January 16 2024 at 09:20 - John_Smith marked this prayer as answered
```

**Backward Compatibility**: Existing archives without categorization metadata default to safe values during import.

### Database Schema Changes (Cache Layer Only)

```sql
-- Phase 1: Core categorization fields (populated from archives)
ALTER TABLE prayer ADD COLUMN safety_score REAL DEFAULT 1.0;
ALTER TABLE prayer ADD COLUMN safety_flags TEXT DEFAULT '[]';
ALTER TABLE prayer ADD COLUMN categorization_method VARCHAR(20) DEFAULT 'default';

-- Phase 2: Classification fields (populated from archives)
ALTER TABLE prayer ADD COLUMN specificity_type VARCHAR(20) DEFAULT 'unknown';
ALTER TABLE prayer ADD COLUMN specificity_confidence REAL DEFAULT 0.0;
ALTER TABLE prayer ADD COLUMN subject_category VARCHAR(50) DEFAULT 'general';

-- Indexing for efficient filtering
CREATE INDEX idx_prayer_categories ON prayer(specificity_type, subject_category, safety_score);
CREATE INDEX idx_prayer_safety ON prayer(safety_score);

-- IMPORTANT: These fields are populated from text archives during import
-- The text archive is the authoritative source of truth
```

## Implementation Phases

### Phase 1: Archive-First Safety System (Week 1-2)
**Goal**: Implement basic safety filtering with archive-first architecture

**Tasks**:
1. **Archive Format Update**: Enhance `TextArchiveService` to write categorization metadata
2. **Prayer Generation Integration**: Modify `generate_prayer()` to include AI categorization
3. **Archive Writing**: Update `create_prayer_archive()` to include safety metadata
4. **Import Enhancement**: Update `text_importer_service.py` to parse categorization data
5. **Database Population**: Populate Prayer model fields from parsed archive data
6. **Feed Filtering**: Add safety filtering to feed queries (hide score < 0.7)
7. **Admin Interface**: Create interface to review flagged content

**Acceptance Criteria**:
- All new prayers write categorization to text archives FIRST
- Database fields populated from archive data during import
- Safety filtering works from database cache layer
- Archives contain human-readable categorization metadata
- Import process is fully idempotent with categorization data

### Phase 2: Archive-First Full Classification (Week 3-4)
**Goal**: Implement specificity and subject categorization with full archive integration

**Tasks**:
1. **Archive Format Expansion**: Add specificity and subject metadata to archive format
2. **AI Integration Enhancement**: Enhance system prompt with full categorization instructions
3. **Archive Writing**: Update archive creation to include all categorization data
4. **Import Parser Enhancement**: Extend import parser for all categorization fields
5. **Database Schema**: Add remaining classification columns to Prayer model
6. **UI Integration**: Add category badges/indicators to prayer cards in feeds
7. **Feed Filtering**: Create category-based feed filters using database cache

**Acceptance Criteria**:
- Archives contain complete categorization metadata in human-readable format
- All new prayers classified as specific/general with subject categories
- Import process handles all categorization fields idempotently
- Users can filter feeds by category using database cache
- Category information visible in prayer cards
- Archives remain the authoritative source for all categorization data

### Phase 3: Advanced Features with Archive Consistency (Week 5-6)
**Goal**: Enhanced user experience and matching while maintaining archive integrity

**Tasks**:
1. **User Preferences**: Category filtering controls in user settings
2. **Prayer Partner Matching**: Based on category compatibility from database cache
3. **Category Suggestions**: Category-specific prayer prompts and suggestions
4. **Analytics Dashboard**: Category trends from database aggregation
5. **Historical Categorization**: Bulk re-categorization with archive updates
6. **Archive Healing**: Ensure all prayers have categorization metadata in archives
7. **Export Consistency**: Verify export includes all categorization data

**Acceptance Criteria**:
- Users can set category preferences in settings
- Prayer partner suggestions consider category interests from cached data
- Historical prayers categorized and written back to archives
- Admin dashboard shows category distribution and trends
- All categorization changes update both archive and database
- Export/import maintains full categorization data consistency

## AI Integration

### Enhanced System Prompt Addition
```
After generating the prayer, analyze it for categorization:

SAFETY EVALUATION:
- Does this request contain harmful intent, vindictive wishes, manipulative goals, or destructive desires?
- Rate safety from 0.0 (definitely concerning) to 1.0 (completely positive)
- If score < 1.0, list specific concerns

CATEGORIZATION:
- Specificity: SPECIFIC (named individuals/personal situations) or GENERAL (community/world concerns)?
- Subject: Which primary category? (health, relationships, work, spiritual, provision, protection, guidance, gratitude, transitions, crisis)
- Confidence: How certain are you of these classifications? (0.0-1.0)

Return structured format:
SAFETY_SCORE: 0.95
SAFETY_FLAGS: []
SPECIFICITY: SPECIFIC
SUBJECT: health
CONFIDENCE: 0.88
```

### Archive-First Categorization Integration

```python
DEFAULT_CATEGORIZATION = {
    'safety_score': 1.0,  # Assume safe if analysis fails
    'specificity_type': 'unknown',
    'subject_category': 'general',
    'safety_flags': [],
    'categorization_method': 'default_fallback',
    'categorization_confidence': 0.0
}

def create_prayer_with_categorization(prayer_text: str, user: User, **kwargs) -> Prayer:
    """Archive-first prayer creation with categorization"""
    
    # Step 1: Generate prayer with categorization
    ai_response = generate_prayer_with_categorization(prayer_text)
    generated_prayer, categorization = parse_prayer_and_categorization(ai_response)
    
    # Step 2: Apply fallback if needed
    if not categorization:
        categorization = categorize_prayer_with_fallback(prayer_text)
    
    # Step 3: Write to archive FIRST (archive-first principle)
    archive_data = {
        'prayer_text': prayer_text,
        'generated_prayer': generated_prayer,
        'author': user.display_name,
        'categorization': categorization,
        **kwargs
    }
    archive_path = text_archive_service.create_prayer_archive_with_categorization(archive_data)
    
    # Step 4: Create database record with archive reference
    prayer = Prayer(
        text=prayer_text,
        generated_prayer=generated_prayer,
        author_id=user.id,
        text_file_path=archive_path,
        # Populate categorization fields from archive data
        safety_score=categorization['safety_score'],
        safety_flags=json.dumps(categorization['safety_flags']),
        specificity_type=categorization['specificity_type'],
        subject_category=categorization['subject_category'],
        categorization_method=categorization['categorization_method'],
        **kwargs
    )
    
    return prayer

class TextArchiveService:
    def create_prayer_archive_with_categorization(self, archive_data: dict) -> str:
        """Create prayer archive with categorization metadata"""
        
        categorization = archive_data['categorization']
        
        content = f"""Prayer {archive_data.get('prayer_id', 'NEW')} by {archive_data['author']}
Submitted {datetime.now().strftime('%B %d %Y at %H:%M')}
Project: {archive_data.get('tag', 'general')}
Audience: {archive_data.get('target_audience', 'all')}
Safety Score: {categorization['safety_score']}
Safety Flags: {categorization['safety_flags']}
Category: {categorization['subject_category']}
Specificity: {categorization['specificity_type']}
Categorization Method: {categorization['categorization_method']}
Categorization Confidence: {categorization.get('categorization_confidence', 0.0)}

{archive_data['prayer_text']}

Generated Prayer:
{archive_data['generated_prayer']}

Activity:
"""
        
        archive_path = self._get_prayer_archive_path()
        self._write_file_atomic(archive_path, content)
        return archive_path

def parse_prayer_archive_with_categorization(archive_path: str) -> dict:
    """Parse prayer archive including categorization metadata"""
    
    with open(archive_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    data = {}
    
    for line in lines:
        if line.startswith('Safety Score:'):
            data['safety_score'] = float(line.split(':', 1)[1].strip())
        elif line.startswith('Safety Flags:'):
            flags_str = line.split(':', 1)[1].strip()
            data['safety_flags'] = json.loads(flags_str) if flags_str != '[]' else []
        elif line.startswith('Category:'):
            data['subject_category'] = line.split(':', 1)[1].strip()
        elif line.startswith('Specificity:'):
            data['specificity_type'] = line.split(':', 1)[1].strip()
        elif line.startswith('Categorization Method:'):
            data['categorization_method'] = line.split(':', 1)[1].strip()
        elif line.startswith('Categorization Confidence:'):
            data['categorization_confidence'] = float(line.split(':', 1)[1].strip())
    
    # Apply defaults for missing fields (backward compatibility)
    for key, default_value in DEFAULT_CATEGORIZATION.items():
        if key not in data:
            data[key] = default_value
    
    return data

# Enhanced text importer for categorization
class TextImporterService:
    def _import_prayer_with_categorization(self, archive_data: dict) -> Prayer:
        """Import prayer with categorization from archive"""
        
        # Parse categorization from archive
        categorization = parse_prayer_archive_with_categorization(archive_data['archive_path'])
        
        # Create prayer with categorization fields populated
        prayer = Prayer(
            text=archive_data['prayer_text'],
            generated_prayer=archive_data['generated_prayer'],
            author_id=archive_data['author_id'],
            text_file_path=archive_data['archive_path'],
            # Populate from archive data
            safety_score=categorization['safety_score'],
            safety_flags=json.dumps(categorization['safety_flags']),
            specificity_type=categorization['specificity_type'],
            subject_category=categorization['subject_category'],
            categorization_method=categorization['categorization_method']
        )
        
        return prayer
```

## User Experience

### Feed Interface
- **Safety Toggle**: "Show filtered content" option in user settings
- **Category Filters**: Dropdown/checkboxes for subject categories
- **Specificity Toggle**: "Show specific prayers" / "Show general prayers"
- **Category Badges**: Small indicators on prayer cards showing category

### Admin Interface
- **Safety Review Queue**: List of prayers with safety_score < 0.8
- **Category Override**: Manual category assignment for edge cases
- **Analytics**: Category distribution, safety flag trends
- **Bulk Operations**: Re-categorize prayers, adjust safety thresholds

## Graceful Degradation Strategies

### Circuit Breaker Pattern
```python
class CategorizationCircuitBreaker:
    def __init__(self, failure_threshold=0.2, cooldown_minutes=15):
        self.failure_threshold = failure_threshold
        self.cooldown_period = timedelta(minutes=cooldown_minutes)
        self.failure_count = 0
        self.total_attempts = 0
        self.last_failure_time = None
        self.is_open = False
    
    def should_attempt_ai_categorization(self) -> bool:
        if not self.is_open:
            return True
            
        # Check if cooldown period has passed
        if datetime.now() - self.last_failure_time > self.cooldown_period:
            self.is_open = False
            self.failure_count = 0
            self.total_attempts = 0
            return True
            
        return False
    
    def record_attempt(self, success: bool):
        self.total_attempts += 1
        if not success:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
        # Open circuit if failure rate exceeds threshold
        if self.total_attempts >= 10:  # Minimum attempts before evaluation
            failure_rate = self.failure_count / self.total_attempts
            if failure_rate > self.failure_threshold:
                self.is_open = True
```

### Progressive Retry Strategy
```python
async def categorize_with_progressive_fallback(prayer_text: str) -> dict:
    """Progressive retry with increasing timeouts and simpler analysis"""
    
    # Attempt 1: Full AI categorization (5s timeout)
    try:
        response = await ai_categorize_full(prayer_text, timeout=5)
        return parse_ai_categorization(response)
    except TimeoutError:
        log_categorization_error("Full AI categorization timeout")
    except Exception as e:
        log_categorization_error("Full AI categorization failed", e)
    
    # Attempt 2: Safety-only analysis (2s timeout)
    try:
        safety_score = await ai_safety_check_only(prayer_text, timeout=2)
        fallback_categories = keyword_based_categorization(prayer_text)
        fallback_categories['safety_score'] = safety_score
        fallback_categories['categorization_method'] = 'hybrid_fallback'
        return fallback_categories
    except Exception as e:
        log_categorization_error("Safety-only analysis failed", e)
    
    # Attempt 3: Pure keyword fallback
    return keyword_based_categorization(prayer_text)
```

### Background Processing Queue
```python
class BackgroundCategorizationService:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.is_running = False
    
    async def queue_for_categorization(self, prayer_id: int, prayer_text: str):
        """Queue prayer for background categorization"""
        await self.queue.put({
            'prayer_id': prayer_id,
            'prayer_text': prayer_text,
            'queued_at': datetime.now()
        })
    
    async def process_queue(self):
        """Background worker to process categorization queue"""
        while self.is_running:
            try:
                item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                # Try full AI categorization with no time pressure
                categories = await ai_categorize_full(item['prayer_text'], timeout=30)
                
                # Update prayer in database
                await update_prayer_categories(item['prayer_id'], categories)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                log_categorization_error("Background processing failed", e)
```

### User-Driven Classification
```python
# Add to prayer submission form
class PrayerSubmissionForm:
    def __init__(self):
        self.optional_category_help = """
        <div class="category-help" style="display: none;">
            <p>Help us categorize your prayer (optional):</p>
            <select name="suggested_category">
                <option value="">Not sure</option>
                <option value="health">Health & Healing</option>
                <option value="relationships">Relationships</option>
                <option value="work">Work & Purpose</option>
                <!-- ... other categories -->
            </select>
            <label>
                <input type="checkbox" name="is_specific"> 
                This prayer mentions specific people or situations
            </label>
        </div>
        """

# Community classification feature
def show_classification_prompt(prayer_id: int, user_id: int) -> bool:
    """Show classification prompt to users for unclear categorizations"""
    prayer = get_prayer(prayer_id)
    
    # Only show for prayers with low confidence or failed categorization
    if (prayer.specificity_confidence < 0.5 or 
        prayer.categorization_method in ['keyword_fallback', 'default_fallback']):
        
        # Don't overwhelm users - limit to 1 prompt per day
        if not user_has_classified_today(user_id):
            return True
    
    return False
```

### Database Resilience
```python
# Add categorization method tracking
ALTER TABLE prayer ADD COLUMN categorization_method VARCHAR(20) DEFAULT 'ai_full';
ALTER TABLE prayer ADD COLUMN categorization_attempted_at TIMESTAMP;
ALTER TABLE prayer ADD COLUMN categorization_retry_count INTEGER DEFAULT 0;

# Graceful schema handling
def ensure_categorization_columns():
    """Ensure categorization columns exist with safe defaults"""
    try:
        # Check if columns exist, add if missing
        columns_to_add = [
            ('safety_score', 'REAL DEFAULT 1.0'),
            ('safety_flags', 'TEXT DEFAULT "[]"'),
            ('categorization_method', 'VARCHAR(20) DEFAULT "default"')
        ]
        
        for column, definition in columns_to_add:
            if not column_exists('prayer', column):
                execute_sql(f'ALTER TABLE prayer ADD COLUMN {column} {definition}')
                
    except Exception as e:
        log_error("Failed to ensure categorization columns", e)
        # Continue without categorization features
```

## Testing Strategy

### Unit Tests
- AI response parsing functions with malformed input handling
- Safety score calculation logic with edge cases
- Category assignment validation with invalid data
- Feed filtering with various category combinations
- Fallback mechanism testing with simulated failures
- Circuit breaker behavior under different failure scenarios

### Integration Tests
- End-to-end prayer generation with categorization failures
- Feed queries with category filters applied during system degradation
- Admin interface category override functionality
- User preference persistence and application
- Background processing queue behavior
- Progressive retry mechanism validation

### Failure Simulation Tests
- AI service timeouts and errors
- Malformed AI responses
- Database connection failures during categorization
- High load scenarios with circuit breaker activation
- Network issues during categorization attempts

### Validation
- Manual review of initial categorizations for accuracy
- A/B testing of safety threshold values
- User feedback on category assignments
- Performance testing of categorized feed queries
- Fallback accuracy testing against manual classifications
- Recovery time measurement after system failures

## Archive-First Migration & Rollout

### Backward Compatibility with Archives
- **Existing Archives**: Parse without categorization metadata, apply safe defaults
- **Legacy Database Records**: Create missing archive files with default categorization
- **Archive Healing**: Background job to add categorization metadata to existing archives
- **Import Idempotency**: Categorization data import is fully idempotent like all archive data

### Archive-First Rollout Strategy
1. **Archive Format Validation**: Test enhanced archive format with existing import/export
2. **Staff Preview**: Deploy with categorization written to archives but hidden in UI
3. **Archive Healing**: Background process to categorize and update existing archives
4. **Database Population**: Import enhanced archives to populate categorization cache
5. **Soft Launch**: Enable UI features for subset of users with feedback collection
6. **Full Release**: Roll out to all users with announcement
7. **Monitoring**: Track category distribution, archive consistency, import performance

### Archive Consistency Validation
```python
def validate_archive_categorization_consistency():
    """Ensure archives and database categorization data match"""
    
    prayers_with_archives = session.exec(
        select(Prayer).where(Prayer.text_file_path.isnot(None))
    ).all()
    
    inconsistencies = []
    for prayer in prayers_with_archives:
        archive_data = parse_prayer_archive_with_categorization(prayer.text_file_path)
        
        # Compare archive vs database
        if prayer.safety_score != archive_data['safety_score']:
            inconsistencies.append({
                'prayer_id': prayer.id,
                'field': 'safety_score',
                'archive': archive_data['safety_score'],
                'database': prayer.safety_score
            })
    
    return inconsistencies
```

## Success Metrics

### Technical
- 95%+ of prayers successfully categorized
- < 100ms additional latency for prayer generation
- Zero safety false positives reported by users
- Feed query performance maintains current levels

### User Experience  
- Reduced reports of inappropriate content
- Increased engagement with category-filtered feeds
- Positive feedback on prayer organization features
- Growth in prayer partner matching success rate

## Archive-First Architecture Summary

This implementation plan has been **fully aligned with ThyWill's archive-first architecture**:

### Key Architectural Principles Maintained
1. **Text Files Written FIRST**: All categorization metadata written to archives before database
2. **Archives as Source of Truth**: Database fields serve as performance cache, archives are authoritative
3. **Human-Readable Format**: Categorization data stored in plain text format in archives
4. **Import Idempotency**: Categorization import fully idempotent like existing archive system
5. **Database Reconstruction**: Complete categorization data recoverable from text archives alone

### Critical Changes from Original Plan
- **Database Schema**: Changed from primary storage to cache layer populated from archives
- **Creation Flow**: Archive creation with categorization metadata happens BEFORE database insert
- **Import Integration**: Enhanced text importer to parse and populate categorization fields
- **Consistency Validation**: Tools to ensure archive and database categorization data alignment
- **Graceful Degradation**: Fallback strategies preserve archive-first workflow even during AI failures

### Archive Format Enhancement
```
Prayer 123 by John_Smith
Submitted January 15 2024 at 14:30
Project: healing
Audience: all
Safety Score: 0.95
Safety Flags: []
Category: health
Specificity: specific
Categorization Method: ai_full
Categorization Confidence: 0.88
```

This focused implementation plan provides atomic, testable phases while maintaining both the platform's core mission of supporting reverent, community-focused prayer **and full compatibility with the archive-first data philosophy that ensures long-term data durability and transparency**.