# Persistent Daily Priorities - Feature Description

## Problem
Daily priority prayers currently expire after one day due to date-based logic, but should remain prioritized until manually removed by admins.

## User Stories

- As an admin, I want to mark prayers as daily priority so that they appear first in the daily prayer feed until I remove the priority
- As an admin, I want to see when a priority was set so that I have context about how long it's been prioritized  
- As a user viewing the daily prayer feed, I want to see priority prayers at the top consistently so that I know which prayers need the most attention
- As an admin, I want to easily remove daily priority status so that I can manage the priority list
- As a user, I want priority prayers to remain stable day-to-day so that I can develop consistent prayer patterns

## Core Requirements

- Daily priority status persists until manually removed (no automatic expiration)
- Priority date serves as metadata showing when priority was set
- Priority prayers always appear first in daily prayer feed regardless of date
- Admin can set and remove daily priority status via existing UI
- Existing priority prayers continue working without data loss

## User Flow

1. Admin marks prayer as daily priority via admin controls
2. Prayer appears at top of daily prayer feed with priority indicator
3. Priority date shows in UI as "Set as priority on [date]" 
4. Prayer remains prioritized across days until admin removes it
5. Admin removes priority status, prayer returns to normal chronological order

## Success Criteria

- Priority prayers persist across day boundaries
- No existing priority prayers are lost during transition
- Priority date is visible as helpful metadata in UI
- Daily prayer feed consistently shows priorities first
- Admin can easily manage priority status without confusion