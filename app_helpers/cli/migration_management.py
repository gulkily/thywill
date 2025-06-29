#!/usr/bin/env python3
"""
Migration Management CLI Module

Handles database migration status, rollback, and management operations.
Can be run independently or called from the CLI script.
"""

import sys
from typing import List, Dict, Any, Optional
from app_helpers.utils.enhanced_migration import MigrationManager


def get_migration_status() -> Dict[str, Any]:
    """
    Get comprehensive migration status information.
    
    Returns:
        Dict containing migration status details
    """
    try:
        manager = MigrationManager()
        
        status = {
            'current_version': manager.get_current_version(),
            'applied_migrations': manager.get_applied_migrations(),
            'pending_migrations': [],
            'schema_integrity': manager.validate_schema_integrity()
        }
        
        # Get detailed pending migration info
        pending = manager.get_pending_migrations()
        for migration in pending:
            metadata = migration['metadata']
            estimated_time = manager.estimate_migration_time(migration)
            maintenance_mode = manager.should_enable_maintenance_mode(migration)
            
            status['pending_migrations'].append({
                'id': migration['id'],
                'description': metadata.get('description', 'No description'),
                'estimated_time': estimated_time,
                'requires_maintenance': maintenance_mode
            })
        
        return status
        
    except Exception as e:
        raise RuntimeError(f"Error getting migration status: {e}")


def print_migration_status():
    """Print formatted migration status report."""
    print('📊 Migration Status')
    print('=' * 25)
    print()
    
    try:
        status = get_migration_status()
        
        # Current version
        if status['current_version']:
            print(f'📊 Current schema version: {status["current_version"]}')
        else:
            print('📊 No migrations applied yet')
        
        # Applied migrations
        applied = status['applied_migrations']
        if applied:
            print(f'✅ Applied migrations ({len(applied)}):')
            for migration in applied:
                print(f'   - {migration}')
        else:
            print('ℹ️  No migrations applied yet')
        
        print()
        
        # Pending migrations
        pending = status['pending_migrations']
        if pending:
            print(f'⏳ Pending migrations ({len(pending)}):')
            for migration in pending:
                print(f'   - {migration["id"]}')
                print(f'     Description: {migration["description"]}')
                print(f'     Estimated time: {migration["estimated_time"]}s')
                if migration['requires_maintenance']:
                    print(f'     ⚠️  Requires maintenance mode')
                print()
        else:
            print('✅ No pending migrations - database is up to date')
        
        # Schema integrity
        print('🔍 Schema integrity check:')
        if status['schema_integrity']:
            print('   ✅ Database integrity verified')
        else:
            print('   ❌ Database integrity check failed')
            
    except Exception as e:
        print(f'❌ Error checking migration status: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    return True


def get_last_migration() -> Optional[str]:
    """
    Get the ID of the last applied migration.
    
    Returns:
        Migration ID or None if no migrations applied
    """
    try:
        manager = MigrationManager()
        return manager.get_current_version()
    except:
        return None


def rollback_migration(migration_id: Optional[str] = None, confirm: bool = True) -> bool:
    """
    Rollback a specific migration or the last applied one.
    
    Args:
        migration_id: Specific migration to rollback, or None for last
        confirm: Whether to ask for confirmation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        manager = MigrationManager()
        
        # Get migration ID if not specified
        if not migration_id:
            migration_id = get_last_migration()
            
            if not migration_id:
                print("❌ No migrations found to rollback")
                print("Use 'thywill migrate status' to see applied migrations")
                return False
            
            print(f"🔍 Found last migration: {migration_id}")
            
            if confirm:
                response = input("Rollback this migration? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("⚠️  Rollback cancelled")
                    return True  # Not an error, user chose to cancel
        
        print(f"🔄 Rolling back migration: {migration_id}")
        
        # Perform rollback
        success = manager.rollback_migration(migration_id)
        
        if success:
            print(f"✅ Migration {migration_id} rolled back successfully")
            
            # Show new status
            new_version = manager.get_current_version()
            if new_version:
                print(f"📊 Current schema version: {new_version}")
            else:
                print("📊 All migrations rolled back - database at initial state")
            
            return True
        else:
            print(f"❌ Failed to rollback migration {migration_id}")
            return False
            
    except Exception as e:
        print(f'❌ Error rolling back migration: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point when run as a standalone script."""
    if len(sys.argv) < 2:
        print("Usage: python migration_management.py [status|rollback] [migration_id]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        if print_migration_status():
            sys.exit(0)
        else:
            sys.exit(1)
            
    elif command == "rollback":
        migration_id = sys.argv[2] if len(sys.argv) > 2 else None
        
        print("🔄 Rolling Back Migration")
        print("=" * 30)
        
        if rollback_migration(migration_id):
            sys.exit(0)
        else:
            sys.exit(1)
            
    elif command == "get-current-version":
        # Simple command to get current version (used by CLI script)
        version = get_last_migration()
        if version:
            print(version)
        # Don't print anything if no version - just exit
        sys.exit(0)
            
    else:
        print(f"Unknown command: {command}")
        print("Usage: python migration_management.py [status|rollback|get-current-version] [migration_id]")
        sys.exit(1)


if __name__ == '__main__':
    main()