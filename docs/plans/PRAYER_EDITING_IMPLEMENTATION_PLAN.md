# Prayer Editing Implementation Plan

## Overview
Allow users to edit AI-generated prayers after they are created, providing flexibility to personalize the generated content while maintaining the community prayer experience.

## Database Changes

### 1. Prayer Model Updates
- Add `is_edited` boolean field to Prayer model (default: False)
- Add `original_generated_prayer` text field to store the original AI-generated version
- Add `edited_at` timestamp field for tracking when edits occur
- Add `edit_count` integer field to track number of edits (optional, for analytics)

```python
# In models.py - Prayer class around line 80
class Prayer(SQLModel, table=True):
    # ... existing fields ...
    is_edited: bool = Field(default=False)
    original_generated_prayer: str | None = Field(default=None)
    edited_at: datetime | None = Field(default=None)
    edit_count: int = Field(default=0)
```

### 2. Archive-First Integration
Since ThyWill uses an archive-first philosophy, prayer edits must integrate with the text archive system:
- Edits should append to existing text archive files
- Original prayer content should be preserved in archives
- Edit history should be maintained in human-readable format
- Use `ArchiveFirstService` for consistent data flow

## Frontend Changes

### 2. Prayer Display Updates
- Add visual indicator for edited prayers (e.g., small "edited" badge)
- Modify prayer card template (`templates/components/prayer_card.html`) to show edit status
- Add tooltip or expandable section to show original prayer if desired
- Follow existing UI patterns and CSS class conventions
- Ensure mobile-responsive design

### 3. Edit Interface
- Add "Edit Prayer" button/link on prayer cards (only for prayer author)
- Create inline editing form following existing form patterns
- Include save/cancel buttons with proper HTMX integration
- Add character limit validation (match original prayer creation limits)
- Use existing CSS classes and form styling
- Implement proper loading states and error handling

### 4. HTMX Implementation
Follow existing HTMX patterns used throughout the codebase:

```html
<!-- Edit button in prayer card -->
<button hx-get="/prayer/{{ prayer.id }}/edit" 
        hx-target="#prayer-{{ prayer.id }}-content"
        hx-swap="outerHTML"
        class="btn btn-sm btn-outline-secondary"
        {% if not can_edit %}disabled{% endif %}>
    ✏️ Edit Prayer
</button>

<!-- Edit form template -->
<div id="prayer-edit-form-{{ prayer.id }}" class="prayer-edit-form">
    <form hx-post="/prayer/{{ prayer.id }}/edit"
          hx-target="#prayer-{{ prayer.id }}-content"
          hx-swap="outerHTML">
        <textarea name="edited_prayer" 
                  class="form-control"
                  rows="4"
                  maxlength="2000"
                  hx-on:input="updateCharCount(this)">{{ prayer.generated_prayer }}</textarea>
        <div class="edit-controls">
            <span class="char-count">0/2000</span>
            <button type="submit" class="btn btn-primary btn-sm">Save Changes</button>
            <button type="button" class="btn btn-secondary btn-sm" 
                    hx-get="/prayer/{{ prayer.id }}/cancel-edit"
                    hx-target="#prayer-{{ prayer.id }}-content"
                    hx-swap="outerHTML">Cancel</button>
        </div>
    </form>
</div>
```

**HTMX Integration Points:**
- Inline editing using `hx-target` and `hx-swap`
- Real-time character count with `hx-on:input`
- Form submission with proper error handling
- Cancel functionality that restores original view

## Backend Implementation

### 5. New Routes
Based on the modular route structure, add to the appropriate prayer sub-module:

```python
# In app_helpers/routes/prayer/prayer_operations.py (or new prayer_editing.py)
from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from app_helpers.services.auth_helpers import current_user, require_full_auth
from app_helpers.services.archive_first_service import update_prayer_with_archive

router = APIRouter()

@router.get("/prayer/{prayer_id}/edit")
async def get_prayer_edit_form(prayer_id: str, request: Request, user_session=Depends(require_full_auth)):
    """Get prayer edit form (HTMX endpoint)"""

@router.post("/prayer/{prayer_id}/edit")
async def update_prayer(prayer_id: str, request: Request, edited_prayer: str = Form(...), user_session=Depends(require_full_auth)):
    """Update prayer text with archive-first approach"""

@router.get("/prayer/{prayer_id}/original")
async def view_original_prayer(prayer_id: str, request: Request, user_session=Depends(require_full_auth)):
    """View original AI-generated prayer"""
```

