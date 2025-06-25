# AI Prayer Preview Feature Implementation Plan

## Overview
Allow users to preview the AI-generated prayer before submitting their prayer request to the community queue, giving them control over the final prayer content.

## Current State Analysis
- **Current Flow**: User submits request → AI generates prayer server-side → Prayer immediately published to community
- **Gap**: No preview/confirmation step - users cannot see or modify the AI-generated prayer before publication
- **Location**: Prayer form in `/templates/components/prayer_form.html`, submission via `/prayers` POST endpoint

## Proposed User Experience Flow

### 1. Form Submission → Preview Step
```
[Current] User fills form → Submits → Prayer published
[Proposed] User fills form → Preview → Approve/Edit → Submit → Prayer published
```

### 2. Preview Screen UI Components
- **Preview Section**: Display AI-generated prayer prominently
- **Original Request**: Show user's original text (collapsible)
- **Action Buttons**: 
  - "Submit Prayer" (confirm and publish)
  - "Regenerate Prayer" (create new AI version)
  - "Edit Request" (return to form)
  - "Cancel" (abandon submission)

## Technical Implementation

### 1. New API Endpoint
```python
# New route in prayer_routes.py
@router.post("/prayers/preview")
async def preview_prayer(request: PrayerPreviewRequest):
    """Generate prayer preview without saving to database"""
    # Validate input
    # Generate AI prayer using existing generate_prayer() function
    # Return preview data (generated prayer + original request)
```

### 2. Frontend Modifications

**Prayer Form Updates** (`templates/components/prayer_form.html`):
- Change form action from direct submission to preview endpoint
- Add preview container section (initially hidden)
- Update JavaScript to handle preview flow

**Preview Interface**:
```html
<!-- New preview section -->
<div id="prayer-preview" class="hidden">
  <div class="preview-header">
    <h3>Prayer Preview</h3>
    <p>Review how your request will appear to the community</p>
  </div>
  
  <div class="generated-prayer">
    <h4>Generated Prayer</h4>
    <div id="preview-prayer-text"></div>
  </div>
  
  <div class="original-request collapsible">
    <h4>Your Original Request</h4>
    <div id="preview-original-text"></div>
  </div>
  
  <div class="preview-actions">
    <button id="submit-final">Submit Prayer</button>
    <button id="regenerate">Generate Different Prayer</button>
    <button id="edit-request">Edit Request</button>
    <button id="cancel-preview">Cancel</button>
  </div>
</div>
```

### 3. JavaScript Flow Enhancement
```javascript
// Updated form submission flow
async function handlePrayerSubmission(formData) {
  // Step 1: Get preview
  const preview = await fetchPrayerPreview(formData);
  
  // Step 2: Show preview interface
  showPreviewSection(preview);
  
  // Step 3: Handle user actions
  setupPreviewActions(formData, preview);
}

function setupPreviewActions(originalFormData, preview) {
  // Submit final prayer
  document.getElementById('submit-final').onclick = () => {
    submitFinalPrayer(originalFormData, preview.generated_prayer);
  };
  
  // Regenerate prayer
  document.getElementById('regenerate').onclick = () => {
    regeneratePrayer(originalFormData);
  };
  
  // Edit original request
  document.getElementById('edit-request').onclick = () => {
    returnToForm(originalFormData);
  };
}
```

### 4. Backend Service Updates

**New Preview Service** (`app_helpers/services/prayer_helpers.py`):
```python
def generate_prayer_preview(text: str, tag: str = None, target_audience: str = "all"):
    """Generate prayer preview without database storage"""
    generated_prayer = generate_prayer(text, target_audience)
    
    return {
        "original_text": text,
        "generated_prayer": generated_prayer,
        "tag": tag,
        "target_audience": target_audience,
        "preview_id": generate_preview_token()  # For security
    }

def submit_previewed_prayer(preview_data: dict, user_id: int):
    """Submit prayer using preview data"""
    # Validate preview token
    # Create prayer record using preview data
    # Continue with existing submission flow
```

### 5. Security Considerations
- **Preview Tokens**: Generate temporary tokens to prevent replay attacks
- **Session Validation**: Ensure preview belongs to current user
- **Rate Limiting**: Prevent abuse of preview generation
- **Content Validation**: Re-validate content on final submission

## Implementation Phases

### Phase 1: Basic Preview (2-3 hours)
- Add preview endpoint
- Create preview UI components
- Implement basic preview → submit flow
- Update form JavaScript

### Phase 2: Enhanced Actions (1-2 hours)
- Add "Regenerate Prayer" functionality
- Implement "Edit Request" return flow
- Add loading states and error handling

### Phase 3: Polish & Testing (1-2 hours)
- Improve UI/UX styling
- Add smooth transitions
- Test edge cases and error scenarios
- Performance optimization

## Benefits
- **User Control**: Users can review AI-generated content before publication
- **Quality Assurance**: Opportunity to catch inappropriate or unclear prayers
- **User Confidence**: Builds trust by showing exactly what will be shared
- **Flexibility**: Allow multiple generation attempts for better results

## Considerations
- **Additional API Call**: Slightly increases server load (preview + submit)
- **User Experience**: Adds one extra step to submission process
- **Caching**: Consider caching generated prayers briefly for regeneration