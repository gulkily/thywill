# Text Archive System Documentation

## Overview

The ThyWill application implements an "archive-first" data philosophy where human-readable text files serve as the authoritative source of truth for all essential application data. This ensures data durability, transparency, and recoverability beyond traditional database backups.

## Architecture Philosophy

### Archive-First Principle

1. **Text files are written FIRST** - Before any database record is created, the data is written to a human-readable text archive file
2. **Database records reference archives** - Every database record contains a `text_file_path` field pointing to its source archive
3. **Archives can recreate the database** - The entire database can be reconstructed from text archives if needed
4. **Human-readable format** - All archives use plain text formatting that humans can read and understand

### Key Benefits

- **Data Durability**: Text files are more durable than database formats
- **Transparency**: All data is human-readable without special tools
- **Auditability**: Complete history of all activities is preserved in text
- **Recoverability**: Database can be fully reconstructed from archives
- **Backup Simplicity**: Simple file backup is sufficient for complete data preservation

## File Structure

```
text_archives/
├── prayers/
│   ├── 2024/
│   │   ├── 01/
│   │   │   ├── 2024_01_15_prayer_at_1430.txt
│   │   │   └── 2024_01_15_prayer_at_1545.txt
│   │   └── 02/
│   └── 2025/
├── users/
│   ├── 2024_01_users.txt
│   ├── 2024_02_users.txt
│   └── 2025_01_users.txt
└── activity/
    ├── activity_2024_01.txt
    ├── activity_2024_02.txt
    └── activity_2025_01.txt
```

## Archive File Formats

### Prayer Archives

Each prayer gets its own individual file with complete history:

```
Prayer 123 by John_Smith
Submitted January 15 2024 at 14:30
Project: healing
Audience: all

Please pray for my grandmother's recovery from surgery.

Generated Prayer:
Heavenly Father, we lift up John's grandmother in prayer...

Activity:
January 15 2024 at 14:35 - Mary_Johnson prayed this prayer
January 16 2024 at 09:20 - John_Smith marked this prayer as answered
January 16 2024 at 09:20 - John_Smith added testimony: She's doing much better!
```

### User Registration Archives

Monthly files tracking all user registrations:

```
User Registrations for January 2024

January 15 2024 at 14:30 - John_Smith joined on invitation from Mary_Johnson
January 16 2024 at 09:15 - Sarah_Wilson joined directly
January 16 2024 at 11:30 - Mike_Brown joined on invitation from John_Smith
```

### Activity Archives

Monthly files tracking all site activity:

```
Activity for January 2024

January 15 2024
14:30 - John_Smith registered via invitation from Mary_Johnson
14:35 - John_Smith submitted prayer 123 (healing)
14:40 - Mary_Johnson prayed for prayer 123

January 16 2024
09:15 - Sarah_Wilson registered directly
09:20 - John_Smith marked prayer 123 as answered
```

## Implementation Services

### TextArchiveService

Core service handling file operations:

- `create_prayer_archive()` - Creates new prayer files
- `append_prayer_activity()` - Adds activity to prayer files
- `append_user_registration()` - Logs user registrations
- `append_monthly_activity()` - Logs site activity
- `parse_prayer_archive()` - Reads and parses prayer files

### ArchiveFirstService

High-level service implementing archive-first workflows:

- `create_prayer_with_text_archive()` - Archive-first prayer creation
- `append_prayer_activity_with_archive()` - Archive-first activity logging
- `create_user_with_text_archive()` - Archive-first user registration

## Configuration

### Environment Variables

```bash
# Enable/disable text archives
TEXT_ARCHIVE_ENABLED=true

# Base directory for archives (relative to app root)
TEXT_ARCHIVE_BASE_DIR=./text_archives

# Days after which archives may be compressed
TEXT_ARCHIVE_COMPRESSION_AFTER_DAYS=365
```

### Application Settings

In `app.py`:

```python
TEXT_ARCHIVE_ENABLED = os.getenv("TEXT_ARCHIVE_ENABLED", "true").lower() == "true"
TEXT_ARCHIVE_BASE_DIR = os.getenv("TEXT_ARCHIVE_BASE_DIR", "./text_archives")
TEXT_ARCHIVE_COMPRESSION_AFTER_DAYS = int(os.getenv("TEXT_ARCHIVE_COMPRESSION_AFTER_DAYS", "365"))
```

