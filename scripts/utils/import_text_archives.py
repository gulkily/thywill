#!/usr/bin/env python3
"""
Import prayers and data from text_archives/ directory to database

Usage: python import_text_archives.py [--dry-run]
"""

import sys
import argparse
import tempfile
import zipfile
import shutil
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app_helpers.services.text_archive_service import TextArchiveService
from app_helpers.services.text_importer_service import TextImporterService


def copy_text_archives_to_local(source_archive_dir: str, target_base_dir: str = None) -> dict:
    """
    Copy text archive files from source directory to local text_archives directory.
    
    Returns dict with results: {'success': bool, 'copied': int, 'skipped': int, 'errors': list}
    """
    if target_base_dir is None:
        target_base_dir = os.environ.get('TEXT_ARCHIVE_BASE_DIR', './text_archives')
    
    source_path = Path(source_archive_dir)
    target_path = Path(target_base_dir)
    
    results = {
        'success': True,
        'copied': 0,
        'skipped': 0,
        'errors': []
    }
    
    if not source_path.exists():
        results['success'] = False
        results['errors'].append(f"Source directory not found: {source_archive_dir}")
        return results
    
    # Create target directory if it doesn't exist
    target_path.mkdir(parents=True, exist_ok=True)
    
    # Copy files while preserving directory structure
    for root, dirs, files in os.walk(source_path):
        # Calculate relative path from source
        rel_path = Path(root).relative_to(source_path)
        target_dir = target_path / rel_path
        
        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files
        for file in files:
            source_file = Path(root) / file
            target_file = target_dir / file
            
            try:
                # Skip if target file already exists and is identical
                if target_file.exists():
                    if source_file.stat().st_size == target_file.stat().st_size:
                        results['skipped'] += 1
                        continue
                
                # Copy file
                shutil.copy2(source_file, target_file)
                results['copied'] += 1
                
            except Exception as e:
                results['success'] = False
                results['errors'].append(f"Failed to copy {source_file}: {str(e)}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Import data from text archives to database')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Preview import without making changes')
    parser.add_argument('--archive-dir', default='text_archives',
                        help='Directory containing text archives (default: text_archives)')
    parser.add_argument('zip_file', nargs='?',
                        help='ZIP file containing text archives to import')
    
    args = parser.parse_args()
    
    # Handle ZIP file input
    temp_dir = None
    if args.zip_file:
        zip_path = Path(args.zip_file)
        if not zip_path.exists():
            print(f"❌ ZIP file not found: {args.zip_file}")
            return 1
        
        print(f"📦 Extracting ZIP file: {zip_path.name}")
        temp_dir = tempfile.mkdtemp()
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find the archive directory in the extracted files
            extracted_path = Path(temp_dir)
            archive_candidates = list(extracted_path.glob('*/'))
            
            if archive_candidates:
                # Use the first directory found
                archive_path = archive_candidates[0]
                print(f"📁 Found archive directory: {archive_path.name}")
            else:
                # Use the temp directory directly if no subdirectories
                archive_path = extracted_path
                
        except zipfile.BadZipFile:
            print(f"❌ Invalid ZIP file: {args.zip_file}")
            return 1
    else:
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
    
    # Copy text archive files to local directory (only if importing from ZIP and successful)
    if results.get('success') and not args.dry_run and args.zip_file:
        print("\n📁 Copying text archive files to local directory...")
        copy_results = copy_text_archives_to_local(str(archive_path))
        
        if copy_results['success']:
            print(f"✅ Text archive files copied successfully!")
            print(f"   📋 Files copied: {copy_results['copied']}")
            print(f"   ⏭️ Files skipped: {copy_results['skipped']}")
        else:
            print(f"⚠️  Some text archive files could not be copied:")
            for error in copy_results['errors'][:3]:
                print(f"   • {error}")
            if len(copy_results['errors']) > 3:
                print(f"   ... and {len(copy_results['errors']) - 3} more errors")

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
    
    # Clean up temporary directory if we used one
    if temp_dir:
        import shutil
        shutil.rmtree(temp_dir)
        print(f"🧹 Cleaned up temporary files")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())