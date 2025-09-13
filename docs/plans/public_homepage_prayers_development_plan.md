# Public Homepage Prayers - Development Plan

## Implementation Stages

### Stage 1: Public Prayer Data Service (<2 hours)
**Goal**: Create service to fetch eligible prayers for public display
**Dependencies**: None
**Changes**:
- Add `PublicPrayerService` class in `app_helpers/services/`
- Method `get_public_prayers(page, page_size)` - paginated query
- Method `get_public_prayer_by_id(prayer_id)` - individual prayer fetch
- Filter logic: exclude flagged=True, include archived prayers with praise reports
- Include user data with supporter badges for display

**Testing**: Unit tests for filtering logic, pagination, individual prayer retrieval
**Risks**: Low - pure data layer, no UI changes

### Stage 2: Public Routes and API (<2 hours)
**Goal**: Add FastAPI routes for public prayer access
**Dependencies**: Stage 1 (PublicPrayerService)
**Changes**:
- Add `/public/prayers` route - paginated prayer list (JSON)
- Add `/public/prayer/{prayer_id}` route - individual prayer (JSON)
- Rate limiting on public endpoints (10 requests/minute per IP)
- No authentication required, public access enabled

**Testing**: Integration tests for routes, rate limiting, JSON response format
**Risks**: Medium - new public endpoints require security review

### Stage 3: Public Homepage Template (<2 hours)
**Goal**: Create public homepage with prayer list display
**Dependencies**: Stage 2 (public routes)
**Changes**:
- New template `templates/public_homepage.html`
- Prayer card display with author, date, supporter badges
- Pagination controls (Previous/Next, page numbers)
- "Login" and "Request Access" buttons in header
- Responsive design matching existing UI patterns

**Testing**: Template rendering tests, mobile responsiveness check
**Risks**: Low - template changes only

### Stage 4: Individual Prayer Page Template (<2 hours)
**Goal**: Create dedicated pages for individual prayers
**Dependencies**: Stage 2 (public routes)
**Changes**:
- New template `templates/public_prayer.html`
- Full prayer display with generated prayer text
- Author attribution with supporter badges
- "Back to Prayers" navigation link
- SEO-friendly URL structure (`/prayer/{prayer_id}`)

**Testing**: Template rendering, navigation flow, mobile display
**Risks**: Low - isolated template functionality

### Stage 5: Main App Route Updates (<1 hour)
**Goal**: Route public traffic to new homepage, authenticated users to existing feeds
**Dependencies**: Stages 3-4 (templates)
**Changes**:
- Update main `/` route in `app.py`
- If not authenticated → render public homepage
- If authenticated → redirect to existing feed (`/feed` or dashboard)
- Preserve existing authentication system unchanged

**Testing**: Route behavior for authenticated vs anonymous users
**Risks**: Medium - changes core routing logic

### Stage 6: Public Homepage Integration Testing (<1 hour)
**Goal**: End-to-end testing of complete public homepage flow
**Dependencies**: All previous stages
**Changes**:
- Integration tests covering full user flows
- Performance testing with realistic prayer data
- Cross-browser compatibility check
- Security audit of public endpoints

**Testing**: Full flow testing, performance benchmarks, security review
**Risks**: Low - testing and validation only

## Database Schema
**No database changes required** - using existing Prayer model fields:
- `flagged` field for content filtering
- `archived` field for praise report inclusion
- `user_id` for author attribution
- `created_at` for chronological ordering

## Function Signatures

```python
class PublicPrayerService:
    def get_public_prayers(page: int = 1, page_size: int = 20) -> Dict[str, Any]
    def get_public_prayer_by_id(prayer_id: int) -> Optional[Prayer]
    def _is_prayer_public_eligible(prayer: Prayer) -> bool

# New FastAPI routes
@app.get("/public/prayers")
async def get_public_prayers_api(page: int = 1, page_size: int = 20)

@app.get("/public/prayer/{prayer_id}")
async def get_public_prayer_api(prayer_id: int)

@app.get("/prayer/{prayer_id}")
async def public_prayer_page(prayer_id: int)
```

## Testing Strategy
**Unit Tests**:
- PublicPrayerService filtering and pagination logic
- Prayer eligibility rules (flagged exclusion, praise report inclusion)

**Integration Tests**:
- Public API endpoints with various prayer data scenarios
- Rate limiting functionality
- Authentication routing (public vs authenticated users)

**Functional Tests**:
- Complete user flows from homepage to individual prayers
- Pagination navigation and edge cases
- Mobile responsiveness and cross-browser compatibility

## Risk Assessment

**High Risk**:
- **Route changes to main `/`**: Could break existing user experience
  - *Mitigation*: Thorough testing, gradual rollout, easy rollback plan

**Medium Risk**:
- **Public API security**: New endpoints without authentication
  - *Mitigation*: Rate limiting, input validation, security audit
- **Performance impact**: Public traffic on prayer queries
  - *Mitigation*: Database indexing, query optimization, caching consideration

**Low Risk**:
- **Template rendering**: Isolated UI changes
  - *Mitigation*: Template validation, responsive design testing

## Dependencies
- Existing Prayer model with `flagged`, `archived` fields
- Current supporter badge system (`UsernameDisplayService`)
- Existing pagination patterns from authenticated feeds
- FastAPI rate limiting middleware
- Mobile-responsive CSS framework from existing templates

## Success Criteria
- Public homepage loads in <3 seconds
- All eligible prayers accessible through pagination
- Individual prayer pages load correctly
- Rate limiting prevents abuse (10 req/min per IP)
- No flagged prayers appear on public pages
- Existing authenticated user experience unchanged
- Mobile-responsive design matches existing UI patterns

## Rollback Plan
- Feature flag for public homepage (if needed for gradual rollout)
- Main route easily reverts to authentication requirement
- Public endpoints can be disabled without affecting authenticated users
- Database unchanged - no migration rollback required