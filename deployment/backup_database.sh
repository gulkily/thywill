#!/bin/bash

# ThyWill Database Backup Script
# This script creates timestamped backups of the SQLite database

# Get the project root directory (parent of deployment/)
PROJECT_ROOT=$(dirname "$(dirname "$(realpath "$0")")")

# Configuration - Use environment-aware paths
if [ -f "$PROJECT_ROOT/thywill.db" ]; then
    DB_PATH="$PROJECT_ROOT/thywill.db"
elif [ -f "/home/thywill/thywill/thywill.db" ]; then
    DB_PATH="/home/thywill/thywill/thywill.db"
else
    echo "ERROR: Could not find thywill.db database file"
    echo "Searched in:"
    echo "  - $PROJECT_ROOT/thywill.db" 
    echo "  - /home/thywill/thywill/thywill.db"
    exit 1
fi

# Set backup directory based on environment
# On production, use /home/thywill/backups if it exists and is writable
if [ -d "/home/thywill/backups" ] && [ -w "/home/thywill/backups" ]; then
    BACKUP_DIR="/home/thywill/backups"
else
    # Use local project backup directory
    BACKUP_DIR="$PROJECT_ROOT/backups"
fi

BACKUP_RETENTION_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="thywill_backup_${TIMESTAMP}.db"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Create backup
echo "Creating backup: $BACKUP_PATH"
echo "Source database: $DB_PATH"

# Check if source database exists and is readable
if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database file not found: $DB_PATH"
    exit 1
fi

if [ ! -r "$DB_PATH" ]; then
    echo "ERROR: Cannot read database file: $DB_PATH"
    exit 1
fi

# Create the backup using cp (simple and reliable)
if cp "$DB_PATH" "$BACKUP_PATH"; then
    echo "Backup created successfully!"
    
    # Verify backup file size matches original
    ORIGINAL_SIZE=$(stat -c%s "$DB_PATH" 2>/dev/null || echo "0")
    BACKUP_SIZE=$(stat -c%s "$BACKUP_PATH" 2>/dev/null || echo "0")
    
    if [ "$ORIGINAL_SIZE" -eq "$BACKUP_SIZE" ] && [ "$ORIGINAL_SIZE" -gt "0" ]; then
        echo "Backup verification successful (size: $BACKUP_SIZE bytes)"
    else
        echo "WARNING: Backup size verification failed"
        echo "Original: $ORIGINAL_SIZE bytes, Backup: $BACKUP_SIZE bytes"
        exit 1
    fi
    
    # Clean up old backups
    echo "Cleaning up backups older than $BACKUP_RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "thywill_backup_*.db" -mtime +$BACKUP_RETENTION_DAYS -delete 2>/dev/null || true
    
    echo "Backup process completed successfully!"
    exit 0
else
    echo "ERROR: Failed to create backup!"
    exit 1
fi