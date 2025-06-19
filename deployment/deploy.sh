#!/bin/bash

# ThyWill Deployment Script with Rollback Support
# This script handles safe deployment with automatic rollback on failure

set -euo pipefail

# Configuration
APP_DIR="/home/thywill/thywill"
BACKUP_DIR="/home/thywill/backups"
DEPLOY_LOG_DIR="/home/thywill/deploy_logs"
SERVICE_NAME="thywill"
HEALTH_CHECK_URL="http://127.0.0.1:8000/health"
ROLLBACK_TIMEOUT=60  # seconds to wait before rollback on failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$DEPLOY_LOG"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$DEPLOY_LOG"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$DEPLOY_LOG"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$DEPLOY_LOG"
}

# Create directories
mkdir -p "$BACKUP_DIR" "$DEPLOY_LOG_DIR"

# Setup deployment log
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DEPLOY_LOG="$DEPLOY_LOG_DIR/deploy_${TIMESTAMP}.log"

log "Starting deployment process..."

# Step 1: Pre-deployment backup
log "Step 1: Creating pre-deployment backup..."
if ! ./pre_deploy_backup.sh; then
    error "Pre-deployment backup failed! Aborting deployment."
    exit 1
fi

BACKUP_NAME="thywill_backup_${TIMESTAMP}.db"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Step 2: Create code snapshot
log "Step 2: Creating code snapshot..."
CODE_BACKUP_DIR="${BACKUP_DIR}/code_${TIMESTAMP}"
mkdir -p "$CODE_BACKUP_DIR"
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    "$APP_DIR/" "$CODE_BACKUP_DIR/" >> "$DEPLOY_LOG" 2>&1

# Step 3: Stop service
log "Step 3: Stopping application service..."
sudo systemctl stop "$SERVICE_NAME"
if [ $? -eq 0 ]; then
    success "Service stopped successfully"
else
    error "Failed to stop service"
    exit 1
fi

# Step 4: Update application code (this would be git pull in real deployment)
log "Step 4: Application code is already updated (assuming git pull was done)"

# Step 5: Install/update dependencies
log "Step 5: Installing dependencies..."
cd "$APP_DIR"
source venv/bin/activate
pip install -r requirements.txt >> "$DEPLOY_LOG" 2>&1

# Step 6: Run enhanced database migrations
log "Step 6: Running enhanced database migrations..."

# Acquire migration lock and estimate migration time
log "Checking pending migrations..."
MIGRATION_OUTPUT=$(./thywill migrate status 2>&1)
log "$MIGRATION_OUTPUT"

# Check if any migrations require maintenance mode
if echo "$MIGRATION_OUTPUT" | grep -q "Requires maintenance mode"; then
    warning "Some migrations require maintenance mode"
    log "Running migrations with service stopped..."
    
    # Run migrations while service is stopped
    if ! ./thywill migrate new >> "$DEPLOY_LOG" 2>&1; then
        error "Enhanced migrations failed! Attempting rollback..."
        
        # Try legacy migrations as fallback
        log "Attempting legacy migration fallback..."
        if ! ./thywill migrate legacy >> "$DEPLOY_LOG" 2>&1; then
            error "Legacy migration fallback also failed!"
            # The rollback process will handle database restoration
            exit 1
        else
            success "Legacy migration fallback completed"
        fi
    else
        success "Enhanced migrations completed successfully"
    fi
else
    log "No maintenance mode required, migrations will run during startup"
    # Migrations will be handled automatically by application startup
    # But we can still run them here for immediate feedback
    if ! ./thywill migrate new >> "$DEPLOY_LOG" 2>&1; then
        warning "Enhanced migrations failed, will rely on startup migrations"
        log "Service will attempt migrations during startup"
    else
        success "Enhanced migrations completed successfully"
    fi
fi

# Step 7: Start service
log "Step 7: Starting application service..."
sudo systemctl start "$SERVICE_NAME"

# Step 8: Health check with timeout
log "Step 8: Performing health check..."
HEALTH_CHECK_PASSED=false

for i in {1..30}; do
    sleep 2
    log "Health check attempt $i/30..."
    
    if curl -f -s "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
        HEALTH_CHECK_PASSED=true
        success "Health check passed!"
        break
    fi
done

if [ "$HEALTH_CHECK_PASSED" = false ]; then
    error "Health check failed! Initiating rollback..."
    
    # Rollback process
    log "ROLLBACK: Stopping failed deployment..."
    sudo systemctl stop "$SERVICE_NAME"
    
    log "ROLLBACK: Attempting migration-based rollback first..."
    cd "$APP_DIR"
    
    # Try migration rollback first
    if ./thywill migrate rollback >> "$DEPLOY_LOG" 2>&1; then
        success "ROLLBACK: Migration rollback completed"
    else
        warning "ROLLBACK: Migration rollback failed, using database file restore"
        log "ROLLBACK: Restoring database backup..."
        cp "$BACKUP_PATH" "${APP_DIR}/thywill.db"
    fi
    
    log "ROLLBACK: Restoring code snapshot..."
    rsync -av --delete "$CODE_BACKUP_DIR/" "$APP_DIR/" >> "$DEPLOY_LOG" 2>&1
    
    log "ROLLBACK: Reinstalling previous dependencies..."
    cd "$APP_DIR"
    source venv/bin/activate
    pip install -r requirements.txt >> "$DEPLOY_LOG" 2>&1
    
    log "ROLLBACK: Starting service with previous version..."
    sudo systemctl start "$SERVICE_NAME"
    
    # Verify rollback worked
    sleep 5
    if curl -f -s "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
        success "ROLLBACK: Service restored successfully"
        warning "Deployment failed but rollback completed. Check logs at: $DEPLOY_LOG"
        exit 1
    else
        error "ROLLBACK FAILED! Manual intervention required!"
        error "Backup location: $BACKUP_PATH"
        error "Code backup: $CODE_BACKUP_DIR"
        exit 2
    fi
else
    success "Deployment completed successfully!"
    log "Cleaning up old backups and logs..."
    
    # Keep only last 10 deployment logs
    ls -t "$DEPLOY_LOG_DIR"/deploy_*.log | tail -n +11 | xargs -r rm
    
    # Keep only last 30 days of code backups
    find "$BACKUP_DIR" -name "code_*" -type d -mtime +30 -exec rm -rf {} +
    
    success "Deployment and cleanup completed!"
fi

log "Deployment process finished. Log saved to: $DEPLOY_LOG"