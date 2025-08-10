# Prayer Text File Linking - Feature Description

## Problem
Technically adept users need direct access to the underlying text archive files for prayers they're viewing to enable advanced analysis, backup workflows, or debugging.

## User Stories
- As a technical user, I want to click a link on a prayer's detail page so that I can view the raw text archive file
- As an admin, I want to provide transparent access to the underlying data so that users can verify system integrity
- As a power user, I want to access text files directly so that I can perform advanced analysis or create custom workflows
- As a developer, I want to link to specific prayer text files so that I can debug archive-related issues

## Core Requirements
- Add "View Text File" link on individual prayer detail pages (`/prayer/{id}`)
- Link points directly to the corresponding text archive file for that prayer
- Only show link when text archives are enabled (`TEXT_ARCHIVE_ENABLED=true`)
- Respect existing authentication and permissions (user must be logged in)
- Handle cases where text file doesn't exist gracefully (show appropriate message)

## User Flow
1. User navigates to a prayer detail page (`/prayer/{prayer_id}`)
2. User sees "View Text File" link (if text archives enabled)
3. User clicks link
4. User is taken directly to the raw text file content for that specific prayer
5. User can view, copy, or download the text file content

## Success Criteria
- Link appears on all prayer detail pages when text archives are enabled
- Clicking link displays the correct text file for that specific prayer
- Non-existent files show clear error message instead of breaking
- Feature integrates seamlessly with existing UI without disrupting prayer page layout
- Performance impact is minimal (no unnecessary file system checks)