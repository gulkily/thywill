# Persistent Daily Priorities - Solution Assessment

## Problem Statement
Daily priority prayers currently disappear after one day due to date-based expiration logic, but should persist until manually unmarked.

## Solution Options

### Option 1: Remove Date Logic Entirely
**Pros:**
- Simplest implementation - just remove date checks
- No migration needed for existing priorities
- Maintains current database structure

**Cons:** 
- Loses "daily" semantic meaning
- May need UI terminology updates

### Option 2: Boolean Flag Approach
**Pros:**
- Clear semantic meaning (is_daily_priority: true/false)
- Simpler queries and logic
- Natural fit for toggle UI

**Cons:**
- Requires database migration
- Need to migrate existing date-based priorities

### Option 3: Hybrid Approach - Date as Metadata
**Pros:**
- Preserves when priority was set
- Can still show "set on X date" in UI
- Maintains audit trail

**Cons:**
- More complex logic
- Date field becomes confusing (not expiration)

### Option 4: Status-Based System
**Pros:**
- Could support multiple priority levels
- Extensible for future priority types
- Clear state management

**Cons:**
- Over-engineering for current needs
- More complex migration and logic

## Recommendation

**Option 1: Remove Date Logic Entirely**

Reasoning: Current system already stores priorities correctly, just has wrong expiration logic. Removing date checks is minimal code change with immediate fix. Can always enhance later if needed.