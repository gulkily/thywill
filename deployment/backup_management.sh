#!/bin/bash

# Advanced Backup Management Script for ThyWill
# Provides multiple backup strategies and restore capabilities

set -euo pipefail

# Configuration
DB_PATH="/home/thywill/thywill/thywill.db"
BACKUP_DIR="/home/thywill/backups"
REMOTE_BACKUP_DIR="/home/thywill/remote_backups"  # Could be mounted network drive
BACKUP_RETENTION_DAYS=30
HOURLY_RETENTION_HOURS=48
DAILY_RETENTION_DAYS=30
WEEKLY_RETENTION_WEEKS=12

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Create backup directories
mkdir -p "$BACKUP_DIR/hourly" "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly" "$REMOTE_BACKUP_DIR"

create_backup() {
    local backup_type="$1"
    local backup_subdir="$2"
    
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="thywill_${backup_type}_${timestamp}.db"
    local backup_path="${BACKUP_DIR}/${backup_subdir}/${backup_file}"
    
    log "Creating $backup_type backup: $backup_file"
    
    # Create backup with integrity check
    if sqlite3 "$DB_PATH" ".backup '$backup_path'"; then
        # Verify backup integrity
        if sqlite3 "$backup_path" "PRAGMA integrity_check;" | grep -q "ok"; then
            success "$backup_type backup created and verified: $backup_path"
            
            # Create checksum
            sha256sum "$backup_path" > "${backup_path}.sha256"
            
            # Copy to remote backup if directory exists and is writable
            if [ -w "$REMOTE_BACKUP_DIR" ]; then
                cp "$backup_path" "$REMOTE_BACKUP_DIR/"
                cp "${backup_path}.sha256" "$REMOTE_BACKUP_DIR/"
                info "Backup copied to remote location"
            fi
            
            echo "$backup_path"
        else
            error "Backup integrity check failed for $backup_path"
            rm -f "$backup_path"
            return 1
        fi
    else
        error "Failed to create $backup_type backup"
        return 1
    fi
}

cleanup_backups() {
    info "Cleaning up old backups..."
    
    # Cleanup hourly backups (keep last 48 hours)
    find "$BACKUP_DIR/hourly" -name "thywill_hourly_*.db" -type f -mtime +2 -delete
    find "$BACKUP_DIR/hourly" -name "thywill_hourly_*.db.sha256" -type f -mtime +2 -delete
    
    # Cleanup daily backups (keep last 30 days)
    find "$BACKUP_DIR/daily" -name "thywill_daily_*.db" -type f -mtime +$DAILY_RETENTION_DAYS -delete
    find "$BACKUP_DIR/daily" -name "thywill_daily_*.db.sha256" -type f -mtime +$DAILY_RETENTION_DAYS -delete
    
    # Cleanup weekly backups (keep last 12 weeks = 84 days)
    find "$BACKUP_DIR/weekly" -name "thywill_weekly_*.db" -type f -mtime +84 -delete
    find "$BACKUP_DIR/weekly" -name "thywill_weekly_*.db.sha256" -type f -mtime +84 -delete
    
    # Cleanup remote backups
    if [ -w "$REMOTE_BACKUP_DIR" ]; then
        find "$REMOTE_BACKUP_DIR" -name "thywill_*.db" -type f -mtime +$BACKUP_RETENTION_DAYS -delete
        find "$REMOTE_BACKUP_DIR" -name "thywill_*.db.sha256" -type f -mtime +$BACKUP_RETENTION_DAYS -delete
    fi
    
    success "Backup cleanup completed"
}

list_backups() {
    info "Available backups:"
    
    echo -e "\n${BLUE}Hourly backups (last 48 hours):${NC}"
    ls -lah "$BACKUP_DIR/hourly"/thywill_hourly_*.db 2>/dev/null | tail -10 || echo "No hourly backups found"
    
    echo -e "\n${BLUE}Daily backups (last 30 days):${NC}"
    ls -lah "$BACKUP_DIR/daily"/thywill_daily_*.db 2>/dev/null | tail -10 || echo "No daily backups found"
    
    echo -e "\n${BLUE}Weekly backups (last 12 weeks):${NC}"
    ls -lah "$BACKUP_DIR/weekly"/thywill_weekly_*.db 2>/dev/null | tail -10 || echo "No weekly backups found"
    
    if [ -d "$REMOTE_BACKUP_DIR" ] && [ "$(ls -A $REMOTE_BACKUP_DIR)" ]; then
        echo -e "\n${BLUE}Remote backups:${NC}"
        ls -lah "$REMOTE_BACKUP_DIR"/thywill_*.db 2>/dev/null | tail -10 || echo "No remote backups found"
    fi
}

restore_backup() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Verify backup integrity before restore
    if ! sqlite3 "$backup_file" "PRAGMA integrity_check;" | grep -q "ok"; then
        error "Backup file is corrupted: $backup_file"
        return 1
    fi
    
    # Verify checksum if available
    if [ -f "${backup_file}.sha256" ]; then
        if ! sha256sum -c "${backup_file}.sha256" > /dev/null 2>&1; then
            error "Backup checksum verification failed: $backup_file"
            return 1
        fi
        info "Backup checksum verified"
    fi
    
    warning "This will overwrite the current database!"
    read -p "Are you sure you want to restore from $backup_file? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Create a backup of current database before restore
        local pre_restore_backup="${BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S).db"
        cp "$DB_PATH" "$pre_restore_backup"
        info "Current database backed up to: $pre_restore_backup"
        
        # Stop service before restore
        sudo systemctl stop thywill
        
        # Restore database
        cp "$backup_file" "$DB_PATH"
        
        # Start service
        sudo systemctl start thywill
        
        success "Database restored from: $backup_file"
        info "Previous database saved as: $pre_restore_backup"
    else
        info "Restore cancelled"
    fi
}

case "${1:-}" in
    "hourly")
        create_backup "hourly" "hourly"
        cleanup_backups
        ;;
    "daily")
        create_backup "daily" "daily"
        cleanup_backups
        ;;
    "weekly")
        create_backup "weekly" "weekly"
        cleanup_backups
        ;;
    "list")
        list_backups
        ;;
    "restore")
        if [ -z "${2:-}" ]; then
            error "Please provide backup file path"
            echo "Usage: $0 restore /path/to/backup.db"
            exit 1
        fi
        restore_backup "$2"
        ;;
    "cleanup")
        cleanup_backups
        ;;
    *)
        echo "ThyWill Backup Management Script"
        echo "Usage: $0 {hourly|daily|weekly|list|restore|cleanup}"
        echo ""
        echo "Commands:"
        echo "  hourly   - Create hourly backup"
        echo "  daily    - Create daily backup"
        echo "  weekly   - Create weekly backup"
        echo "  list     - List all available backups"
        echo "  restore  - Restore from backup file"
        echo "  cleanup  - Clean up old backups"
        echo ""
        echo "Examples:"
        echo "  $0 daily"
        echo "  $0 list"
        echo "  $0 restore /home/thywill/backups/daily/thywill_daily_20231201_120000.db"
        exit 1
        ;;
esac