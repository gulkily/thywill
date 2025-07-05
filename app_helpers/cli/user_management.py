#!/usr/bin/env python3
"""
User Management CLI Module

Handles duplicate user checking and merging operations.
Can be run independently or called from the CLI script.
"""

import sys
import os
import subprocess
from typing import Dict, Any


def check_project_directory() -> bool:
    """Check if we're in the correct ThyWill project directory."""
    return os.path.exists("models.py") or os.path.exists("thywill.db")


def check_migration_script_exists() -> bool:
    """Check if the duplicate user migration script exists."""
    return os.path.exists("migrations/duplicate_user_migration.py")


def check_duplicates() -> Dict[str, Any]:
    """
    Check for duplicate users by calling the migration script.
    
    Returns:
        Dict containing check results
    """
    if not check_project_directory():
        raise RuntimeError("Must run from ThyWill project directory. Database or models.py not found")
    
    if not check_migration_script_exists():
        raise RuntimeError("Migration script not found: migrations/duplicate_user_migration.py")
    
    # Call the migration script with check-only flag
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = '.'
        result = subprocess.run([
            sys.executable, "migrations/duplicate_user_migration.py", "--check-only"
        ], capture_output=True, text=True, check=True, env=env)
        
        return {
            'success': True,
            'output': result.stdout,
            'error': result.stderr
        }
    except subprocess.CalledProcessError as e:
        return {
            'success': False,
            'output': e.stdout,
            'error': e.stderr,
            'return_code': e.returncode
        }


def merge_duplicates() -> Dict[str, Any]:
    """
    Merge duplicate users by calling the migration script interactively.
    
    Returns:
        Dict containing merge results
    """
    if not check_project_directory():
        raise RuntimeError("Must run from ThyWill project directory. Database or models.py not found")
    
    if not check_migration_script_exists():
        raise RuntimeError("Migration script not found: migrations/duplicate_user_migration.py")
    
    # Call the migration script with interactive flag
    try:
        env = os.environ.copy()
        env['PYTHONPATH'] = '.'
        result = subprocess.run([
            sys.executable, "migrations/duplicate_user_migration.py", "--interactive"
        ], check=True, env=env)
        
        return {
            'success': True,
            'return_code': result.returncode
        }
    except subprocess.CalledProcessError as e:
        return {
            'success': False,
            'return_code': e.returncode
        }


def main():
    """Main entry point when run as a standalone script."""
    if len(sys.argv) < 2:
        print("Usage: python user_management.py [check|merge]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "check":
            print("🔍 Checking for Duplicate Users")
            print("=" * 35)
            print()
            
            result = check_duplicates()
            if result['output']:
                print(result['output'])
            if result['error']:
                print(result['error'], file=sys.stderr)
            
            if not result['success']:
                sys.exit(result.get('return_code', 1))
                
        elif command == "merge":
            print("🔧 Merging Duplicate Users")
            print("=" * 30)
            print()
            
            result = merge_duplicates()
            if not result['success']:
                sys.exit(result.get('return_code', 1))
                
        else:
            print(f"Unknown command: {command}")
            print("Usage: python user_management.py [check|merge]")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Operation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()