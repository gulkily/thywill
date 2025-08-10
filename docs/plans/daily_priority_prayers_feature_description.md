# Daily Priority Prayers - Feature Description

## Problem Statement
Admins need a way to highlight important community prayers that deserve special attention and visibility on a daily basis.

## User Stories
- As an admin, I want to mark specific prayers as "Daily Priority" so that community members see the most important prayers first
- As a community member, I want to see daily priority prayers prominently displayed so I can focus my prayers on what matters most today
- As an admin, I want to easily manage daily priorities so I can update them as situations change
- As a community member, I want to distinguish priority prayers from regular prayers so I understand their special significance
- As an admin, I want priority prayers to reset daily so yesterday's priorities don't clutter today's focus

## Core Requirements
- Admin-only menu option to mark/unmark prayers as "Daily Priority"
- Daily priority prayers appear at the top of the main feed with visual distinction
- Priority status resets automatically at midnight (server time)
- Clear visual indicators (badge, highlighting) for priority prayers
- Priority prayers maintain chronological order within their priority section

## User Flow
1. Admin views any prayer in the system
2. Admin clicks prayer menu and selects "Mark as Daily Priority" option
3. Prayer immediately moves to priority section with visual badge
4. All users see priority prayers at top of main feed
5. At midnight, priority status automatically expires
6. Previously priority prayers return to normal chronological position

## Success Criteria
- Admins can successfully mark/unmark prayers as daily priorities
- Priority prayers are visually distinct and appear at feed top
- Priority status automatically expires at midnight
- Regular users can clearly identify and focus on priority prayers
- Admin actions are logged for transparency and accountability