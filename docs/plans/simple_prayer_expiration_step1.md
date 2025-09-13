# Simple Prayer Expiration System - Step 1: Feature Description

## Overview
A straightforward system to automatically expire prayers after a set period, replacing the complex AI-powered archive date suggestion system.

## User Stories

### As a Prayer Author
- **I want my prayers to automatically expire after a reasonable time** so they don't clutter the community feed indefinitely
- **I want to manually set a custom expiration date** when submitting a prayer if I know when it should expire
- **I want to extend or remove expiration dates** for prayers that need ongoing prayer support
- **I want to see when my prayers will expire** so I can manage them appropriately

### As a Community Member  
- **I want to see fresh, relevant prayers** without old, outdated requests cluttering the feed
- **I want to know when a prayer is approaching expiration** so I can pray for urgent requests
- **I want expired prayers to be clearly marked** but still accessible if needed

### As an Administrator
- **I want to configure default expiration periods** for different types of prayers
- **I want to see system-wide expiration statistics** to understand prayer lifecycle patterns
- **I want to disable expiration entirely** if the community prefers unlimited prayer duration

## Core Requirements

### 1. Manual Expiration Date Setting
- Add optional "Expiration Date" field to prayer submission form
- Allow prayer authors to set a specific future date when the prayer should expire
- Default behavior: no expiration date (prayers remain active indefinitely)

### 2. Default Expiration Feature Flag
- New environment variable: `DEFAULT_PRAYER_EXPIRATION_DAYS` 
- When set (e.g., `DEFAULT_PRAYER_EXPIRATION_DAYS=30`), automatically set expiration date X days from creation
- When unset or `0`, prayers have no default expiration
- Can be overridden by manual expiration date setting

### 3. Prayer Lifecycle Management
- **Active**: Prayer is normal, shows in all feeds
- **Expiring Soon**: Prayer expires within 7 days, shows warning indicator
- **Expired**: Prayer no longer shows in main feeds, moves to "expired" status

### 4. User Interface Elements
- Expiration date picker in prayer submission form (optional)
- "Expires: [date]" indicator on prayer cards for prayers with expiration dates
- "⏰ Expiring Soon" warning for prayers expiring within 7 days
- "📅 Expired" status indicator for expired prayers

### 5. Prayer Author Controls
- "Extend Expiration" action to add more time (7 days, 30 days, or custom date)
- "Remove Expiration" action to make prayer permanent
- "Expire Now" action to manually expire immediately

## Technical Approach

### Database Design
- Use existing `PrayerAttribute` system (no schema changes needed)
- Store expiration date as attribute: `expiration_date: "2025-10-15"`
- Store expiration status as attribute: `expired: "true"` when expired

### Feature Flags
- `DEFAULT_PRAYER_EXPIRATION_DAYS=0` (default: disabled)
- `PRAYER_EXPIRATION_ENABLED=false` (master toggle)

### Implementation Strategy
- **Phase 1**: Manual expiration date setting during prayer submission
- **Phase 2**: Default expiration with configurable days
- **Phase 3**: Expiration management UI (extend, remove, expire)
- **Phase 4**: Feed filtering and expiration indicators

## Success Criteria
- Prayer authors can set expiration dates when submitting prayers
- Default expiration works when configured via environment variable  
- Expired prayers are clearly distinguished from active prayers
- System is simple to understand, configure, and debug
- No complex AI integration or prompt engineering required

## Out of Scope (For Now)
- Automatic expiration based on prayer content analysis
- AI-suggested expiration dates
- Email notifications about expiring prayers
- Bulk expiration management tools
- Historical expiration analytics

## Questions for Consideration
1. Should expired prayers be completely hidden or just moved to a separate view?
2. Should there be different default expiration periods for different prayer types?
3. Should community members be notified when prayers they've prayed for are about to expire?
4. Should expired prayers automatically become "answered" or remain in a separate "expired" state?

---
**Next Step**: Review this feature description, then proceed to Step 2 (Development Plan) in FEATURE_DEVELOPMENT_PROCESS.md