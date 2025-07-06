# Database Roundtrip Testing Plan

## Overview
Complete workflow for testing database export, backup, restore, and comparison to verify data integrity across the full backup/recovery pipeline. This plan uses ThyWill's dual archive system: text archives for prayer/user data and database exports for administrative data.

## Prerequisites
- ThyWill development environment setup
- Current database with test data
- Sufficient disk space for multiple database copies
- Access to all backup/restore commands

## Phase 1: Export Current Database to Archives

### Step 1.1: Create Complete Archive Export
```bash
# Export administrative data (sessions, invites, security logs, roles)
./thywill export-all

# Sync users to text archives (if not already current)
./thywill sync-users

# Create missing prayer archives (idempotent)
./thywill heal-archives

# Export active sessions separately for comparison
./thywill export-sessions

# Check both archive directories
ls -la text_archives/
ls -la text_archives/database_exports/
```

### Step 1.2: Validate Archive Quality
```bash
# Run comprehensive archive validation
./thywill validate-archives

# Run template validation
./validate_templates.py

# Check for any missing data or corruption
./thywill test-recovery --dry-run

# Verify archive-database consistency
./thywill validate-consistency
```

## Phase 2: Backup Current Database

### Step 2.1: Create Database Backup
```bash
# Create timestamped backup
./thywill backup

# List available backups to confirm creation
./thywill list

# Verify backup integrity
./thywill verify
```

### Step 2.2: Record Current State
```bash
# Document current database statistics
./thywill status > pre_restore_status.txt

# Count records in each table
sqlite3 thywill.db "SELECT name FROM sqlite_master WHERE type='table';" | while read table; do
    echo "$table: $(sqlite3 thywill.db "SELECT COUNT(*) FROM $table;")"
done > pre_restore_counts.txt
```

## Phase 3: Restore Brand New Database Copy

### Step 3.1: Create Clean Environment
```bash
# Backup current database file
cp thywill.db thywill_original.db

# Create fresh database
rm thywill.db
./thywill init

# Verify clean slate
./thywill status > post_init_status.txt
```

### Step 3.2: Restore from Archives
```bash
# Import prayer and user data from text archives
./thywill import text-archives --dry-run  # Preview changes first
./thywill import text-archives

# Import administrative data (sessions, invites, security, roles)
./thywill import-all --dry-run  # Preview changes first
./thywill import-all

# Run any necessary migrations
./thywill migrate

# Verify restoration completed
./thywill status > post_restore_status.txt
```

## Phase 4: Compare Database Copies

### Step 4.1: Statistical Comparison
```bash
# Count records in restored database
sqlite3 thywill.db "SELECT name FROM sqlite_master WHERE type='table';" | while read table; do
    echo "$table: $(sqlite3 thywill.db "SELECT COUNT(*) FROM $table;")"
done > post_restore_counts.txt

# Compare record counts
diff pre_restore_counts.txt post_restore_counts.txt
```

### Step 4.2: Data Integrity Verification
```bash
# Run archive validation on restored data
./thywill validate-archives

# Test recovery functionality
./thywill test-recovery

# Verify database consistency
./thywill validate-consistency
```

### Step 4.3: Detailed Data Comparison
```bash
# Export both databases to compare
cp thywill.db thywill_restored.db
cp thywill_original.db thywill.db

# Create comparison exports from original database
mkdir comparison_test/original
./thywill export-all
cp -r text_archives/database_exports/* comparison_test/original/
./thywill export-sessions
cp sessions_backup.json comparison_test/original/

# Export from restored database
cp thywill_restored.db thywill.db
mkdir comparison_test/restored
./thywill export-all
cp -r text_archives/database_exports/* comparison_test/restored/
./thywill export-sessions
cp sessions_backup.json comparison_test/restored/

# Compare export contents
diff -r comparison_test/original/ comparison_test/restored/

# Compare text archives (prayer and user data)
./thywill validate-archives  # Validates against current database
```

## Phase 5: Verification and Cleanup

### Step 5.1: Functional Testing
```bash
# Test key application functions
./thywill test --markers="integration"

# Verify authentication works
# Verify prayer creation/retrieval works
# Verify archive downloads work
```

### Step 5.2: Performance Comparison
```bash
# Compare database file sizes
ls -lh thywill_original.db thywill_restored.db

# Check query performance on both databases
# Run timing tests on common operations
```

### Step 5.3: Cleanup
```bash
# Restore original database
cp thywill_original.db thywill.db

# Archive test results
mkdir test_results_$(date +%Y%m%d_%H%M%S)
mv *_status.txt *_counts.txt comparison_test test_results_*/

# Clean up temporary files
rm thywill_restored.db thywill_original.db
```

## Success Criteria

### Data Integrity
- [ ] All record counts match between original and restored databases
- [ ] No differences in archive file contents
- [ ] All validation checks pass on restored database
- [ ] Functional tests pass on restored database

### Process Verification
- [ ] Export process completes without errors
- [ ] Backup creation succeeds and verifies
- [ ] Import process completes without errors
- [ ] No data loss or corruption detected

## Expected Outcomes

### Positive Results
- Identical record counts across all tables
- No differences in exported archive contents
- All validation tests pass
- Functional tests complete successfully

### Potential Issues
- **Missing Data**: Some records not exported/imported correctly
- **Schema Differences**: Database structure changes during process
- **Performance Degradation**: Restored database slower than original
- **Archive Corruption**: Validation failures on restored archives

## Troubleshooting

### Common Issues
1. **Export Failures**: Check disk space, permissions, database locks
2. **Import Errors**: Verify archive integrity, check migration status
3. **Validation Failures**: Compare archive formats, check data consistency
4. **Performance Issues**: Analyze database indexes, query plans

### Recovery Steps
1. Restore from database backup if archive process fails
2. Re-run export with verbose logging for diagnostics
3. Use partial import commands to isolate problematic data
4. Contact support with detailed error logs

## Notes

- This process tests the complete backup/recovery pipeline using ThyWill's dual archive system
- **Text Archives**: Prayer data, user data, activity logs (automatic creation)
- **Database Exports**: Sessions, invites, security logs, roles, auth data (export-all/import-all)
- **Traditional Backups**: SQLite database file copies
- Validates both archive systems and database backup methods
- Provides confidence in disaster recovery procedures
- Should be run before any major system changes
- Results should be documented for future reference

## Archive System Architecture

ThyWill uses a dual archive approach:

1. **Text Archives** (`text_archives/`):
   - Prayers and user data automatically archived
   - Human-readable format with pipe-separated values
   - Monthly organization for large datasets
   - Imported via `import text-archives`

2. **Database Exports** (`text_archives/database_exports/`):
   - Administrative data: sessions, invites, security, roles
   - Exported via `export-all`, imported via `import-all`
   - Organized by data type and date
   - Fully idempotent operations

## Related Documentation
- `docs/plans/backup_export_import_features.md`
- `docs/plans/backup_deprecation_catalog.md`
- Archive validation scripts and procedures