#!/usr/bin/env python3
"""
Migration Runner CLI Module

Handles running new migrations and migration-related operations.
Can be run independently or called from the CLI script.
"""

import sys
import os
import subprocess
from typing import Dict, Any, List


def run_new_migrations() -> bool:
    """
    Run new migrations using the enhanced migration system.
    
    Returns:
        True if successful, False otherwise
    """
    print("🚀 Running New Migrations")
    print("=" * 30)
    
    try:
        # Use the existing enhanced migration manager
        result = subprocess.run([sys.executable, "-c", """
import sys
sys.path.append('.')
from app_helpers.utils.enhanced_migration import MigrationManager

try:
    manager = MigrationManager()
    
    # Check for pending migrations
    pending = manager.get_pending_migrations()
    
    if not pending:
        print('✅ No pending migrations - database is up to date')
        sys.exit(0)
    
    print(f'📋 Found {len(pending)} pending migration(s):')
    for migration in pending:
        metadata = migration['metadata']
        print(f'   - {migration["id"]}: {metadata.get("description", "No description")}')
    
    print()
    
    # Run all pending migrations
    if not manager.acquire_migration_lock():
        print('❌ Could not acquire migration lock - another migration may be in progress')
        sys.exit(1)
    
    try:
        success_count = 0
        for migration in pending:
            migration_id = migration['id']
            print(f'🔄 Running migration: {migration_id}')
            
            if manager.run_migration(migration_id):
                print(f'✅ Migration {migration_id} completed successfully')
                success_count += 1
            else:
                print(f'❌ Migration {migration_id} failed')
                break
        
        if success_count == len(pending):
            print()
            print(f'🎉 All {success_count} migrations completed successfully!')
            current_version = manager.get_current_version()
            print(f'📊 Current schema version: {current_version}')
        else:
            print(f'⚠️  Only {success_count}/{len(pending)} migrations completed')
            sys.exit(1)
        
    finally:
        manager.release_migration_lock()
    
except Exception as e:
    print(f'❌ Migration failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""], check=True, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return False


def run_legacy_migrations() -> bool:
    """
    Run legacy migrations for backward compatibility.
    
    Returns:
        True if successful, False otherwise
    """
    print("🔄 Running Legacy Migrations")
    print("=" * 32)
    
    try:
        # Check if legacy migration scripts exist
        legacy_scripts = [
            'scripts/migration/migrate_to_roles.py',
            'migrations/duplicate_user_migration.py'
        ]
        
        available_scripts = [script for script in legacy_scripts if os.path.exists(script)]
        
        if not available_scripts:
            print('ℹ️  No legacy migration scripts found')
            print('   Database may already be migrated or scripts not present')
            return True
        
        print(f'📋 Found {len(available_scripts)} legacy migration script(s):')
        for script in available_scripts:
            print(f'   - {script}')
        
        print()
        
        # Run each available script
        for script in available_scripts:
            print(f'🔄 Running: {script}')
            
            try:
                result = subprocess.run([sys.executable, script], 
                                      check=True, capture_output=True, text=True)
                print(f'✅ {script} completed successfully')
                if result.stdout:
                    print(result.stdout)
                    
            except subprocess.CalledProcessError as e:
                print(f'❌ {script} failed: {e}')
                if e.stdout:
                    print(e.stdout)
                if e.stderr:
                    print(e.stderr, file=sys.stderr)
                return False
        
        print()
        print('🎉 All legacy migrations completed!')
        
        return True
        
    except Exception as e:
        print(f"❌ Legacy migration failed: {e}")
        return False


def main():
    """Main entry point when run as a standalone script."""
    if len(sys.argv) < 2:
        print("Usage: python migration_runner.py [new|legacy]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "new":
        if run_new_migrations():
            sys.exit(0)
        else:
            sys.exit(1)
            
    elif command == "legacy":
        if run_legacy_migrations():
            sys.exit(0)
        else:
            sys.exit(1)
            
    else:
        print(f"Unknown command: {command}")
        print("Usage: python migration_runner.py [new|legacy]")
        sys.exit(1)


if __name__ == '__main__':
    main()