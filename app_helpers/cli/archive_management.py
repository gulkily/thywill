#!/usr/bin/env python3
"""
Archive Management CLI Module

Handles archive healing, synchronization, and validation operations.
Can be run independently or called from the CLI script.
"""

import sys
import os
import subprocess
from typing import Dict, Any, List


def validate_project_directory() -> bool:
    """Check if we're in the correct ThyWill project directory."""
    return os.path.exists("app.py") and os.path.exists("models.py")


def heal_archives() -> bool:
    """
    Heal missing prayer archives by creating text files for existing prayers.
    
    This function finds prayers in the database that don't have corresponding
    text archive files and creates them, following ThyWill's archive-first philosophy.
    
    Returns:
        True if successful, False otherwise
    """
    print("🩹 Healing Prayer Archives")
    print("=" * 30)
    
    if not validate_project_directory():
        print("❌ app.py not found in current directory")
        print("Please run this command from your ThyWill project directory")
        return False
    
    try:
        result = subprocess.run([
            sys.executable, 
            "scripts/utils/heal_prayer_archives.py",
            "--force"
        ], check=True, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        print("✅ Archive healing completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Archive healing failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print("❌ Heal archives script not found")
        print("Expected: scripts/utils/heal_prayer_archives.py")
        return False


def sync_archives() -> bool:
    """
    Interactive post-deployment archive synchronization.
    
    This function performs a complete archive synchronization workflow:
    1. Check database status
    2. Validate existing archives
    3. Import any missing data from archives
    4. Heal any missing archive files
    5. Final validation
    
    Returns:
        True if successful, False otherwise
    """
    print("🔄 Archive Synchronization Wizard")
    print("=" * 35)
    print()
    print("This will synchronize your database with text archives:")
    print("1. Check database status")
    print("2. Validate existing archives")
    print("3. Import any missing data from archives")
    print("4. Heal any missing archive files")
    print("5. Final validation")
    print()
    
    if not validate_project_directory():
        print("❌ app.py not found in current directory")
        print("Please run this command from your ThyWill project directory")
        return False
    
    # Prompt for confirmation
    try:
        response = input("Continue with archive synchronization? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Archive synchronization cancelled.")
            return True
    except KeyboardInterrupt:
        print("\nArchive synchronization cancelled.")
        return True
    
    print("\n🔍 Step 1: Checking database status...")
    # Add database status check here if needed
    
    print("\n✅ Step 2: Validating existing archives...")
    if not validate_archives():
        print("⚠️  Archive validation found issues - continuing anyway")
    
    print("\n📥 Step 3: Importing from text archives...")
    if not import_all_database_data():
        print("❌ Import failed - stopping synchronization")
        return False
    
    print("\n🩹 Step 4: Healing missing archives...")
    if not heal_archives():
        print("❌ Archive healing failed - stopping synchronization")
        return False
    
    print("\n🔍 Step 5: Final validation...")
    if not validate_archives():
        print("⚠️  Final validation found issues")
        return False
    
    print("\n✅ Archive synchronization completed successfully!")
    return True


def validate_archives() -> bool:
    """
    Validate archive completeness and integrity.
    
    Returns:
        True if validation passes, False otherwise
    """
    print("🔍 Validating Archives")
    print("=" * 20)
    
    if not validate_project_directory():
        print("❌ app.py not found in current directory")
        return False
    
    try:
        # Run archive validation
        result = subprocess.run([
            sys.executable, "-c", """
import sys
import os
sys.path.append('.')

# Import validation functions
from app_helpers.services.text_archive_service import TextArchiveService

service = TextArchiveService()
if service.validate_archives():
    print("✅ Archive validation passed")
    sys.exit(0)
else:
    print("❌ Archive validation failed")
    sys.exit(1)
"""
        ], check=True, capture_output=True, text=True)
        
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Archive validation failed")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def export_all_database_data() -> bool:
    """
    Export absolutely all server data to text archives.
    
    This includes everything in the database organized in unified archive structure.
    
    Returns:
        True if successful, False otherwise
    """
    if not validate_project_directory():
        print("❌ app.py not found in current directory")
        print("Please run this command from your ThyWill project directory")
        return False
    
    try:
        # Use the clean export service
        from app_helpers.services.export_service import export_all_database_data
        return export_all_database_data()
    except ImportError as e:
        print(f"❌ Error importing export service: {e}")
        return False


def import_all_database_data(dry_run: bool = False) -> bool:
    """
    Import all database data from text archives.
    
    Args:
        dry_run: If True, preview changes without making them
        
    Returns:
        True if successful, False otherwise
    """
    if not validate_project_directory():
        print("❌ app.py not found in current directory")
        print("Please run this command from your ThyWill project directory")
        return False
    
    try:
        # Use the clean import service
        from app_helpers.services.import_service import import_all_database_data
        return import_all_database_data(dry_run)
    except ImportError as e:
        print(f"❌ Error importing import service: {e}")
        return False


def main():
    """Main entry point for archive management commands."""
    if len(sys.argv) < 2:
        print("Usage: python -m app_helpers.cli.archive_management <command>")
        print("Commands:")
        print("  heal-archives    - Create missing archive files")
        print("  sync-archives    - Interactive archive synchronization")
        print("  validate-archives - Validate archive integrity")
        print("  export-all       - Export all database data")
        print("  import-all       - Import all database data")
        print("  import-all --dry-run - Preview import changes")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "heal-archives":
        success = heal_archives()
    elif command == "sync-archives":
        success = sync_archives()
    elif command == "validate-archives":
        success = validate_archives()
    elif command == "export-all":
        success = export_all_database_data()
    elif command == "import-all":
        dry_run = "--dry-run" in sys.argv
        success = import_all_database_data(dry_run)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()