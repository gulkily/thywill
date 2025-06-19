#!/usr/bin/env python3
"""
Import prayers and data from text_archives/ directory to database

Usage: python import_text_archives.py [--dry-run]
"""

import sys
import argparse
from pathlib import Path

# Add current directory to path for imports
sys.path.append('.')

from app_helpers.services.text_archive_service import TextArchiveService
from app_helpers.services.text_importer_service import TextImporterService


def main():
    parser = argparse.ArgumentParser(description='Import data from text archives to database')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Preview import without making changes')
    parser.add_argument('--archive-dir', default='text_archives',
                        help='Directory containing text archives (default: text_archives)')
    
    args = parser.parse_args()
    
    # Check if archive directory exists
    archive_path = Path(args.archive_dir)
    if not archive_path.exists():
        print(f"❌ Archive directory not found: {args.archive_dir}")
        print("Make sure you're running this from the project root directory.")
        return 1
    
    print(f"📁 Archive directory: {archive_path.absolute()}")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
    
    # Initialize services
    archive_service = TextArchiveService(base_dir=str(archive_path))
    importer_service = TextImporterService(archive_service)
    
    # Perform import
    print("\n🚀 Starting import...")
    results = importer_service.import_from_archive_directory(
        archive_dir=str(archive_path),
        dry_run=args.dry_run
    )
    
    # Display results
    print("\n📊 Import Results:")
    print("=" * 50)
    
    if results.get('success'):
        stats = results.get('stats', {})
        print(f"✅ Import {'simulation' if args.dry_run else 'completed'} successfully!")
        print(f"👥 Users: {stats.get('users_imported', 0)}")
        print(f"🙏 Prayers: {stats.get('prayers_imported', 0)}")
        print(f"📿 Prayer marks: {stats.get('prayer_marks_imported', 0)}")
        print(f"🏷️  Prayer attributes: {stats.get('prayer_attributes_imported', 0)}")
        print(f"📝 Activity logs: {stats.get('activity_logs_imported', 0)}")
        
        errors = stats.get('errors', [])
        if errors:
            print(f"\n⚠️  Errors encountered ({len(errors)}):")
            for i, error in enumerate(errors[:5], 1):  # Show first 5 errors
                print(f"  {i}. {error}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more errors")
    else:
        print(f"❌ Import failed: {results.get('error', 'Unknown error')}")
        return 1
    
    # Run validation
    if not args.dry_run:
        print("\n🔍 Running validation...")
        validation = importer_service.validate_import_consistency(str(archive_path))
        
        print(f"📋 Validation Results:")
        print(f"  Prayers checked: {validation.get('prayers_checked', 0)}")
        print(f"  Users checked: {validation.get('users_checked', 0)}")
        
        inconsistencies = validation.get('inconsistencies', [])
        if inconsistencies:
            print(f"  ⚠️  Inconsistencies: {len(inconsistencies)}")
            for issue in inconsistencies[:3]:
                print(f"    • {issue}")
        else:
            print("  ✅ No inconsistencies found")
        
        missing_archives = validation.get('missing_archives', [])
        if missing_archives:
            print(f"  📄 Missing archives: {len(missing_archives)}")
    
    print("\n" + "=" * 50)
    
    if args.dry_run:
        print("💡 Run without --dry-run to actually import the data")
    else:
        print("🎉 Import completed! Check your database for the imported prayers.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())