Note: Prayer IDs are strings (UUIDs) in this codebase, not integers.

### 6. Business Logic
Create a new service module for prayer editing logic:

```python
# In app_helpers/services/prayer_editing_service.py
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlmodel import Session, select
from models import Prayer, User
from app_helpers.services.archive_first_service import update_prayer_with_archive

def can_edit_prayer(prayer: Prayer, user_id: str, session: Session) -> Tuple[bool, Optional[str]]:
    """Check if user can edit this prayer with reason if not"""
    
def edit_prayer_text(prayer_id: str, new_text: str, user_id: str, session: Session) -> Prayer:
    """Edit prayer using archive-first approach"""
    
def get_prayer_edit_metadata(prayer: Prayer) -> dict:
    """Get metadata about prayer editing status"""
```

**Key Logic Requirements:**
- Validate user permissions (only prayer author can edit)
- Implement edit time limits (configurable, default 24-48 hours)
- Store original prayer before first edit using `original_generated_prayer` field
- Update prayer text and metadata
- Log edit activity using existing audit trail systems
- Integrate with text archive system via `ArchiveFirstService`

### 7. Security & Validation
- Ensure only prayer author can edit their prayers
- Validate edited content (length, appropriate content)
- Rate limiting for edits to prevent abuse
- Maintain edit history for moderation purposes

## User Experience Considerations

### 8. Edit Restrictions
- Time-based editing window (configurable, default 24-48 hours)
- Edit count limits to prevent excessive modifications
- Admin override capability for moderation purposes
- Clear messaging about edit limitations

### 9. Community Transparency
- Visual indicators for edited prayers
- Option to view original AI-generated version
- Edit timestamp display
- Consideration for prayer marks on edited vs original prayers

## Technical Implementation Steps

### Phase 1: Database & Models (1-2 days)
1. Update Prayer model in `models.py` with new fields
2. Create database migration using ThyWill's migration system
3. Update existing queries in prayer services to handle new fields
4. Test migration with backup/restore functionality

### Phase 2: Archive Integration (1-2 days)
1. Extend `ArchiveFirstService` to handle prayer edits
2. Implement edit history in text archive format
3. Ensure edit operations maintain archive-first data flow
4. Test archive integrity with edits

### Phase 3: Backend Logic (2-3 days)
1. Create `prayer_editing_service.py` in `app_helpers/services/`
2. Add permission validation using existing auth patterns
3. Create new routes in `app_helpers/routes/prayer/` structure
4. Integrate with existing audit logging systems
5. Add rate limiting for edit operations

### Phase 4: Frontend Interface (2-3 days)
1. Add edit buttons to prayer card templates (`templates/components/prayer_card.html`)
2. Create edit form templates following existing UI patterns
3. Implement HTMX interactions using established patterns
4. Add visual indicators for edited prayers
5. Update CSS in existing stylesheets

### Phase 5: Testing & Validation (1-2 days)
1. Unit tests in `tests/unit/` following existing test structure
2. Integration tests in `tests/integration/` for edit workflows
3. CLI tests in `tests/cli/` if needed
4. Security testing for permission validation
5. Test archive integrity with edits

## Configuration Options

### Environment Variables
```bash
PRAYER_EDIT_ENABLED=true                    # Enable/disable prayer editing
PRAYER_EDIT_TIME_LIMIT_HOURS=24            # Hours after creation editing is allowed
PRAYER_EDIT_COUNT_LIMIT=3                  # Maximum number of edits per prayer
SHOW_ORIGINAL_PRAYER_LINK=true             # Allow viewing original AI version
```

## Migration Strategy

### Database Migration
- Use ThyWill's existing migration system (`./thywill migrate`)
- Add new fields with proper defaults to avoid breaking existing data
- Ensure backward compatibility with existing prayer queries
- Test migration with database backup/restore workflow

### Feature Rollout
- Feature flag via environment variable (`PRAYER_EDIT_ENABLED=true`)
- Graceful degradation when feature is disabled
- Existing prayers remain unchanged unless edited
- No impact on current prayer viewing/marking functionality
- Optional retroactive application to recent prayers

### Archive Compatibility
- Existing text archives remain valid and readable
- New edit history appends to existing archive files
- Archive-first philosophy maintained throughout
- No breaking changes to existing archive structure

## Future Enhancements
- Edit history tracking with full version control
- Collaborative editing for group prayers
- Admin moderation of edited content
- Analytics on editing patterns and usage