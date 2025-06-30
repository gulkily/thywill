# ThyWill Tools Directory

This directory contains debugging, analysis, and repair tools developed to diagnose and fix data integrity issues.

## Directory Structure

### 🔍 debug/
Scripts for investigating current database and archive state:
- `debug_production_db.py` - Examine database for orphaned records
- `debug_display_issues.py` - Investigate UI display problems (prayers by "None")
- `debug_archive_structure.py` - Analyze text archive file structure and content

### 📊 analysis/
Scripts for comprehensive data analysis:
- `analyze_production_issues.py` - Initial production issue analysis
- `validate_archive_consistency.py` - Comprehensive archive-database consistency validation

### 🔧 repair/
Scripts for fixing data integrity issues:
- `fix_archive_paths.py` - Fix broken archive path references in database
- `fix_orphaned_user_ids.py` - Handle prayers/marks with orphaned user IDs
- `create_placeholder_users.py` - Create placeholder users for orphaned references
- `reconstruct_from_archives.py` - Rebuild relationships from text archives
- `add_username_index.py` - Add performance indexes for username resolution

### 🚀 Restoration Tools (root level)
Major database restoration utilities:
- `export_active_sessions.py` - Export user sessions before restoration
- `restore_from_archives_username_based.py` - Complete database rebuild with username-based schema

## Usage Examples

### Quick Health Check
```bash
PRODUCTION_MODE=1 python tools/analysis/validate_archive_consistency.py --summary
```

### Debug Archive Structure
```bash
PRODUCTION_MODE=1 python tools/debug/debug_archive_structure.py
```

### Emergency Database Restoration
```bash
# Export sessions first
PRODUCTION_MODE=1 python tools/export_active_sessions.py

# Test restoration
PRODUCTION_MODE=1 python tools/restore_from_archives_username_based.py --dry-run

# Execute restoration
PRODUCTION_MODE=1 python tools/restore_from_archives_username_based.py --execute
```

## Tool Development Context

These tools were developed to address a fundamental architectural issue:
- **Problem**: Text archives use usernames, database uses UUID IDs
- **Symptom**: "Prayers by None" and orphaned relationships
- **Root Cause**: Username-to-ID resolution failures during import
- **Solution**: Either fix relationships or use username-based schema

## Historical Notes

### Issue Timeline
1. **Initial Problem**: Prayers showing no author, "None" in prayer marks
2. **Diagnosis**: Orphaned user ID references (UUIDs pointing to deleted users)
3. **Attempted Fix**: Reconstruction from archives (partially successful)
4. **Final Solution**: Database rebuild from text archives (successful)

### Lessons Learned
- Text archives are the authoritative source of truth
- Database is a query layer that can be rebuilt
- Username-based foreign keys eliminate ID/username mismatches
- Regular archive-database consistency validation is essential