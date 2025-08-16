# Auto-Archive Date Development Plan

## Stage 1: Feature Flag and Environment Setup (<1 hour)
**Goal**: Add feature flag infrastructure for controlled rollout
**Dependencies**: None
**Changes**:
- Add `AUTO_ARCHIVE_DATE_ENABLED=false` to `.env.example`
- Update `CLAUDE.md` environment variables section
- Add feature flag checks in relevant service imports

**Testing**: Verify feature flag toggles functionality on/off
**Risks**: Low - standard feature flag pattern

## Stage 2: AI Prompt Enhancement (<2 hours)
**Goal**: Extend prayer generation AI to analyze temporal context
**Dependencies**: Stage 1 complete
**Changes**:
- Create new prompt file `prompts/auto_archive_analysis.txt`
- Update `PromptCompositionService` to include archive analysis when flag enabled
- Modify `generate_prayer()` to parse archive date suggestions from AI response

**Testing**: Test AI responses include archive date analysis, verify fallback behavior
**Risks**: Medium - AI response parsing reliability

## Stage 3: Database Schema Extension (<1 hour)
**Goal**: Add suggested archive date storage to Prayer model
**Dependencies**: Stage 2 complete
**Changes**:
- Add `suggested_archive_date: datetime | None` field to Prayer model
- Add `archive_suggestion_dismissed: bool` field to Prayer model  
- Create migration for new fields with safe defaults

**Testing**: Verify migration runs cleanly, fields populate correctly
**Risks**: Low - additive schema changes only

## Stage 4: Archive-First Service Integration (<1.5 hours)
**Goal**: Integrate archive date suggestions into prayer creation flow
**Dependencies**: Stages 1-3 complete
**Changes**:
- Update `create_prayer_with_text_archive()` to extract and store archive dates
- Add archive date metadata to text archive format
- Update archive healing to handle new metadata fields

**Testing**: Verify archive files contain archive dates, database sync works
**Risks**: Medium - text archive format changes

## Stage 5: UI Notifications and Controls (<2 hours)
**Goal**: Add author notifications and archive date management
**Dependencies**: Stages 1-4 complete
**Changes**:
- Add archive date display to prayer cards (author view only)
- Create archive prompt modal for approaching dates
- Add dismiss/postpone controls to prayer management interface
- Update prayer feeds to highlight approaching archive dates

**Testing**: Test notification timing, modal interactions, postpone functionality
**Risks**: Medium - HTMX modal integration complexity

## Stage 6: Background Processing Setup (<1 hour)
**Goal**: Add system to check for approaching archive dates
**Dependencies**: Stage 5 complete
**Changes**:
- Create `check_approaching_archive_dates()` utility function
- Add to existing system maintenance routines
- Configure notification timing (7 days, 1 day before)

**Testing**: Verify notification triggers work correctly, no performance impact
**Risks**: Low - follows existing maintenance patterns

## Database Schema Changes
**New Prayer fields**:
- `suggested_archive_date: datetime | None` - AI-suggested archive date
- `archive_suggestion_dismissed: bool` - User dismissed suggestion flag

## Function Signatures
```python
# Enhanced prayer generation
def generate_prayer(prompt: str) -> dict:
    # Returns: {'prayer': str, 'suggested_archive_date': datetime|None, ...}

# Archive date utilities  
def extract_archive_date_from_ai_response(ai_response: str) -> datetime | None:
def check_approaching_archive_dates(session: Session) -> list[Prayer]:
def dismiss_archive_suggestion(prayer_id: str, user_id: str, session: Session) -> bool:
def postpone_archive_suggestion(prayer_id: str, days: int, session: Session) -> bool:
```

## Testing Strategy
- Unit tests for AI response parsing
- Integration tests for archive-first flow with dates
- Functional tests for UI notification workflows
- Feature flag toggle testing at each stage

## Risk Assessment
**High**: AI prompt reliability for date extraction
**Medium**: Text archive format compatibility, UI complexity
**Low**: Database changes, feature flag implementation