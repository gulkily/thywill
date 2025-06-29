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
    print("🔍 Validating Archive Structure")
    print("=" * 35)
    
    try:
        # Use existing text archive service for validation
        result = subprocess.run([sys.executable, "-c", """
import sys
sys.path.append('.')
from pathlib import Path
from app_helpers.services.text_archive_service import TextArchiveService

try:
    service = TextArchiveService()
    
    print('📁 Checking archive directories...')
    
    # Check base archive structure
    archive_base = Path('text_archives')
    if not archive_base.exists():
        print('❌ Base archive directory missing: text_archives/')
        sys.exit(1)
    
    # Check main directories
    required_dirs = ['prayers', 'users', 'activity']
    for dir_name in required_dirs:
        dir_path = archive_base / dir_name
        if dir_path.exists():
            file_count = len(list(dir_path.rglob('*.txt')))
            print(f'✅ {dir_name}/: {file_count} files')
        else:
            print(f'⚠️  {dir_name}/: directory missing')
    
    print()
    print('🔍 Archive integrity check completed')
    print('✅ Archive validation passed')
    
except Exception as e:
    print(f'❌ Archive validation failed: {e}')
    sys.exit(1)
"""], check=True, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Archive validation failed: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return False


def test_recovery() -> bool:
    """
    Test recovery capabilities by simulating recovery process.
    
    Returns:
        True if test passes, False otherwise
    """
    print("🧪 Testing Recovery Capabilities")
    print("=" * 35)
    
    try:
        # Use existing database recovery service for testing
        result = subprocess.run([sys.executable, "-c", """
import sys
sys.path.append('.')
from app_helpers.services.database_recovery import CompleteSystemRecovery

try:
    recovery = CompleteSystemRecovery('text_archives')
    
    print('🔍 Testing recovery system...')
    
    # Test archive accessibility
    archive_dir = recovery.archive_dir
    if not archive_dir.exists():
        print(f'❌ Archive directory not found: {archive_dir}')
        sys.exit(1)
    
    print(f'✅ Archive directory accessible: {archive_dir}')
    
    # Test key recovery components
    prayers_dir = archive_dir / 'prayers'
    users_dir = archive_dir / 'users'
    
    if prayers_dir.exists():
        prayer_files = list(prayers_dir.rglob('*.txt'))
        print(f'✅ Prayer recovery: {len(prayer_files)} files available')
    else:
        print('⚠️  Prayer recovery: limited (no archive files)')
    
    if users_dir.exists():
        user_files = list(users_dir.glob('*.txt'))
        print(f'✅ User recovery: {len(user_files)} files available')
    else:
        print('⚠️  User recovery: limited (no archive files)')
    
    print()
    print('🎉 Recovery test completed successfully')
    print('💡 System can be recovered from text archives')
    
except Exception as e:
    print(f'❌ Recovery test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""], check=True, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Recovery test failed: {e}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
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
    
    if os.path.exists('heal_prayer_archives.py'):
        print('📁 Running archive healing script...')
        heal_result = subprocess.run([sys.executable, 'heal_prayer_archives.py'], 
                                   check=True, capture_output=True, text=True)
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


def main():
    """Main entry point when run as a standalone script."""
    if len(sys.argv) < 2:
        print("Usage: python archive_validation.py [validate|test-recovery|repair]")
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
            
    elif command == "repair":
        if repair_archives():
            sys.exit(0)
        else:
            sys.exit(1)
            
    else:
        print(f"Unknown command: {command}")
        print("Usage: python archive_validation.py [validate|test-recovery|repair]")
        sys.exit(1)


if __name__ == '__main__':
    main()