# Prioritized Prayer Feed - Solution Assessment (Step 0)

## Problem
Need prioritized feed order: unprayed prayers first, admin-marked daily prayers second, others chronologically.

## Solution Options

**Option 1: Prayer Attribute System** (Recommended)
- Use existing PrayerAttribute to mark `daily_priority`
- Extend feed queries with priority ordering
- Low risk, uses proven infrastructure

**Option 2: Priority Score Field**
- Add score column to Prayer table  
- High performance, but complex migration

**Option 3: Multiple Query Composition**
- Separate queries for each priority tier
- Poor performance, pagination issues

**Option 4: New Feed Type**
- Add "prioritized" to existing feed types
- User must opt-in, doesn't change defaults

## Recommendation
**Option 1** - leverages existing attribute system with minimal risk and natural admin integration.

---

# Step 1: Prioritized Prayer Feed Feature Description

## Problem
Users need unprayed prayers to appear first in their feed, with admin-marked daily priorities second, ensuring critical prayers get attention before being buried in chronological order.

## User Stories
- As a community member, I want to see unprayed prayers at the top of my feed so that no prayer request goes unanswered
- As an admin, I want to mark certain prayers as "daily priority" so that important community needs get consistent visibility
- As a prayer warrior, I want a clear visual distinction between unprayed, priority, and regular prayers so that I can focus my attention appropriately
- As a user returning after time away, I want to see what needs prayer most rather than just the newest posts
- As someone with limited time, I want the most important prayers to be immediately visible without scrolling

## Core Requirements
- Implement priority ordering: unprayed prayers first, admin-marked daily priorities second, others chronologically
- Use existing PrayerAttribute system to mark `daily_priority` status
- Maintain all existing prayer functionality (marking, archiving, flagging) with new ordering
- Add admin interface for marking/unmarking daily priority prayers
- Ensure performance remains fast with new query ordering

## User Flow
1. User visits prayer feed and sees prayers in priority order automatically
2. Unprayed prayers appear at top with visual indicator (e.g., highlighted border)
3. Daily priority prayers appear next with distinct visual marker (e.g., star icon)
4. Remaining prayers follow in chronological order as before
5. Admin can mark/unmark prayers as daily priority through prayer detail page
6. All prayer interactions (marking, details, etc.) work normally in priority-ordered feed

## Success Criteria
- Unprayed prayers receive community response within 24 hours instead of potentially being missed
- Daily priority prayers maintain consistent visibility throughout the day
- Page load performance remains under 500ms with priority ordering
- Admin daily priority marking interface is intuitive and accessible
- User satisfaction with prayer discovery improves (measured through engagement metrics)