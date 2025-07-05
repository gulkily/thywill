# ThyWill Backup, Export, Restore, and Import Features

## Overview
ThyWill implements a comprehensive backup and recovery system with multiple layers of protection, featuring an archive-first architecture that prioritizes human-readable text files and complete disaster recovery capabilities.

## CLI Commands

### Database Backup Commands
```bash
./thywill backup              # Create database backup
./thywill list               # List all available backups  
./thywill restore <file>     # Restore from specific backup file
./thywill cleanup            # Clean up old backups
./thywill verify <file>      # Verify backup integrity
```

### Import Commands
```bash
./thywill import prayers <file>      # Import prayers from JSON file
./thywill import text-archives       # Import data from text_archives/ directory
./thywill import text-archives --dry-run  # Preview text archive import
```

### Archive Management Commands
```bash
./thywill heal-archives              # Create missing archive files
./thywill sync-users                 # Export/sync users to text archives
./thywill export-sessions            # Export active user sessions to JSON backup
./thywill sync-archives              # Complete archive synchronization
./thywill validate-archives          # Check archive completeness and integrity
./thywill test-recovery              # Simulate complete database recovery
./thywill full-recovery              # Perform complete database reconstruction
./thywill repair-archives            # Fix archive inconsistencies
./thywill recovery-report            # Generate recovery capability report
./thywill reconstruct-from-archives  # Rebuild database relationships from text archives
./thywill validate-consistency       # Validate archive-database consistency
```

## API Endpoints

### Archive Download Routes
- `GET /api/archive/user/{user_id}/download` - Download user's complete text archive as ZIP
- `GET /api/archive/user/{user_id}/metadata` - Get metadata about user's available archives  
- `GET /api/archive/community/list` - List all community archive files
- `GET /api/archive/community/download` - Download complete community text archive
- `GET /api/archive/prayer/{prayer_id}/file` - Get direct link to prayer's text archive file
- `DELETE /api/archive/downloads/cleanup` - Clean up old download files (admin only)

## Core Services

### Archive Download Service
**Location:** `app_helpers/services/archive_download_service.py`
- `create_user_archive_zip()` - Create ZIP of user's text archives
- `create_full_community_zip()` - Create ZIP of entire community archive  
- `get_user_archive_metadata()` - Get comprehensive archive metadata
- `list_community_archives()` - List all community archives with metadata
- `cleanup_old_downloads()` - Remove old download files

### Text Archive Service
**Location:** `app_helpers/services/text_archive_service.py`
- Archive management and validation
- Text file creation and organization

### Text Importer Service  
**Location:** `app_helpers/services/text_importer_service.py`
- Import data from text archives into database
- Idempotent import operations
- Dry-run capability

## Backup Management Scripts

### Deployment Backup Management
**Location:** `deployment/backup_management.sh`

**Commands:**
```bash
./backup_management.sh hourly        # Create timestamped hourly backup
./backup_management.sh daily         # Create timestamped daily backup  
./backup_management.sh weekly        # Create timestamped weekly backup
./backup_management.sh list          # List all available backups
./backup_management.sh restore <file> # Traditional restore
./backup_management.sh restore-safe <file> # Migration-safe restore with schema updates
./backup_management.sh cleanup       # Clean up old backups
```

**Features:**
- Integrity verification with checksums
- Remote backup support
- Retention policies (48 hours for hourly, 30 days for daily, 12 weeks for weekly)

## CLI Python Modules

### Archive Management
**Location:** `app_helpers/cli/archive_management.py`
- `heal` - Create missing archive files
- `sync` - Interactive archive synchronization
- `validate` - Archive structure validation
- `import` - Text archive import

### Prayer Import
**Location:** `app_helpers/cli/prayer_import.py`
- Import prayers from JSON files
- User creation for missing authors
- Batch processing with statistics

### Archive Validation
**Location:** `app_helpers/cli/archive_validation.py`
- Comprehensive archive validation
- Recovery testing
- Consistency checking

## Session Management Tools

### Session Export/Restore
**Location:** `tools/`
- `export_active_sessions.py` - Export sessions before database restoration
- `restore_active_sessions.py` - Restore sessions after database reconstruction
- Handles both username-based and UUID-based schemas

## Text Archive Import Script

**Location:** `scripts/utils/import_text_archives.py`
- Import from text_archives/ directory or ZIP files
- Dry-run capability
- Copy archive files to local directory
- Validation after import
- Comprehensive error handling

## Database Recovery Tools

### Complete Recovery
**Location:** `tools/restore_from_archives_username_based.py`
- Complete database reconstruction from archives
- Username-based schema migration
- Session preservation
- Idempotent operations

### Archive Healing
**Location:** `scripts/utils/heal_prayer_archives.py`
- Create missing archive files
- Backfill historical data
- Content-based verification

## Key Features

### Idempotency & Safety
- All import operations are idempotent (safe to run multiple times)
- Dry-run modes for testing
- Backup creation before destructive operations
- Integrity verification with checksums

### Archive-First Architecture
- Text files created before database entries
- Human-readable format
- Complete audit trail
- Disaster recovery capability

### Multi-Format Support
- JSON prayer imports
- ZIP archive imports
- Text archive directories  
- Database backups (.db files)

### Comprehensive Coverage
- User data and registrations
- Prayer requests and generated prayers
- Prayer marks and activities
- Session preservation
- Invite relationships
- Complete activity history

## Usage Patterns

### Routine Backups
```bash
# Regular database backup
./thywill backup

# Archive maintenance
./thywill heal-archives
./thywill validate-archives
```

### Data Import
```bash
# Import prayers from JSON
./thywill import prayers data.json

# Import from text archives (with preview)
./thywill import text-archives --dry-run
./thywill import text-archives
```

### User Archive Downloads
- Individual users can download their complete prayer history as ZIP files
- Admins can download community-wide archives
- All downloads include metadata and are automatically cleaned up

### Disaster Recovery
```bash
# Test recovery capability
./thywill test-recovery

# Full database reconstruction
./thywill full-recovery

# Validate consistency after recovery
./thywill validate-consistency
```

## Security & Compliance
- All archive operations respect user privacy
- Admin-only access to community-wide exports
- Automatic cleanup of temporary download files
- Comprehensive audit logging for all operations