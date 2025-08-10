# Prayer Text File Linking - Development Plan

## Stage 1: Create File System URL Route (<1.5 hours)
**Goal**: Create new route that serves files with file system-like URL structure

**Dependencies**: None

**Changes**:
- Add new route `/files/prayers/{year}/{month}/{filename}.txt` to serve archive files
- Create helper function to map prayer IDs to actual file system paths using `prayer.text_file_path`
- Use existing authentication and file reading logic from current `/api/archive/prayer/{prayer_id}/file`
- Return files as `text/plain` with proper encoding and filename headers

**Testing**:
- Test URL format matches file system structure: `/files/prayers/2025/08/2025_08_10_prayer_at_1234.txt`
- Verify authentication requirements (logged in users only)
- Test file serving with proper MIME type and headers
- Test 404 handling for non-existent files
- Test permission checks (users can access any community prayer file)

**Risks**: Medium - new route with file system mapping logic

---

## Stage 2: Add Helper Function to Generate File URLs (<1 hour)
**Goal**: Create utility to convert prayer objects to file system URLs

**Dependencies**: Stage 1 completed

**Changes**:
- Add template filter or helper function `prayer_file_url(prayer)` 
- Extract date components and filename from `prayer.text_file_path`
- Generate `/files/prayers/{year}/{month}/{filename}.txt` URL format
- Handle edge cases where `text_file_path` is None or malformed

**Function signature**:
```python
def prayer_file_url(prayer: Prayer) -> Optional[str]:
    """Convert prayer to file system URL or None if no archive file"""
```

**Testing**:
- Test with various `text_file_path` formats from database
- Test with None/empty `text_file_path`
- Verify URL generation matches actual file locations
- Test URL compatibility with browser address bar

**Risks**: Low - utility function with clear inputs/outputs

---

## Stage 3: Add Text File Link to Prayer Marks Template (<1 hour)
**Goal**: Add "View Text File" link to existing prayer detail page using new URL structure

**Dependencies**: Stages 1-2 completed

**Changes**:
- Modify `templates/prayer_marks.html` to add text file link using new URL format
- Add conditional display based on `TEXT_ARCHIVE_ENABLED` and file URL availability
- Include link styling consistent with existing UI (purple theme)  
- Position link in prayer details section with clear labeling

**Testing**:
- Verify link appears when text archives enabled and text file exists
- Verify link hidden when `TEXT_ARCHIVE_ENABLED=false`
- Verify link hidden when prayer has no archive file
- Click test to confirm correct file opens in browser
- Test link format displays clean URL with .txt extension

**Risks**: Low - template changes using established URL pattern

---

## Stage 4: Add Template Context and Update Existing Link (<1 hour)
**Goal**: Ensure template has all necessary context variables and optionally update existing download link

**Dependencies**: Stages 1-3 completed

**Changes**:
- Verify `prayer_marks` route passes `TEXT_ARCHIVE_ENABLED` to template context
- Add prayer file URL helper to template filters
- **Decision Point**: Keep existing download link in prayer cards OR replace with new file system URL
- If replacing: Update prayer card template to use new URL format for "Download Text File" 

**Testing**:
- Verify link visibility responds to environment variable changes
- Test template renders without errors when archives disabled
- Verify both prayer marks page link and prayer card download work correctly
- Test that both links point to same file content

**Risks**: Low - mainly template context, optional template link update

---

## Database Changes
None required - feature uses existing `Prayer.text_file_path` column and `/api/archive/prayer/{prayer_id}/file` route.

## Function Signatures
No new functions required - using existing:
- `templates.TemplateResponse()` - existing template rendering
- `/api/archive/prayer/{prayer_id}/file` - existing file download route

## Testing Strategy
- **Unit**: Template rendering with different context variables
- **Integration**: End-to-end link clicking and file downloading
- **Manual**: UI verification across different prayer states and settings