# Multi-Type Supporter Badge System Plan

## Overview
Extend the current supporter badge system to support multiple types of supporters with configurable badges.

## Current State
- Single `is_supporter` boolean field
- Single red heart badge (♥)
- Text archive based configuration

## Proposed Changes

### 1. Database Schema Updates
- Add `supporter_type` field to User model (default: 'financial')
- Keep `is_supporter` for backward compatibility
- Support multiple types: 'financial', 'prayer_warrior', 'advisor', 'community_leader'

### 2. Configuration System
- Create `supporter_badges_config.json` in project root
- Easy to edit without code changes
- Support custom symbols, colors, tooltips, and priority

### 3. Text Archive Format
- Update `user_attributes.txt` to include supporter_type
- Maintain backward compatibility

### 4. Template System Updates
- Update badge filters to support multiple types
- Show appropriate badge based on supporter_type
- Support badge stacking for users with multiple types

## Implementation Details

### Configuration File Structure
```json
{
  "financial": {
    "symbol": "♥",
    "color": "#dc2626",
    "tooltip": "Financial Supporter",
    "priority": 1
  },
  "prayer_warrior": {
    "symbol": "🙏",
    "color": "#8b5cf6",
    "tooltip": "Prayer Warrior",
    "priority": 2
  },
  "advisor": {
    "symbol": "🌟",
    "color": "#f59e0b",
    "tooltip": "Community Advisor",
    "priority": 3
  },
  "community_leader": {
    "symbol": "👑",
    "color": "#10b981",
    "tooltip": "Community Leader",
    "priority": 4
  }
}
```

### Text Archive Format
```
username: Michael Resonance
is_supporter: true
supporter_type: financial
supporter_since: 2025-07-15

username: Jane Doe
is_supporter: true
supporter_type: prayer_warrior
supporter_since: 2025-07-16
```

### Multi-Type Support
- Users can have multiple types (comma-separated)
- Display multiple badges in priority order
- Limit to 3 badges max to avoid clutter

## Benefits
1. **Easy Configuration**: Non-technical users can edit JSON file
2. **Flexible Types**: Support any number of supporter categories
3. **Visual Distinction**: Different symbols/colors for different contributions
4. **Backward Compatible**: Existing supporters continue to work
5. **Recognition**: Proper acknowledgment of different contribution types

## Migration Strategy
1. Add new fields with defaults
2. Update existing supporters to 'financial' type
3. Gradually migrate to new system
4. Update documentation