## Database Schema Changes

All relevant models include `text_file_path` fields:

```python
class Prayer(SQLModel, table=True):
    # ... existing fields ...
    text_file_path: str | None = Field(default=None)  # Path to text archive

class User(SQLModel, table=True):
    # ... existing fields ...
    text_file_path: str | None = Field(default=None)  # Path to text archive

class PrayerMark(SQLModel, table=True):
    # ... existing fields ...
    text_file_path: str | None = Field(default=None)  # Path to text archive

class PrayerAttribute(SQLModel, table=True):
    # ... existing fields ...
    text_file_path: str | None = Field(default=None)  # Path to text archive

class PrayerActivityLog(SQLModel, table=True):
    # ... existing fields ...
    text_file_path: str | None = Field(default=None)  # Path to text archive
```

## Integration Points

### Prayer Submission

```python
# OLD: Direct database creation
prayer = Prayer(author_id=user.id, text=text)
session.add(prayer)

# NEW: Archive-first approach
prayer = submit_prayer_archive_first(
    text=text,
    author=user,
    tag=tag,
    target_audience=target_audience,
    generated_prayer=final_prayer
)
```

### User Registration

```python
# OLD: Direct database creation
user = User(**user_data)
session.add(user)

# NEW: Archive-first approach
user, archive_path = create_user_with_text_archive(user_data, uid)
```

### Activity Logging

```python
# OLD: Database-only logging
mark = PrayerMark(user_id=user.id, prayer_id=prayer_id)
session.add(mark)

# NEW: Archive-first logging
append_prayer_activity_with_archive(prayer_id, "prayed", user)
```

## File Operations

### Thread Safety

All file operations use atomic writes and file locking:

```python
def _append_to_file(self, file_path: str, content: str):
    with open(file_path, 'a', encoding='utf-8') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
        f.write(content + '\n')
        f.flush()
        os.fsync(f.fileno())  # Force write to disk
```

### Atomic Creation

New files are created atomically using temporary files:

```python
def _write_file_atomic(self, file_path: str, content: str):
    temp_path = file_path + '.tmp'
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.rename(temp_path, file_path)  # Atomic rename
```

## Disaster Recovery

### Full Database Reconstruction

The text archives contain all necessary information to rebuild the entire database:

1. **User Registration Data**: All users and their invitation relationships
2. **Prayer Data**: Complete prayer content, metadata, and history
3. **Activity History**: All user interactions and prayer status changes
4. **Relationships**: User invitation trees and prayer authorship

### Recovery Process

1. Create fresh database with current schema
2. Parse user registration archives to recreate User records
3. Parse prayer archives to recreate Prayer records
4. Parse activity logs to recreate PrayerMark and PrayerAttribute records
5. Validate data consistency between archives and database

### Data Validation

The system includes validation functions to ensure archive-database consistency:

```python
def validate_archive_database_consistency(prayer_id: str) -> Dict:
    # Compare archive content with database records
    # Return validation results with any discrepancies
```

## Testing Considerations

### Test Environment

Tests automatically disable text archives to prevent file creation:

```python
# In conftest.py
with patch('app_helpers.services.text_archive_service.TEXT_ARCHIVE_ENABLED', False):
    # Test execution with archives disabled
```

### Legacy Prayer Handling

The system gracefully handles prayers created before archive implementation:

```python
if not prayer.text_file_path:
    # Create missing archive file for legacy prayer
    archive_file_path = text_archive_service.create_prayer_archive(archive_data)
    prayer.text_file_path = archive_file_path
```

## Monitoring and Maintenance

### Log Messages

The system logs all archive operations for monitoring:

```
INFO: Created prayer archive: /path/to/prayer/file.txt
INFO: Added activity to /path/to/prayer/file.txt: prayed by user
WARNING: Prayer 123 has no associated text archive - creating one now
```

### File System Requirements

- **Storage**: Plan for ~1KB per prayer, ~100 bytes per activity
- **I/O**: Mostly append operations, minimal disk overhead
- **Backup**: Simple file-based backup sufficient for complete data preservation

## Future Enhancements

### Compression

Archives older than `TEXT_ARCHIVE_COMPRESSION_AFTER_DAYS` may be compressed while preserving readability.

### Import/Export Tools

Additional tools for importing archives from other formats and exporting to various backup formats.

### Archive Validation

Automated tools to validate archive integrity and consistency with database records.