# Foundational Prayers Implementation Plan

## Overview
Add foundational prayers that are embedded in the source code and loaded into memory during page execution, integrating seamlessly with ThyWill's existing prayer system.

## Current System Analysis
- **Archive-first architecture**: Text files written first, then database records
- **AI-generated prayers**: Uses Anthropic Claude for prayer generation
- **Religious preference filtering**: "all" vs "christians_only" audiences
- **Flexible attribute system**: Dynamic prayer attributes
- **No existing foundational prayers**: System only handles user-generated content

## Implementation Strategy

### 1. Foundational Prayers Data Structure
- **Location**: `app_helpers/foundational_prayers.py`
- **Format**: Python constants with structured prayer data
- **Content**: Core prayers for various spiritual needs and occasions
- **Metadata**: Include author, audience, category, and spiritual purpose

### 2. Prayer Categories
```python
FOUNDATIONAL_PRAYERS = {
    "protection": [...],
    "guidance": [...],
    "healing": [...],
    "gratitude": [...],
    "community": [...],
    "wisdom": [...],
    "strength": [...],
    "peace": [...]
}
```

### 3. Integration Points

#### A. Application Startup (`app.py`)
- Load foundational prayers into memory during FastAPI startup
- Create in-memory cache for quick access
- Ensure prayers are available before first request

#### B. Database Integration
- Add `is_foundational: bool` field to Prayer model
- Foundational prayers get special handling (cannot be deleted/archived by users)
- Maintain archive-first pattern for consistency

#### C. Archive System Integration
- Pre-populate text archives with foundational prayers
- Use special naming convention: `foundational_[category]_[id].txt`
- Store in dedicated foundational prayers archive directory

#### D. Feed System Enhancement
- Add "Foundational Prayers" feed type
- Include foundational prayers in appropriate existing feeds
- Respect religious preference filtering

### 4. Loading Mechanism

#### Option A: Startup Loading (Recommended)
```python
@app.on_event("startup")
async def load_foundational_prayers():
    # Load prayers from source code constants
    # Create archive files if they don't exist
    # Insert database records if they don't exist
    # Cache prayers in memory for quick access
```

#### Option B: CLI Command
```bash
thywill import foundational-prayers
```

#### Option C: Lazy Loading
- Load prayers on first access
- Cache subsequent requests

### 5. Prayer Content Strategy

#### Universal Prayers ("all" audience)
- Interfaith-friendly language
- Focus on universal human needs
- Avoid denomination-specific terminology

#### Christian Prayers ("christians_only" audience)
- Biblical references appropriate
- Christ-centered language
- Christian theological concepts

### 6. File Structure
```
app_helpers/
├── foundational_prayers.py          # Prayer constants and data
├── services/
│   ├── foundational_prayer_service.py  # Loading/management logic
│   └── prayer_helpers.py            # Existing prayer services
└── routes/
    └── prayer/
        └── foundational_routes.py    # API endpoints for foundational prayers
```

### 7. Archive Structure
```
text_archives/
├── prayers/                          # Existing user prayers
└── foundational/                     # New foundational prayers directory
    ├── protection/
    ├── guidance/
    ├── healing/
    └── ...
```

### 8. API Enhancements

#### New Endpoints
- `GET /api/prayers/foundational` - List all foundational prayers
- `GET /api/prayers/foundational/{category}` - Get prayers by category
- `GET /api/prayers/foundational/{id}` - Get specific foundational prayer

#### Existing Endpoint Modifications
- Update feed endpoints to include foundational prayers
- Modify prayer detail endpoints to handle foundational prayer metadata

### 9. Database Schema Updates

#### Prayer Model Enhancement
```python
class Prayer(SQLModel, table=True):
    # ... existing fields ...
    is_foundational: bool = False
    foundational_category: str | None = None
    spiritual_purpose: str | None = None
```

#### Migration Required
- Add new fields to existing Prayer table
- Populate foundational prayers on first run

### 10. Memory Management
- Cache foundational prayers in application memory
- Implement refresh mechanism for development
- Consider Redis caching for production scaling

### 11. Testing Strategy
- Unit tests for foundational prayer loading
- Integration tests for API endpoints
- Test religious preference filtering
- Verify archive-first consistency

### 12. Content Curation
- Research traditional prayers from various traditions
- Write original prayers for modern spiritual needs
- Ensure theological appropriateness
- Review with spiritual advisors if available

## Implementation Phases

### Phase 1: Foundation (Core Infrastructure)
1. Create `foundational_prayers.py` with initial prayer constants
2. Implement `foundational_prayer_service.py` loading logic
3. Add database schema changes and migration
4. Implement startup loading mechanism

### Phase 2: Integration (System Integration)
1. Update feed system to include foundational prayers
2. Create foundational prayer API endpoints
3. Implement archive system integration
4. Add memory caching system

### Phase 3: Content & Testing (Content & Quality)
1. Populate comprehensive foundational prayer content
2. Implement thorough testing suite
3. Add CLI commands for management
4. Performance optimization and monitoring

## Technical Considerations

### Performance
- In-memory caching for frequently accessed prayers
- Lazy loading for less common categories
- Database indexing on foundational prayer fields

### Security
- Foundational prayers should be read-only to users
- Admin-only modification capabilities
- Audit logging for foundational prayer changes

### Scalability
- Consider external configuration for large prayer libraries
- Implement prayer versioning system
- Support for multiple languages/translations

### Maintenance
- Clear documentation for adding new foundational prayers
- Validation system for prayer content format
- Automated backup of foundational prayer content

## Benefits

1. **Spiritual Depth**: Provides users with time-tested, meaningful prayers
2. **Community Building**: Shared foundational prayers unite the community
3. **User Guidance**: Helps users learn different prayer styles and approaches
4. **System Bootstrap**: Ensures new deployments have meaningful content immediately
5. **Educational Value**: Exposes users to diverse spiritual traditions and practices

## Risks & Mitigation

### Risk: Theological Disputes
- **Mitigation**: Careful content curation, multiple tradition representation

### Risk: Performance Impact
- **Mitigation**: Efficient caching, lazy loading, performance monitoring

### Risk: Maintenance Overhead
- **Mitigation**: Clear documentation, automated testing, simple content management

### Risk: User Confusion
- **Mitigation**: Clear UI distinction between user and foundational prayers

## Success Metrics

- Foundational prayers successfully load on application startup
- Users can access foundational prayers through existing UI
- Archive-first consistency maintained
- No performance degradation
- User engagement with foundational prayer content
- System stability and reliability maintained