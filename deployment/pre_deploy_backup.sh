#!/bin/bash

# Pre-deployment backup script
# Run this BEFORE any deployment to production

echo "=== PRE-DEPLOYMENT BACKUP ==="
echo "Creating backup before deployment..."

# Get the project root directory (parent of deployment/)
PROJECT_ROOT=$(dirname "$(dirname "$(realpath "$0")")")

# Run the main backup script from deployment directory
"$PROJECT_ROOT/deployment/backup_database.sh"

if [ $? -eq 0 ]; then
    echo "Pre-deployment backup completed successfully."
    echo "Safe to proceed with deployment."
else
    echo "PRE-DEPLOYMENT BACKUP FAILED!"
    echo "DO NOT PROCEED WITH DEPLOYMENT until backup succeeds."
    exit 1
fi