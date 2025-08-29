# Admin Statistics Dashboard - Development Plan

## Stage 1: Statistics Service Foundation (<2 hours)
**Goal**: Create core statistics calculation service
**Dependencies**: None
**Changes**:
- Create `app_helpers/statistics_service.py` with basic prayer counting functions
- Add functions: `get_prayer_counts_by_period()`, `get_total_prayers()`, `get_active_prayers_count()`
- Database queries using SQLModel with date grouping
**Testing**: Unit tests for date range calculations and count accuracy
**Risks**: Query performance with large datasets

## Stage 2: Statistics API Endpoints (<1.5 hours)
**Goal**: Add REST endpoints for statistics data
**Dependencies**: Stage 1
**Changes**:
- Add `/api/statistics/prayers` endpoint in `app_helpers/routes/admin_routes.py`
- Support query parameters: `period` (daily/weekly/monthly/yearly), `start_date`, `end_date`
- JSON response format with time series data
- Admin authentication required
**Testing**: API endpoint tests with different time periods
**Risks**: None

## Stage 3: Statistics Dashboard UI (<2 hours)
**Goal**: Create statistics dashboard page
**Dependencies**: Stage 2
**Changes**:
- Create `templates/admin/statistics.html` template
- Add statistics navigation link to admin panel
- Simple table display of prayer counts by time period
- Time period selector (dropdown)
**Testing**: Manual UI testing, template validation
**Risks**: Date handling edge cases

## Stage 4: Chart Visualization Integration (<1.5 hours)
**Goal**: Add interactive charts using Chart.js
**Dependencies**: Stage 3
**Changes**:
- Add Chart.js CDN to statistics template
- JavaScript to fetch API data and render line/bar charts
- Chart updates when time period changes
**Testing**: Chart rendering with sample data, responsive behavior
**Risks**: JavaScript compatibility, chart library loading

## Database Changes
**Conceptual**: No new tables required - uses existing Prayer model with date-based grouping queries

## Function Signatures
```python
# statistics_service.py
def get_prayer_counts_by_period(period: str, start_date: date, end_date: date) -> Dict[str, int]
def get_total_prayers() -> int
def get_active_prayers_count() -> int

# admin_routes.py  
@router.get("/api/statistics/prayers")
async def get_prayer_statistics(period: str, start_date: str, end_date: str, current_user: User = Depends(require_admin))
```

## Testing Strategy
- Unit tests for statistics calculations
- API endpoint integration tests
- Manual UI testing for chart functionality
- Performance testing with >1000 prayer records

## Risk Assessment
- **Low Risk**: Basic counting queries, simple UI
- **Medium Risk**: Chart.js integration, date handling
- **Mitigation**: Use proven Chart.js patterns, comprehensive date validation