# Historical Prayer Examples Development Plan (MVP)

## Overview
Implement a simple prayer catalog feature based on the existing inspire/ directory. This will create a browsable collection of famous Christian prayers to showcase on the platform.

## Current State Analysis
- **Existing Content**: 11 prayer files in inspire/ directory with historical prayers from various Christian traditions
- **Content Quality**: Authenticated historical prayers including St. Francis, Martin Luther, Thomas Merton, and others
- **Format**: Simple text files with prayer content only
- **Missing**: Database integration, metadata, web interface

## Development Phases

### Phase 1: Database Schema & Data Model (1 day)
**Goal**: Create simple data structure for historical prayers

**Tasks**:
- Create `HistoricalPrayer` model in models.py with fields:
  - id, title, author, period, prayer_text, created_at, updated_at
- Add database migration for new table

**Files to modify**:
- `models.py` - Add HistoricalPrayer model
- `alembic/` - Create migration script

### Phase 2: Text-Archives Integration (1 day)
**Goal**: Integrate historical prayers into existing text-archives import process

**Tasks**:
- Modify text-archives import to process inspire/ directory
- Create structured data format for historical prayers
- Ensure import process is idempotent and safe

**Files to modify**:
- `app_helpers/text_archives.py` - Add historical prayer import
- `inspire/` - Convert to structured format if needed

### Phase 3: Backend API & Services (1 day)
**Goal**: Create basic backend services for prayer catalog

**Tasks**:
- Create `HistoricalPrayerService` class with methods:
  - `get_all_prayers()` - List all prayers
  - `get_prayer_by_id(id)` - Individual prayer retrieval
  - `search_prayers(query)` - Basic search
- Add API routes in `app_helpers/routes/historical_prayers.py`:
  - `GET /api/historical-prayers` - List all prayers
  - `GET /api/historical-prayers/{id}` - Individual prayer

**Files to create**:
- `app_helpers/services/historical_prayer_service.py`
- `app_helpers/routes/historical_prayers.py`

### Phase 4: Frontend Templates & UI (2 days)
**Goal**: Create simple, responsive user interface

**Tasks**:
- Create template structure:
  - `templates/historical_prayers/index.html` - Main catalog page
  - `templates/historical_prayers/prayer_detail.html` - Individual prayer view
- Add navigation menu item
- Create responsive design with good typography
- Add basic search functionality

**Files to create**:
- `templates/historical_prayers/` - Template directory
- `static/css/historical_prayers.css` - Basic styling

## Technical Implementation Details

### Database Schema
```sql
CREATE TABLE historical_prayers (
    id INTEGER PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    period VARCHAR(100),
    prayer_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### URL Structure
- `/inspire` - Main historical prayers catalog page
- `/inspire/{id}` - Individual prayer detail
- `/api/historical-prayers` - API endpoints

### Integration Points
- **Navigation**: Main menu item "Inspire"
- **Text Archives**: Historical prayers imported via text-archives process

## Success Metrics
- User engagement with historical prayer section (time spent, pages viewed)
- Basic usage analytics

## Testing Strategy
- Unit tests for service methods
- Integration tests for API endpoints
- Basic functional tests for user workflows

## Timeline Summary
- **Total Development Time**: 5 days
- **Phase 1**: Database model (1 day)
- **Phase 2**: Text-archives integration (1 day)
- **Phase 3**: Backend API (1 day)
- **Phase 4**: Frontend UI (2 days)

This streamlined MVP plan focuses on creating a simple, functional prayer catalog that leverages the existing inspire/ directory content and integrates with the platform's existing text-archives import system.