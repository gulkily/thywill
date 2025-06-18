# Invite Tree Implementation Plan

## Overview
This document outlines the implementation plan for adding an invite tree feature to the prayer app. The invite tree will show the complete hierarchy of who invited whom, tracing back to the original admin account.

## Current State Analysis

### ✅ What we have:
- `InviteToken` model with `created_by_user` field - tracks who created each invite
- Invite creation/claiming flow that marks invites as used
- User model tracks when users were created

### ❌ What we're missing:
- **Critical gap**: No tracking of which invite token was used to create each user
- No direct relationship between users and their inviters
- No invite tree functionality in the UI

### The Problem:
When a user claims an invite token (lines 1006-1009 in `app.py`), we create the user and mark the invite as used, but we don't store which invite was used to create that user. This means we can't build the invite tree.

## 3-Step Implementation Plan

### Step 1: Data Model Enhancement
**Goal:** Add the missing data relationship to track who invited whom

**Tasks:**
1. **Add fields to User model:**
   - `invited_by_user_id: str | None` - ID of the user who invited this user
   - `invite_token_used: str | None` - Token that was used to create this account

2. **Add field to InviteToken model:**
   - `used_by_user_id: str | None` - ID of user who claimed this invite

3. **Create database migration:**
   - Add new columns to existing tables
   - Handle existing users (set their `invited_by_user_id` to None or "system")

4. **Update user creation flow:**
   - Modify `/claim/{token}` endpoint to store invite relationships
   - Link new users to their inviters through the invite token

**Files to modify:**
- `models.py` - Add new fields
- `app.py` - Update `claim_post()` function and `migrate_database()`

### Step 2: Invite Tree Logic & Data Retrieval
**Goal:** Build the backend logic to construct and query the invite tree

**Tasks:**
1. **Create core tree functions:**
   ```python
   def get_invite_tree() -> dict
   def get_user_descendants(user_id: str) -> list[dict]
   def get_user_invite_path(user_id: str) -> list[dict]
   def get_invite_stats() -> dict
   ```

2. **Implement recursive tree building:**
   - Start from root admin user
   - Recursively find all users invited by each user
   - Include metadata: join dates, invite counts, active status

3. **Add database queries:**
   - Efficient queries with proper joins
   - Handle edge cases (orphaned users, deleted invites)

**Files to modify:**
- `app.py` - Add tree logic functions

### Step 3: Invite Tree UI Implementation
**Goal:** Create the invite tree page visible to all users

**Tasks:**
1. **Create backend route:**
   - `@app.get("/invite-tree")` endpoint
   - Return tree data and render template

2. **Create template:**
   - `templates/invite_tree.html`
   - Collapsible tree nodes with CSS/JavaScript
   - Show user names, join dates, descendant counts

3. **Add navigation:**
   - Link to invite tree from main menu
   - Add to admin panel as well

4. **Style the tree:**
   - Tree lines and indentation
   - User badges and metadata
   - Responsive design for mobile

**Files to create/modify:**
- `templates/invite_tree.html` - New template
- `templates/menu.html` - Add navigation link
- `app.py` - Add route handler

## Implementation Details

### Data Model Changes

```python
# In models.py - User class additions
class User(SQLModel, table=True):
    # ... existing fields ...
    invited_by_user_id: str | None = Field(default=None)  # Who invited this user
    invite_token_used: str | None = Field(default=None)   # Which token was used

# In models.py - InviteToken class additions  
class InviteToken(SQLModel, table=True):
    # ... existing fields ...
    used_by_user_id: str | None = Field(default=None)     # Who used this token
```

### Tree Structure Example

```
👑 Admin (system)
├── 📱 Alice (invited 3 people)
│   ├── 🙏 Bob
│   ├── 🙏 Carol  
│   └── 📱 David (invited 1 person)
│       └── 🙏 Eve
├── 🙏 Frank
└── 📱 Grace (invited 2 people)
    ├── 🙏 Henry
    └── 🙏 Iris
```

### API Response Format

```json
{
  "tree": {
    "user": {"id": "admin", "name": "Admin", "created_at": "..."},
    "children": [
      {
        "user": {"id": "alice", "name": "Alice", "created_at": "..."},
        "children": [...]
      }
    ]
  },
  "stats": {
    "total_users": 9,
    "total_invites_sent": 6,
    "max_depth": 3
  }
}
```

## Security & Privacy Considerations

- All users can view the invite tree (per requirements)
- Display names only, no sensitive information
- No invite tokens exposed in the UI
- Rate limiting on tree endpoint if needed

## Testing Strategy

1. **Unit tests** for tree building functions
2. **Integration tests** for database relationships
3. **UI tests** for tree rendering and navigation
4. **Performance tests** for large trees

## Rollout Plan

1. Deploy Step 1 first to start collecting invite relationships
2. Test data migration on staging environment  
3. Deploy Steps 2 & 3 together for complete feature
4. Monitor performance and user engagement

## Future Enhancements

- Search within the invite tree
- Export tree data
- Invite statistics and analytics
- Gamification (invite leaderboards) 