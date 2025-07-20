# Original Request Auto-Expand Feature Plan

## Overview
Add a user preference option to automatically expand the "Original Request" section on prayer cards in the feed, eliminating the need for manual expansion on each page load.

## Current State Analysis

### Existing Implementation
- **Location**: `templates/components/prayer_card.html:22-32`
- **Current Behavior**: Original Request sections are collapsed by default
- **Toggle Function**: `toggleOriginalRequest()` in `templates/base.html:250-263`
- **Visual Indicators**: Chevron arrows (▶ collapsed, ▼ expanded)

### Current User Preference Patterns
- **Theme Preferences**: Stored in localStorage with fallback to system preference
- **Prayer Mode Progress**: Stored in localStorage with error handling
- **No Server-side UI Preferences**: App follows client-side preference philosophy
- **User Model**: Contains minimal preference fields (`welcome_message_dismissed`)

## Proposed Solution

### Approach: Client-Side localStorage Storage
Following established ThyWill patterns for UI preferences using localStorage.

### Storage Key
```
'prayer_original_request_auto_expand'
```

### Storage Values
- `true` - Auto-expand Original Request sections
- `false` - Keep collapsed (default behavior)
- `null/undefined` - Default to collapsed (backward compatibility)

## Implementation Plan

### Phase 1: Core Auto-Expand Functionality

#### 1.1 Update Prayer Card Template
**File**: `templates/components/prayer_card.html`

- Modify Original Request section to check localStorage preference
- Update initial CSS classes based on preference
- Adjust chevron initial state based on preference

#### 1.2 Enhance Toggle JavaScript Function  
**File**: `templates/base.html`

- Update `toggleOriginalRequest()` to store preference changes
- Add initialization function to apply preferences on page load
- Include error handling following prayer mode progress pattern
- Ensure preference persists across prayer cards and page loads

#### 1.3 Add Preference Initialization
**File**: `templates/base.html` or new script section

- Add `initializeOriginalRequestPreference()` function
- Call on DOMContentLoaded to apply preferences to all prayer cards
- Handle both individual toggle changes and bulk preference application

### Phase 2: User Interface for Preference Management

#### 2.1 Add Settings Option
**File**: `templates/menu.html`

- Add toggle switch in Advanced Tools section for auto-expand preference
- Use consistent styling with existing menu items
- Include clear labeling: "Auto-expand Original Requests"

#### 2.2 Settings Toggle Functionality
**File**: `templates/menu.html` or dedicated script section

- Add `toggleAutoExpandPreference()` function
- Update localStorage when preference changes
- Apply changes immediately to all visible prayer cards
- Provide visual feedback for preference change

### Phase 3: Enhanced User Experience

#### 3.1 Visual Preference Indicator
- Show current auto-expand setting in menu toggle state
- Consistent with other preference indicators in the application

#### 3.2 Immediate Application
- When preference changes, immediately apply to all visible prayer cards
- No page refresh required for preference changes
- Smooth transitions using existing CSS `transition-transform` classes

## Technical Implementation Details

### JavaScript Functions Required

```javascript
// New functions to implement:
1. initializeOriginalRequestPreference() - Apply preference on page load
2. toggleAutoExpandPreference() - Handle preference toggle from menu
3. updateOriginalRequestPreference() - Central preference update function
4. applyOriginalRequestPreference() - Apply preference to all cards

// Modified functions:
1. toggleOriginalRequest() - Update to store individual toggle changes
```

### localStorage Error Handling
Following existing prayer mode pattern:
```javascript
try {
    localStorage.setItem('prayer_original_request_auto_expand', value);
} catch (e) {
    // Silently handle storage errors (private browsing, storage full, etc.)
}
```

### CSS Class Management
- Use existing `hidden` class for collapse/expand
- Leverage existing `transition-transform` for chevron animation
- No additional CSS required

## Dependencies and Prerequisites

### No External Dependencies
- Uses existing CSS classes and JavaScript patterns
- No new libraries or frameworks required
- No database schema changes needed

### Existing System Dependencies
- Requires current toggle functionality (`toggleOriginalRequest`)
- Depends on existing localStorage infrastructure
- Uses established menu structure in `templates/menu.html`

## Backward Compatibility

### Default Behavior Preserved
- Users without preference set will see existing collapsed behavior
- No breaking changes to current functionality
- Progressive enhancement approach

### Graceful Degradation
- Works without localStorage support (falls back to collapsed)
- Error handling prevents JavaScript errors in edge cases
- No impact on users with disabled JavaScript (current behavior maintained)

## Testing Considerations

### Test Cases Required
1. **Preference Storage**: Verify localStorage persistence across page loads
2. **Default Behavior**: Ensure new users see collapsed sections (current behavior)
3. **Toggle Functionality**: Confirm individual toggles still work and update preference
4. **Menu Settings**: Test preference toggle in Advanced Tools section
5. **Error Handling**: Test localStorage errors (private browsing mode)
6. **Cross-Device**: Confirm preferences are device-specific (expected behavior)
7. **Performance**: Ensure no impact on page load with multiple prayer cards

### Browser Testing
- Test localStorage support across target browsers
- Verify preference persistence in private/incognito mode behavior
- Test error handling when localStorage is disabled

## Implementation Timeline

### Phase 1 (Core Functionality): 2-4 hours
- Update prayer card template
- Enhance JavaScript toggle function
- Add preference initialization

### Phase 2 (User Interface): 1-2 hours  
- Add menu settings option
- Implement preference toggle functionality

### Phase 3 (Polish & Testing): 1-2 hours
- Visual enhancements
- Comprehensive testing
- Error handling verification

**Total Estimated Time**: 4-8 hours

## Success Criteria

### User Experience Goals
1. Users can set preference to auto-expand Original Request sections
2. Preference persists across browser sessions and page navigation
3. Individual prayer card toggles continue to work as expected
4. Settings are easily accessible and clearly labeled
5. No performance impact on feed loading

### Technical Goals
1. Clean implementation following existing code patterns
2. Robust error handling for localStorage edge cases
3. No breaking changes to current functionality
4. Maintainable code with clear function separation
5. Comprehensive test coverage for preference functionality

## Future Enhancement Opportunities

### Additional Preference Options
- Auto-expand praise reports
- Feed display preferences (card density, font size)
- Activity feed filtering preferences

### Preference Management
- Export/import preferences
- Reset to defaults option
- Preference backup/restore functionality

### Cross-Device Synchronization
- Server-side preference storage (requires database schema changes)
- Account-based preference sync across devices
- Preference versioning and migration

## Risk Mitigation

### Storage Limitations
- localStorage has browser storage limits (~5-10MB)
- Simple boolean preference has negligible impact
- Error handling prevents application failure

### Browser Support
- localStorage supported in all modern browsers
- Graceful degradation for unsupported browsers
- No breaking changes for edge cases

### User Confusion
- Clear labeling in settings menu
- Consistent behavior with existing preferences
- Obvious visual feedback for preference changes

---

## Conclusion

This feature enhances user experience for frequent prayer platform users by eliminating repetitive manual expansion of Original Request sections. The implementation leverages existing ThyWill patterns and infrastructure, ensuring consistency with the application's architecture while providing immediate user value.

The client-side localStorage approach aligns perfectly with ThyWill's preference management philosophy and provides optimal performance without requiring database changes or server-side complexity.