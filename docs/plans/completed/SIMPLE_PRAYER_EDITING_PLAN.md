# Simple Prayer Editing Implementation Plan

**Status**: ✅ COMPLETED  
**Completed**: 2025-06-25  
**Implementation Commit**: 3208ed3  
**Verification**: All requirements implemented and tested  

## Overview
Allow users to edit the AI-generated prayer text **before submitting** their prayer request. This provides immediate editing capability during the prayer creation flow without complex post-submission editing features.

## Current Prayer Flow
1. User enters prayer request text
2. AI generates prayer automatically
3. User submits (prayer is saved to database)

## New Prayer Flow
1. User enters prayer request text  
2. AI generates prayer automatically
3. **NEW**: User can edit the generated prayer text
4. User submits final prayer (original or edited version)

## Implementation Changes

### 1. Frontend Updates

#### Prayer Creation Form (`templates/submit_prayer.html` or similar)
- Add textarea for editing generated prayer
- Show generated prayer immediately after AI generation
- Allow user to modify text before final submission
- Add character count validation (match existing limits)

#### HTMX Integration
```html
<!-- After AI generates prayer, show editable version -->
<div id="generated-prayer-section" style="display: none;">
    <h4>Generated Prayer</h4>
    <textarea id="generated-prayer-text" 
              name="final_prayer_text"
              class="form-control" 
              rows="4" 
              maxlength="2000"
              hx-on:input="updateCharCount(this)">
    </textarea>
    <div class="form-text">
        <span class="char-count">0/2000 characters</span>
        <small class="text-muted">You can edit this prayer before submitting</small>
    </div>
</div>
```

### 2. Backend Updates

#### Prayer Generation Route (in `app.py`)
Update existing prayer generation to return editable prayer text instead of immediately saving:

```python
@app.post("/generate-prayer")
async def generate_prayer_for_editing(request: Request, prayer_request: str = Form(...)):
    """Generate prayer for user editing before submission"""
    # Generate prayer using existing Claude integration
    generated_prayer = await generate_prayer(prayer_request)
    
    # Return prayer text for editing (don't save yet)
    return {"generated_prayer": generated_prayer}
```

#### Prayer Submission Route
Modify existing prayer submission to accept the final prayer text:

```python
@app.post("/prayers")
async def submit_prayer(
    request: Request, 
    prayer_request: str = Form(...),
    final_prayer_text: str = Form(...),  # NEW: final prayer text
    user_session=Depends(require_full_auth)
):
    """Submit final prayer (original or user-edited)"""
    # Use final_prayer_text instead of regenerating
    # Save to database with existing archive-first approach
```

### 3. JavaScript Updates

Add client-side functionality for prayer editing:

```javascript
// Character count for prayer editing
function updateCharCount(textarea) {
    const count = textarea.value.length;
    const maxCount = textarea.getAttribute('maxlength');
    const counter = textarea.closest('.form-group').querySelector('.char-count');
    counter.textContent = `${count}/${maxCount} characters`;
}

// Show generated prayer section after AI generation
function showGeneratedPrayer(prayerText) {
    document.getElementById('generated-prayer-text').value = prayerText;
    document.getElementById('generated-prayer-section').style.display = 'block';
    updateCharCount(document.getElementById('generated-prayer-text'));
}
```

## User Experience Flow

### Step 1: Request Entry
- User types prayer request in existing form
- Submit triggers AI generation (existing functionality)

### Step 2: Prayer Review & Edit
- Generated prayer appears in editable textarea
- User can:
  - Keep generated prayer as-is
  - Edit the text to personalize it
  - See character count in real-time

### Step 3: Final Submission  
- User clicks final submit button
- Prayer is saved with final text (original or edited)
- Continues to existing prayer feed

## Technical Requirements

### No Database Changes
- No new fields needed in Prayer model
- No migration required
- Uses existing `generated_prayer` field for final text

### Minimal Code Changes
- Update prayer creation form template
- Modify prayer generation/submission flow
- Add basic JavaScript for editing interface

### Backward Compatibility
- No impact on existing prayers
- No changes to prayer viewing/marking functionality
- Maintains archive-first philosophy

## Implementation Steps

### Phase 1: Frontend Updates (1 day)
1. Update prayer submission template with editing interface
2. Add JavaScript for character counting and form management
3. Test prayer generation and editing flow

### Phase 2: Backend Updates (1 day)  
1. Modify prayer generation endpoint to return editable text
2. Update prayer submission to accept final prayer text
3. Test end-to-end prayer creation flow

### Phase 3: Testing & Polish (0.5 day)
1. Test prayer creation with and without editing
2. Verify character limits and validation
3. Ensure mobile-responsive design

## Configuration
No new environment variables needed. Uses existing:
- `ANTHROPIC_API_KEY` for prayer generation
- Existing form validation and limits

## Benefits of This Approach
- **Simple**: No complex editing features or database changes
- **Immediate**: Users can edit during creation flow
- **Non-Breaking**: Zero impact on existing functionality  
- **Fast Implementation**: Can be completed in 2-3 days
- **User-Friendly**: Natural workflow for prayer personalization