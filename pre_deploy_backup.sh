#!/bin/bash

# Pre-deployment backup script
# Run this BEFORE any deployment to production

echo "=== PRE-DEPLOYMENT BACKUP ==="
echo "Creating backup before deployment..."

# Run the main backup script
./backup_database.sh

if [ $? -eq 0 ]; then
    echo "Pre-deployment backup completed successfully."
    echo "Safe to proceed with deployment."
else
    echo "PRE-DEPLOYMENT BACKUP FAILED!"
    echo "DO NOT PROCEED WITH DEPLOYMENT until backup succeeds."
    exit 1
fi