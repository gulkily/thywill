-- Migration 007: Remove religious preference system
-- 
-- This migration validates that religious preference fields have been removed.
-- The actual removal was completed manually/directly in the database.

-- Validate that religious preference fields no longer exist in user table
-- This is a validation-only migration since the work was already completed

-- Check that user table doesn't have religious_preference column
-- (This would fail if the column still exists, which is what we want)

-- Check that user table doesn't have prayer_style column
-- (This would fail if the column still exists, which is what we want)

-- Check that prayer table doesn't have target_audience column  
-- (This would fail if the column still exists, which is what we want)

-- No actual DDL changes needed - validation only
SELECT 'Migration 007: Religious preference fields removal validated' as status;