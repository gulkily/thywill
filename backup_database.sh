#!/bin/bash

# ThyWill Database Backup Script
# This script creates timestamped backups of the SQLite database

# Configuration
DB_PATH="/home/thywill/thywill/thywill.db"
BACKUP_DIR="/home/thywill/backups"
BACKUP_RETENTION_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="thywill_backup_${TIMESTAMP}.db"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Create backup
echo "Creating backup: $BACKUP_PATH"
cp "$DB_PATH" "$BACKUP_PATH"

# Verify backup was created
if [ -f "$BACKUP_PATH" ]; then
    echo "Backup created successfully: $BACKUP_PATH"
    
    # Get file size for verification
    ORIGINAL_SIZE=$(stat -c%s "$DB_PATH")
    BACKUP_SIZE=$(stat -c%s "$BACKUP_PATH")
    
    echo "Original size: $ORIGINAL_SIZE bytes"
    echo "Backup size: $BACKUP_SIZE bytes"
    
    if [ "$ORIGINAL_SIZE" -eq "$BACKUP_SIZE" ]; then
        echo "Backup verification: SUCCESS"
    else
        echo "Backup verification: FAILED - size mismatch"
        exit 1
    fi
else
    echo "Backup creation FAILED"
    exit 1
fi

# Clean up old backups (keep only last 30 days)
echo "Cleaning up backups older than $BACKUP_RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "thywill_backup_*.db" -type f -mtime +$BACKUP_RETENTION_DAYS -delete

# List current backups
echo "Current backups:"
ls -lah "$BACKUP_DIR"/thywill_backup_*.db 2>/dev/null | tail -10

echo "Backup process completed."