# Single Prayer Import Feature Description

## Problem
Operators cannot import individual prayer text files without importing entire text archive directories, making selective prayer restoration cumbersome and inefficient.

## User Stories
- As a system administrator, I want to import a single prayer text file so that I can restore specific prayers without affecting other data
- As a user recovering data, I want to restore just one prayer from my backup so that I don't have to rebuild entire archives
- As a developer testing imports, I want to import individual prayer files so that I can test specific scenarios without full data sets
- As a backup operator, I want to selectively restore prayers so that I can fix individual data corruption issues
- As a migration user, I want to import single prayers so that I can gradually move data between systems

## Core Requirements
- Accept single prayer text file path as command argument
- Parse and validate prayer text file format (same as existing text archive format)
- Import prayer data into database with proper user association and timestamps
- Handle duplicate detection (skip if prayer already exists based on content/timestamp)
- Provide clear feedback on import success/failure with specific error messages

## User Flow
1. User identifies specific prayer text file to import (e.g., `text_archives/prayers/username/prayer_123.txt`)
2. User runs command: `./thywill import-prayer <file_path>`
3. System validates file exists and has correct text archive format
4. System parses prayer content, metadata, and associated data (marks, attributes)
5. System checks for existing prayer to avoid duplicates
6. System imports prayer data and provides success confirmation
7. User can verify prayer appears in appropriate feeds and user history

## Success Criteria
- Command successfully imports valid prayer text files without affecting other data
- Duplicate detection prevents data corruption on repeated imports
- Import process completes in under 5 seconds for typical prayer files
- Clear error messages for invalid files, missing users, or format problems
- Imported prayers appear correctly in user feeds and maintain all original metadata