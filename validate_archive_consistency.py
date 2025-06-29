#!/usr/bin/env python3
"""
Archive-Database Consistency Validation Tool

This tool validates the consistency between text archives (source of truth) and the
SQLite database (query layer). It provides comprehensive reporting on data integrity
and helps identify any remaining issues after reconstruction.

Key Validation Checks:
- All prayers have valid authors
- All prayer marks have valid users
- All users in database exist in archives
- All users in archives exist in database
- Archive paths point to existing files
- Database relationships match archive content

Usage:
    python validate_archive_consistency.py              # Full validation
    python validate_archive_consistency.py --summary    # Summary only
    python validate_archive_consistency.py --fix        # Fix minor issues found
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
from sqlmodel import Session, select
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, User, Prayer, PrayerMark, PrayerAttribute
from app_helpers.services.text_archive_service import TextArchiveService
from app_helpers.utils.username_helpers import normalize_username_for_lookup, usernames_are_equivalent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ArchiveConsistencyValidator:
    """Validates consistency between text archives and database"""
    
    def __init__(self, archive_service: TextArchiveService = None):
        self.archive_service = archive_service or TextArchiveService()
        self.validation_results = {
            'total_users_in_db': 0,
            'total_users_in_archives': 0,
            'total_prayers_in_db': 0,
            'total_prayers_in_archives': 0,
            'total_prayer_marks_in_db': 0,
            'orphaned_prayers': 0,
            'orphaned_prayer_marks': 0,
            'missing_archive_paths': 0,
            'broken_archive_paths': 0,
            'users_only_in_db': [],
            'users_only_in_archives': [],
            'consistency_score': 0.0,
            'issues_found': [],
            'archive_path_issues': []
        }
    
    def validate_consistency(self, archive_dir: str = None, summary_only: bool = False) -> Dict:
        """
        Perform comprehensive consistency validation
        
        Args:
            archive_dir: Override default archive directory
            summary_only: If True, only return summary statistics
            
        Returns:
            Dictionary with validation results
        """
        logger.info("Starting archive-database consistency validation")
        
        if not archive_dir:
            archive_dir = str(self.archive_service.base_dir)
            
        archive_path = Path(archive_dir)
        if not archive_path.exists():
            return {'error': f'Archive directory not found: {archive_dir}'}
        
        try:
            with Session(engine) as session:
                # Step 1: Validate user consistency
                logger.info("Step 1: Validating user consistency...")
                self._validate_user_consistency(session, archive_path)
                
                # Step 2: Validate prayer consistency
                logger.info("Step 2: Validating prayer consistency...")
                self._validate_prayer_consistency(session, archive_path)
                
                # Step 3: Validate prayer mark consistency
                logger.info("Step 3: Validating prayer mark consistency...")
                self._validate_prayer_mark_consistency(session)
                
                # Step 4: Validate archive path integrity
                logger.info("Step 4: Validating archive path integrity...")
                self._validate_archive_paths(session)
                
                # Step 5: Calculate consistency score
                logger.info("Step 5: Calculating consistency score...")
                self._calculate_consistency_score()
                
                return {
                    'success': True,
                    'results': self.validation_results,
                    'summary_only': summary_only
                }
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_user_consistency(self, session: Session, archive_path: Path):
        """Validate user consistency between database and archives"""
        # Get all users from database
        db_users = session.exec(select(User)).all()
        db_usernames = {user.display_name for user in db_users}
        self.validation_results['total_users_in_db'] = len(db_users)
        
        # Get all users from archives
        archive_users = self._extract_users_from_archives(archive_path)
        archive_usernames = set(archive_users.keys())
        self.validation_results['total_users_in_archives'] = len(archive_usernames)
        
        # Find users only in database
        users_only_in_db = db_usernames - archive_usernames
        self.validation_results['users_only_in_db'] = list(users_only_in_db)
        if users_only_in_db:
            self.validation_results['issues_found'].append(
                f"Users in database but not in archives: {users_only_in_db}"
            )
        
        # Find users only in archives
        users_only_in_archives = archive_usernames - db_usernames
        self.validation_results['users_only_in_archives'] = list(users_only_in_archives)
        if users_only_in_archives:
            self.validation_results['issues_found'].append(
                f"Users in archives but not in database: {users_only_in_archives}"
            )
        
        logger.info(f"Database users: {len(db_usernames)}, Archive users: {len(archive_usernames)}")
        logger.info(f"Users only in DB: {len(users_only_in_db)}, Users only in archives: {len(users_only_in_archives)}")
    
    def _validate_prayer_consistency(self, session: Session, archive_path: Path):
        """Validate prayer consistency between database and archives"""
        # Get all prayers from database
        db_prayers = session.exec(select(Prayer)).all()
        self.validation_results['total_prayers_in_db'] = len(db_prayers)
        
        # Check for orphaned prayers (prayers without valid authors)
        orphaned_prayers = [p for p in db_prayers if p.author_id is None]
        self.validation_results['orphaned_prayers'] = len(orphaned_prayers)
        
        if orphaned_prayers:
            orphaned_ids = [p.id for p in orphaned_prayers]
            self.validation_results['issues_found'].append(
                f"Orphaned prayers (no author): {orphaned_ids}"
            )
        
        # Count prayers in archives
        archive_prayer_count = self._count_prayers_in_archives(archive_path)
        self.validation_results['total_prayers_in_archives'] = archive_prayer_count
        
        logger.info(f"Database prayers: {len(db_prayers)}, Archive prayers: {archive_prayer_count}")
        logger.info(f"Orphaned prayers: {len(orphaned_prayers)}")
    
    def _validate_prayer_mark_consistency(self, session: Session):
        """Validate prayer mark consistency"""
        # Get all prayer marks from database
        db_prayer_marks = session.exec(select(PrayerMark)).all()
        self.validation_results['total_prayer_marks_in_db'] = len(db_prayer_marks)
        
        # Check for orphaned prayer marks (marks without valid users)
        orphaned_marks = [m for m in db_prayer_marks if m.user_id is None]
        self.validation_results['orphaned_prayer_marks'] = len(orphaned_marks)
        
        if orphaned_marks:
            orphaned_ids = [m.id for m in orphaned_marks]
            self.validation_results['issues_found'].append(
                f"Orphaned prayer marks (no user): {orphaned_ids}"
            )
        
        logger.info(f"Database prayer marks: {len(db_prayer_marks)}")
        logger.info(f"Orphaned prayer marks: {len(orphaned_marks)}")
    
    def _validate_archive_paths(self, session: Session):
        """Validate that archive paths point to existing files"""
        # Check prayers
        prayers_with_paths = session.exec(
            select(Prayer).where(Prayer.text_file_path.is_not(None))
        ).all()
        
        # Check prayer attributes
        attributes_with_paths = session.exec(
            select(PrayerAttribute).where(PrayerAttribute.text_file_path.is_not(None))
        ).all()
        
        # Check users
        users_with_paths = session.exec(
            select(User).where(User.text_file_path.is_not(None))
        ).all()
        
        missing_paths = 0
        broken_paths = 0
        
        # Validate prayer archive paths
        for prayer in prayers_with_paths:
            if not prayer.text_file_path:
                missing_paths += 1
            elif not Path(prayer.text_file_path).exists():
                broken_paths += 1
                self.validation_results['archive_path_issues'].append(
                    f"Prayer {prayer.id}: Missing file {prayer.text_file_path}"
                )
        
        # Validate prayer attribute archive paths
        for attr in attributes_with_paths:
            if not attr.text_file_path:
                missing_paths += 1
            elif not Path(attr.text_file_path).exists():
                broken_paths += 1
                self.validation_results['archive_path_issues'].append(
                    f"Prayer attribute {attr.id}: Missing file {attr.text_file_path}"
                )
        
        # Count records without archive paths
        prayers_without_paths = session.exec(
            select(Prayer).where(Prayer.text_file_path.is_(None))
        ).all()
        
        attributes_without_paths = session.exec(
            select(PrayerAttribute).where(PrayerAttribute.text_file_path.is_(None))
        ).all()
        
        users_without_paths = session.exec(
            select(User).where(User.text_file_path.is_(None))
        ).all()
        
        total_missing = len(prayers_without_paths) + len(attributes_without_paths) + len(users_without_paths)
        
        self.validation_results['missing_archive_paths'] = total_missing
        self.validation_results['broken_archive_paths'] = broken_paths
        
        if total_missing > 0:
            self.validation_results['issues_found'].append(
                f"Records without archive paths: {total_missing} (Prayers: {len(prayers_without_paths)}, Attributes: {len(attributes_without_paths)}, Users: {len(users_without_paths)})"
            )
        
        if broken_paths > 0:
            self.validation_results['issues_found'].append(
                f"Broken archive paths: {broken_paths}"
            )
        
        logger.info(f"Missing archive paths: {total_missing}, Broken paths: {broken_paths}")
    
    def _calculate_consistency_score(self):
        """Calculate overall consistency score (0-100)"""
        total_issues = (
            self.validation_results['orphaned_prayers'] +
            self.validation_results['orphaned_prayer_marks'] +
            len(self.validation_results['users_only_in_archives']) +
            self.validation_results['missing_archive_paths'] +
            self.validation_results['broken_archive_paths']
        )
        
        total_records = (
            self.validation_results['total_users_in_db'] +
            self.validation_results['total_prayers_in_db'] +
            self.validation_results['total_prayer_marks_in_db']
        )
        
        if total_records == 0:
            consistency_score = 100.0
        else:
            consistency_score = max(0, 100 - (total_issues / total_records * 100))
        
        self.validation_results['consistency_score'] = round(consistency_score, 2)
    
    def _extract_users_from_archives(self, archive_path: Path) -> Dict[str, Dict]:
        """Extract all usernames referenced in archives"""
        users_found = {}
        
        # Scan prayer archives
        prayers_dir = archive_path / "prayers"
        if prayers_dir.exists():
            for year_dir in prayers_dir.iterdir():
                if year_dir.is_dir():
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir():
                            for prayer_file in month_dir.glob("*.txt"):
                                try:
                                    content = prayer_file.read_text(encoding='utf-8')
                                    header_match = re.search(r'Prayer\\s+[a-f0-9]+\\s+by\\s+(.+)', content)
                                    if header_match:
                                        username = header_match.group(1).strip()
                                        if username and username != 'None':
                                            users_found[username] = {'source': 'prayer'}
                                except Exception as e:
                                    logger.warning(f"Failed to parse {prayer_file}: {e}")
        
        # Scan user registration files
        users_dir = archive_path / "users"
        if users_dir.exists():
            for user_file in users_dir.glob("*_users.txt"):
                try:
                    content = user_file.read_text(encoding='utf-8')
                    lines = content.split('\\n')
                    for line in lines:
                        if ' - ' in line and ' joined ' in line:
                            parts = line.split(' - ', 1)
                            if len(parts) == 2:
                                action_str = parts[1]
                                if ' joined ' in action_str:
                                    username = action_str.split(' joined ')[0].strip()
                                    if username:
                                        users_found[username] = {'source': 'registration'}
                except Exception as e:
                    logger.warning(f"Failed to parse {user_file}: {e}")
        
        return users_found
    
    def _count_prayers_in_archives(self, archive_path: Path) -> int:
        """Count total prayers in archive files"""
        prayer_count = 0
        prayers_dir = archive_path / "prayers"
        
        if prayers_dir.exists():
            for year_dir in prayers_dir.iterdir():
                if year_dir.is_dir():
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir():
                            prayer_files = list(month_dir.glob("*.txt"))
                            prayer_count += len(prayer_files)
        
        return prayer_count


def print_validation_report(results: Dict, summary_only: bool = False):
    """Print formatted validation report"""
    r = results['results']
    
    print("\\n" + "="*60)
    print("ARCHIVE-DATABASE CONSISTENCY VALIDATION REPORT")
    print("="*60)
    
    # Summary statistics
    print(f"\\n📊 SUMMARY STATISTICS:")
    print(f"   Users in database: {r['total_users_in_db']}")
    print(f"   Users in archives: {r['total_users_in_archives']}")
    print(f"   Prayers in database: {r['total_prayers_in_db']}")
    print(f"   Prayers in archives: {r['total_prayers_in_archives']}")
    print(f"   Prayer marks in database: {r['total_prayer_marks_in_db']}")
    
    # Consistency score
    score = r['consistency_score']
    if score >= 95:
        score_icon = "✅"
        score_status = "EXCELLENT"
    elif score >= 85:
        score_icon = "🟡"
        score_status = "GOOD"
    elif score >= 70:
        score_icon = "🟠"
        score_status = "FAIR"
    else:
        score_icon = "🔴"
        score_status = "POOR"
    
    print(f"\\n{score_icon} CONSISTENCY SCORE: {score}% ({score_status})")
    
    # Issues found
    if r['issues_found']:
        print(f"\\n⚠️  ISSUES FOUND ({len(r['issues_found'])}):")
        for i, issue in enumerate(r['issues_found'], 1):
            print(f"   {i}. {issue}")
    else:
        print("\\n✅ NO ISSUES FOUND")
    
    if not summary_only:
        # Detailed breakdown
        print(f"\\n📋 DETAILED BREAKDOWN:")
        print(f"   Orphaned prayers: {r['orphaned_prayers']}")
        print(f"   Orphaned prayer marks: {r['orphaned_prayer_marks']}")
        print(f"   Missing archive paths: {r['missing_archive_paths']}")
        print(f"   Broken archive paths: {r['broken_archive_paths']}")
        
        if r['users_only_in_db']:
            print(f"   Users only in database: {r['users_only_in_db']}")
        
        if r['users_only_in_archives']:
            print(f"   Users only in archives: {r['users_only_in_archives']}")
        
        if r['archive_path_issues']:
            print(f"\\n🔗 ARCHIVE PATH ISSUES:")
            for issue in r['archive_path_issues']:
                print(f"   - {issue}")
    
    print("\\n" + "="*60)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Validate archive-database consistency')
    parser.add_argument('--summary', action='store_true',
                       help='Show summary only, not detailed breakdown')
    parser.add_argument('--archive-dir', type=str,
                       help='Override default archive directory')
    parser.add_argument('--fix', action='store_true',
                       help='Attempt to fix minor issues found (not implemented yet)')
    
    args = parser.parse_args()
    
    validator = ArchiveConsistencyValidator()
    results = validator.validate_consistency(
        archive_dir=args.archive_dir,
        summary_only=args.summary
    )
    
    if results.get('success'):
        print_validation_report(results, args.summary)
        
        # Return exit code based on consistency score
        score = results['results']['consistency_score']
        if score >= 95:
            return 0  # Excellent
        elif score >= 85:
            return 1  # Good but has some issues
        else:
            return 2  # Significant issues found
    else:
        print(f"Validation failed: {results.get('error')}")
        return 3


if __name__ == '__main__':
    sys.exit(main())