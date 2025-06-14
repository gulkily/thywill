#!/usr/bin/env python3
"""
Prayer Archive Restoration Utility

This utility restores prayers from text archive files back to the database.
It automatically creates missing users when importing prayers.

Usage:
    python restore_prayers.py              # Interactive mode
    python restore_prayers.py --auto       # Automatic mode
    python restore_prayers.py --dry-run    # See what would be imported
"""

import sys
import argparse
from pathlib import Path
from app_helpers.services.text_importer_service import text_importer_service

def main():
    parser = argparse.ArgumentParser(description='Restore prayers from text archives')
    parser.add_argument('--auto', action='store_true', help='Run automatically without prompts')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be imported without actually importing')
    parser.add_argument('--archive-dir', default='./text_archives', help='Archive directory path')
    
    args = parser.parse_args()
    
    print("🔄 Prayer Archive Restoration Utility")
    print("=" * 50)
    
    archive_dir = args.archive_dir
    
    # Check if archive directory exists
    if not Path(archive_dir).exists():
        print(f"❌ Archive directory not found: {archive_dir}")
        return False
    
    # Count prayer files
    prayers_dir = Path(archive_dir) / "prayers"
    prayer_files = []
    if prayers_dir.exists():
        for year_dir in prayers_dir.iterdir():
            if year_dir.is_dir():
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir():
                        prayer_files.extend(month_dir.glob("*.txt"))
    
    print(f"📁 Found {len(prayer_files)} prayer archive files")
    
    if len(prayer_files) == 0:
        print("✅ No prayer archive files found - nothing to restore")
        return True
    
    # Show sample files
    print("📄 Sample files:")
    for file in prayer_files[:3]:
        print(f"  • {file}")
    if len(prayer_files) > 3:
        print(f"  ... and {len(prayer_files) - 3} more")
    
    # Get user confirmation unless auto mode
    if not args.auto and not args.dry_run:
        try:
            response = input(f"\n🤔 Do you want to restore {len(prayer_files)} prayers from archives? (y/N): ")
            if response.lower() != 'y':
                print("❌ Operation cancelled")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\n❌ Operation cancelled")
            return False
    
    # Perform dry run
    print(f"\n📋 Running dry run...")
    dry_results = text_importer_service.import_from_archive_directory(archive_dir, dry_run=True)
    
    if not dry_results.get('success'):
        print(f"❌ Dry run failed: {dry_results.get('error')}")
        return False
    
    stats = dry_results.get('stats', {})
    print(f"📊 Import preview:")
    print(f"  • Users to import: {stats.get('users_imported', 0)}")
    print(f"  • Prayers to import: {stats.get('prayers_imported', 0)}")
    print(f"  • Prayer marks to import: {stats.get('prayer_marks_imported', 0)}")
    print(f"  • Prayer attributes to import: {stats.get('prayer_attributes_imported', 0)}")
    print(f"  • Activity logs to import: {stats.get('activity_logs_imported', 0)}")
    
    if stats.get('errors'):
        print(f"  ⚠️  Potential issues: {len(stats['errors'])}")
        for error in stats['errors'][:3]:
            print(f"    • {error}")
    
    # Stop here if dry run mode
    if args.dry_run:
        print(f"\n🔍 Dry run complete - no data was imported")
        return True
    
    # Get confirmation for actual import unless auto mode
    if not args.auto:
        try:
            response = input(f"\n✅ Proceed with actual import? (y/N): ")
            if response.lower() != 'y':
                print("❌ Import cancelled")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\n❌ Import cancelled")
            return False
    
    # Perform actual import
    print(f"\n🚀 Performing import...")
    import_results = text_importer_service.import_from_archive_directory(archive_dir, dry_run=False)
    
    if not import_results.get('success'):
        print(f"❌ Import failed: {import_results.get('error')}")
        return False
    
    stats = import_results.get('stats', {})
    print(f"\n🎉 Import completed successfully!")
    print(f"📊 Final results:")
    print(f"  • Users imported: {stats.get('users_imported', 0)}")
    print(f"  • Prayers imported: {stats.get('prayers_imported', 0)}")
    print(f"  • Prayer marks imported: {stats.get('prayer_marks_imported', 0)}")
    print(f"  • Prayer attributes imported: {stats.get('prayer_attributes_imported', 0)}")
    print(f"  • Activity logs imported: {stats.get('activity_logs_imported', 0)}")
    
    if stats.get('errors'):
        print(f"  ⚠️  Import errors: {len(stats['errors'])}")
        for error in stats['errors'][:5]:
            print(f"    • {error}")
    
    # Verify the restoration
    print(f"\n🔍 Verifying restoration...")
    from models import engine, Prayer, User
    from sqlmodel import Session, select
    
    with Session(engine) as s:
        prayers = s.exec(select(Prayer)).all()
        users = s.exec(select(User)).all()
        
        print(f"✅ Database now contains:")
        print(f"  • {len(prayers)} prayers")
        print(f"  • {len(users)} users")
        
        if prayers:
            print(f"\nSample restored prayers:")
            for prayer in prayers[:3]:
                print(f"  • ID: {prayer.id}")
                print(f"    Text: {prayer.text[:50]}...")
                if prayer.text_file_path:
                    print(f"    Archive: {Path(prayer.text_file_path).name}")
    
    print(f"\n🌐 Prayers should now appear on your website!")
    
    if len(prayer_files) > 0 and stats.get('prayers_imported', 0) == 0:
        print(f"\n💡 If no prayers were imported, possible reasons:")
        print(f"  • Prayer files may be corrupted or in wrong format")
        print(f"  • Database constraints preventing import")
        print(f"  • Check the error messages above for details")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)