# Separate Daily and Longest Unprayed Sections - Feature Description

## Problem Statement
The current daily prayer section combines two different concepts (prayers marked as daily priorities and prayers that haven't been prayed the longest), creating confusion about what constitutes a "daily prayer" and reducing clarity for users seeking specific types of prayer content.

## User Stories
- As a user, I want to see prayers specifically marked as daily priorities in their own dedicated section so that I can focus on community-designated important prayers
- As a user, I want to see prayers that haven't been prayed for the longest time in a separate section so that I can help ensure all prayers receive attention
- As a user, I want clear section headers that help me understand the purpose of each prayer grouping so that I can choose where to focus my prayer time
- As a prayer community member, I want both sections to be clearly differentiated so that I understand the distinct purposes they serve
- As an admin, I want the daily priority system to remain focused on manually selected prayers so that the feature maintains its intended purpose

## Core Requirements
- Split current daily prayer section into two distinct sections
- Create "Daily Priority Prayers" section showing only prayers with `is_daily_priority=true`
- Create "Prayers Needing Attention" section showing prayers that haven't been prayed the longest
- Maintain existing functionality for both types of prayers
- Preserve current UI patterns and styling for consistency

## User Flow
1. User visits homepage or prayer feed
2. User sees "Daily Priority Prayers" section with prayers manually marked as daily priorities
3. User sees "Prayers Needing Attention" section with prayers sorted by least recently prayed
4. User can interact with prayers in both sections using existing prayer card functionality
5. User understands clear distinction between community priorities and prayers needing care

## Success Criteria
- Daily Priority Prayers section displays only prayers with `is_daily_priority=true`
- Prayers Needing Attention section displays prayers sorted by longest time since last prayer mark
- Both sections maintain existing prayer card functionality (marking, flagging, etc.)
- Section headers clearly communicate the purpose of each grouping
- No regression in existing daily priority management features
- Feed performance remains acceptable with separated sections