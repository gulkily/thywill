#!/usr/bin/env python3
"""
Community Data Import Utility

Safely imports data from ThyWill community export ZIP files.
Handles both individual JSON files and combined export formats.
"""

import json
import zipfile
import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlmodel import Session, select
from models import (
    User, Prayer, PrayerAttribute, PrayerMark, PrayerSkip,
    PrayerActivityLog, Role, UserRole, ChangelogEntry, engine
)
from database_protection import DatabaseProtection, require_explicit_confirmation

class CommunityImportService:
    """Service for importing community data from export files"""
    
    def __init__(self):
        self.import_stats = {
            'users': {'created': 0, 'skipped': 0, 'errors': 0},
            'prayers': {'created': 0, 'skipped': 0, 'errors': 0},
            'prayer_attributes': {'created': 0, 'skipped': 0, 'errors': 0},
            'prayer_marks': {'created': 0, 'skipped': 0, 'errors': 0},
            'prayer_skips': {'created': 0, 'skipped': 0, 'errors': 0},
            'prayer_activity_log': {'created': 0, 'skipped': 0, 'errors': 0},
            'roles': {'created': 0, 'skipped': 0, 'errors': 0},
            'user_roles': {'created': 0, 'skipped': 0, 'errors': 0},
            'changelog_entries': {'created': 0, 'skipped': 0, 'errors': 0}
        }
    
    def validate_export_file(self, file_path: str) -> Dict[str, Any]:
        """Validate and analyze export file structure"""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Export file not found: {file_path}")
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                file_list = zip_file.namelist()
                
                # Check for required files
                has_metadata = 'metadata.json' in file_list
                has_individual_files = any(f.endswith('.json') and f != 'metadata.json' for f in file_list)
                has_combined_file = any('community_export_' in f and f.endswith('.json') for f in file_list)
                
                # Try to read metadata
                metadata = None
                if has_metadata:
                    try:
                        with zip_file.open('metadata.json') as f:
                            metadata = json.load(f)
                    except Exception as e:
                        print(f"Warning: Could not read metadata: {e}")
                
                # Count records in main tables
                record_counts = {}
                if has_individual_files:
                    for table in ['users', 'prayers', 'prayer_marks']:
                        filename = f"{table}.json"
                        if filename in file_list:
                            try:
                                with zip_file.open(filename) as f:
                                    data = json.load(f)
                                    record_counts[table] = len(data) if isinstance(data, list) else 0
                            except Exception:
                                record_counts[table] = 0
                
                return {
                    'valid': True,
                    'has_metadata': has_metadata,
                    'has_individual_files': has_individual_files,
                    'has_combined_file': has_combined_file,
                    'metadata': metadata,
                    'file_list': file_list,
                    'record_counts': record_counts
                }
                
        except zipfile.BadZipFile:
            raise ValueError(f"Invalid ZIP file: {file_path}")
        except Exception as e:
            raise ValueError(f"Error reading export file: {e}")
    
    def import_from_zip(self, file_path: str, overwrite_existing: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """Import community data from ZIP export file"""
        
        print(f"🔍 Validating export file: {file_path}")
        validation = self.validate_export_file(file_path)
        
        if not validation['valid']:
            raise ValueError("Invalid export file format")
        
        # Show file info
        metadata = validation.get('metadata', {}) or {}
        export_date = metadata.get('export_date', 'Unknown')
        export_version = metadata.get('version', 'Unknown')
        
        print(f"📦 Export Info:")
        print(f"   Date: {export_date}")
        print(f"   Version: {export_version}")
        print(f"   Format: {'Individual files' if validation['has_individual_files'] else 'Combined file'}")
        
        if validation['record_counts']:
            print(f"📊 Record Counts:")
            for table, count in validation['record_counts'].items():
                print(f"   {table}: {count:,}")
        
        if dry_run:
            print("🔍 DRY RUN - No data will be imported")
        elif not require_explicit_confirmation("import this community data"):
            print("❌ Import cancelled by user")
            return {'success': False, 'message': 'Import cancelled'}
        
        # Create backup before import
        if not dry_run:
            print("💾 Creating backup before import...")
            backup_path = DatabaseProtection.backup_database()
            if backup_path:
                print(f"✅ Backup created: {backup_path}")
            else:
                print("⚠️  Could not create backup - proceeding anyway")
        
        # Import data
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            if validation['has_individual_files']:
                return self._import_individual_files(zip_file, overwrite_existing, dry_run)
            elif validation['has_combined_file']:
                return self._import_combined_file(zip_file, overwrite_existing, dry_run)
            else:
                raise ValueError("No valid data files found in export")
    
    def _import_individual_files(self, zip_file: zipfile.ZipFile, overwrite_existing: bool, dry_run: bool) -> Dict[str, Any]:
        """Import from individual JSON files format"""
        
        # Import order matters due to foreign key relationships
        import_order = [
            'users', 'roles', 'user_roles', 'prayers', 'prayer_attributes',
            'prayer_marks', 'prayer_skips', 'prayer_activity_log', 'changelog_entries'
        ]
        
        with Session(engine) as session:
            for table_name in import_order:
                filename = f"{table_name}.json"
                if filename in zip_file.namelist():
                    print(f"📥 Importing {table_name}...")
                    
                    with zip_file.open(filename) as f:
                        data = json.load(f)
                    
                    if isinstance(data, list):
                        self._import_table_data(session, table_name, data, overwrite_existing, dry_run)
                    else:
                        print(f"⚠️  Skipping {table_name}: Invalid data format")
                else:
                    print(f"⚠️  File not found: {filename}")
            
            if not dry_run:
                session.commit()
                print("✅ All data committed to database")
        
        return {
            'success': True,
            'stats': self.import_stats,
            'message': 'Import completed successfully'
        }
    
    def _import_combined_file(self, zip_file: zipfile.ZipFile, overwrite_existing: bool, dry_run: bool) -> Dict[str, Any]:
        """Import from combined JSON file format"""
        
        # Find the combined export file
        combined_files = [f for f in zip_file.namelist() if 'community_export_' in f and f.endswith('.json')]
        if not combined_files:
            raise ValueError("No combined export file found")
        
        combined_file = combined_files[0]
        print(f"📥 Importing from combined file: {combined_file}")
        
        with zip_file.open(combined_file) as f:
            data = json.load(f)
        
        with Session(engine) as session:
            import_order = [
                'users', 'roles', 'user_roles', 'prayers', 'prayer_attributes',
                'prayer_marks', 'prayer_skips', 'prayer_activity_log', 'changelog_entries'
            ]
            
            for table_name in import_order:
                if table_name in data and isinstance(data[table_name], list):
                    print(f"📥 Importing {table_name}...")
                    self._import_table_data(session, table_name, data[table_name], overwrite_existing, dry_run)
                else:
                    print(f"⚠️  No data found for {table_name}")
            
            if not dry_run:
                session.commit()
                print("✅ All data committed to database")
        
        return {
            'success': True,
            'stats': self.import_stats,
            'message': 'Import completed successfully'
        }
    
    def _import_table_data(self, session: Session, table_name: str, data: List[Dict], overwrite_existing: bool, dry_run: bool):
        """Import data for a specific table"""
        
        # Map table names to model classes
        model_map = {
            'users': User,
            'prayers': Prayer,
            'prayer_attributes': PrayerAttribute,
            'prayer_marks': PrayerMark,
            'prayer_skips': PrayerSkip,
            'prayer_activity_log': PrayerActivityLog,
            'roles': Role,
            'user_roles': UserRole,
            'changelog_entries': ChangelogEntry
        }
        
        if table_name not in model_map:
            print(f"⚠️  Unknown table: {table_name}")
            return
        
        model_class = model_map[table_name]
        
        for item in data:
            try:
                # Convert datetime strings back to datetime objects
                for field, value in item.items():
                    if field.endswith('_at') or field.endswith('_date'):
                        if isinstance(value, str) and value:
                            # Remove 'Z' suffix and parse ISO format
                            clean_value = value.rstrip('Z')
                            item[field] = datetime.fromisoformat(clean_value)
                
                # Check if record already exists (handle different primary key names)
                if table_name == 'changelog_entries':
                    # ChangelogEntry uses commit_id as primary key
                    primary_key_value = item.get('commit_id')
                else:
                    # Most tables use id as primary key
                    primary_key_value = item.get('id')
                
                existing = session.get(model_class, primary_key_value) if primary_key_value else None
                
                if existing:
                    if overwrite_existing and not dry_run:
                        # Update existing record
                        for field, value in item.items():
                            if hasattr(existing, field):
                                setattr(existing, field, value)
                        session.add(existing)
                        self.import_stats[table_name]['created'] += 1
                    else:
                        self.import_stats[table_name]['skipped'] += 1
                else:
                    # Create new record
                    if not dry_run:
                        new_record = model_class(**item)
                        session.add(new_record)
                    self.import_stats[table_name]['created'] += 1
                    
            except Exception as e:
                # Get appropriate key for error reporting
                key_value = item.get('commit_id') if table_name == 'changelog_entries' else item.get('id', 'unknown')
                print(f"❌ Error importing {table_name} record {key_value}: {e}")
                self.import_stats[table_name]['errors'] += 1
        
        # Print stats for this table
        stats = self.import_stats[table_name]
        print(f"   ✅ Created: {stats['created']}, ⏭️ Skipped: {stats['skipped']}, ❌ Errors: {stats['errors']}")

def main():
    """Main CLI interface for importing community data"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python import_community_data.py <export_file.zip> [options]")
        print()
        print("Options:")
        print("  --dry-run              Preview import without making changes")
        print("  --overwrite            Overwrite existing records")
        print("  --help                 Show this help message")
        print()
        print("Examples:")
        print("  python import_community_data.py community_export_2024-12-06.zip")
        print("  python import_community_data.py export.zip --dry-run")
        print("  python import_community_data.py export.zip --overwrite")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    # Parse options
    dry_run = '--dry-run' in sys.argv
    overwrite = '--overwrite' in sys.argv
    show_help = '--help' in sys.argv
    
    if show_help:
        main()
        return
    
    try:
        print("🚀 ThyWill Community Data Import")
        print("=" * 40)
        
        # Initialize import service
        import_service = CommunityImportService()
        
        # Import data
        result = import_service.import_from_zip(
            file_path=file_path,
            overwrite_existing=overwrite,
            dry_run=dry_run
        )
        
        if result['success']:
            print()
            print("🎉 Import Summary:")
            print("=" * 40)
            total_created = sum(stats['created'] for stats in result['stats'].values())
            total_skipped = sum(stats['skipped'] for stats in result['stats'].values())
            total_errors = sum(stats['errors'] for stats in result['stats'].values())
            
            print(f"✅ Total created: {total_created:,}")
            print(f"⏭️ Total skipped: {total_skipped:,}")
            print(f"❌ Total errors: {total_errors:,}")
            
            if dry_run:
                print("\n🔍 This was a dry run - no data was actually imported")
            else:
                print(f"\n✅ {result['message']}")
        else:
            print(f"❌ Import failed: {result['message']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()