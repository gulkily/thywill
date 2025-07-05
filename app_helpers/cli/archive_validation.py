#!/usr/bin/env python3
"""
Archive Validation CLI Module

Handles archive validation, testing, and repair operations.
Can be run independently or called from the CLI script.
"""

import sys
import os
import subprocess
from typing import Dict, Any, List


def validate_archives() -> bool:
    """
    Validate archive structure and data integrity.
    
    Returns:
        True if validation passes, False otherwise
    """
    try:
        from app_helpers.services.database_recovery import CompleteSystemRecovery
        
        recovery = CompleteSystemRecovery('text_archives')
        print('🔍 Validating archive structure...')
        recovery._validate_archive_structure()
        
        print('📊 Archive Structure Report:')
        print('=' * 50)
        
        # Check core directories
        core_dirs = ['prayers', 'users', 'activity']
        for dir_name in core_dirs:
            path = recovery.archive_dir / dir_name
            if path.exists():
                file_count = len(list(path.glob('*.txt')))
                print(f'✅ {dir_name}/: {file_count} files')
            else:
                print(f'❌ {dir_name}/: missing')
        
        # Check new directories
        new_dirs = ['auth', 'roles', 'system']
        for dir_name in new_dirs:
            path = recovery.archive_dir / dir_name
            if path.exists():
                file_count = len(list(path.rglob('*.txt')))
                print(f'✅ {dir_name}/: {file_count} files')
            else:
                print(f'⚠️  {dir_name}/: not found (will use defaults)')
        
        print()
        print('📋 Validation complete!')
        print('💡 Use "thywill test-recovery" to simulate recovery')
        return True
        
    except Exception as e:
        print(f'❌ Validation failed: {e}')
        return False


def test_recovery() -> bool:
    """
    Test recovery capabilities by simulating recovery process.
    
    Returns:
        True if test passes, False otherwise
    """
    try:
        from app_helpers.services.database_recovery import CompleteSystemRecovery
        
        recovery = CompleteSystemRecovery('text_archives')
        result = recovery.perform_complete_recovery(dry_run=True)
        
        if result['success']:
            print('🎉 Recovery simulation completed successfully!')
            print()
            print('📊 Recovery Statistics:')
            print('=' * 50)
            stats = result['stats']
            for key, value in stats.items():
                if isinstance(value, int) and value > 0:
                    print(f'{key.replace("_", " ").title()}: {value}')
            
            if stats.get('warnings'):
                print()
                print('⚠️  Warnings:')
                for warning in stats['warnings']:
                    print(f'  • {warning}')
            
            if stats.get('errors'):
                print()
                print('❌ Errors:')
                for error in stats['errors']:
                    print(f'  • {error}')
            
            print()
            print('💡 Use "thywill full-recovery" to perform actual recovery')
            return True
        else:
            print(f'❌ Recovery simulation failed: {result.get("error", "Unknown error")}')
            return False
            
    except Exception as e:
        print(f'❌ Recovery simulation failed: {e}')
        import traceback
        traceback.print_exc()
        return False


def repair_archives() -> bool:
    """
    Repair archive inconsistencies and missing files.
    
    Returns:
        True if repair succeeds, False otherwise
    """
    print("🔧 Repairing Archive Issues")
    print("=" * 30)
    
    try:
        # Use existing archive healing functionality
        result = subprocess.run([sys.executable, "-c", """
import sys
sys.path.append('.')

try:
    print('🔧 Repairing archive structure...')
    
    # This would call existing archive repair logic
    # For now, we'll use the heal_prayer_archives script
    import subprocess
    import os
    
    if os.path.exists('scripts/utils/heal_prayer_archives.py'):
        print('📁 Running archive healing script...')
        env = os.environ.copy()
        env['PYTHONPATH'] = '.'
        heal_result = subprocess.run([sys.executable, 'scripts/utils/heal_prayer_archives.py'], 
                                   check=True, capture_output=True, text=True, env=env)
        print(heal_result.stdout)
        if heal_result.stderr:
            print(heal_result.stderr)
    else:
        print('⚠️  Archive healing script not found')
        print('   Creating basic archive structure...')
        
        # Create basic archive directories
        from pathlib import Path
        base_dir = Path('text_archives')
        base_dir.mkdir(exist_ok=True)
        
        for subdir in ['prayers', 'users', 'activity']:
            (base_dir / subdir).mkdir(exist_ok=True)
        
        print(f'✅ Created archive directories in {base_dir}')
    
    print()
    print('✅ Archive repair completed')
    
except Exception as e:
    print(f'❌ Archive repair failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""], check=True, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Archive repair failed: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return False


def full_recovery() -> bool:
    """
    Perform complete database recovery from archives.
    
    Returns:
        True if recovery succeeds, False otherwise
    """
    try:
        from app_helpers.services.database_recovery import CompleteSystemRecovery
        
        recovery = CompleteSystemRecovery('text_archives')
        result = recovery.perform_complete_recovery(dry_run=False)
        
        if result['success']:
            print('🎉 Complete database recovery finished successfully!')
            print()
            print('📊 Recovery Results:')
            print('=' * 50)
            stats = result['stats']
            for key, value in stats.items():
                if isinstance(value, int) and value > 0:
                    print(f'{key.replace("_", " ").title()}: {value}')
            
            if stats.get('warnings'):
                print()
                print('⚠️  Warnings:')
                for warning in stats['warnings']:
                    print(f'  • {warning}')
            
            if stats.get('errors'):
                print()
                print('❌ Errors:')
                for error in stats['errors']:
                    print(f'  • {error}')
            
            print()
            print('✅ Database reconstruction complete!')
            print('💡 Test your application to ensure everything is working correctly')
            return True
        else:
            print(f'❌ Recovery failed: {result.get("error", "Unknown error")}')
            return False
            
    except Exception as e:
        print(f'❌ Recovery failed: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point when run as a standalone script."""
    if len(sys.argv) < 2:
        print("Usage: python archive_validation.py [validate|test-recovery|full-recovery|repair]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "validate":
        if validate_archives():
            sys.exit(0)
        else:
            sys.exit(1)
            
    elif command == "test-recovery":
        if test_recovery():
            sys.exit(0)
        else:
            sys.exit(1)
            
    elif command == "full-recovery":
        if full_recovery():
            sys.exit(0)
        else:
            sys.exit(1)
            
    elif command == "repair":
        if repair_archives():
            sys.exit(0)
        else:
            sys.exit(1)
            
    else:
        print(f"Unknown command: {command}")
        print("Usage: python archive_validation.py [validate|test-recovery|full-recovery|repair]")
        sys.exit(1)


if __name__ == '__main__':
    main()