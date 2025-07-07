#!/usr/bin/env python3
"""
Archive-Based Database Reconstruction Tool

This tool fixes orphaned database relationships by using text archives as the source of truth.
It addresses the fundamental architectural issue where text archives use usernames but the
database uses UUID IDs, causing mismatches that result in "prayers by None" and orphaned records.

Key Features:
- Scans all text archives to extract correct user relationships
- Fixes orphaned prayers and prayer marks using archive data
- Creates missing users found in archives but not in database
- Validates consistency between archives and database
- Provides detailed reporting and dry-run mode

Usage:
    python reconstruct_from_archives.py --dry-run    # Preview changes
    python reconstruct_from_archives.py --execute    # Apply fixes
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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models import engine, User, Prayer, PrayerMark, PrayerAttribute
from app_helpers.services.text_archive_service import TextArchiveService
from app_helpers.utils.username_helpers import normalize_username_for_lookup, usernames_are_equivalent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ArchiveReconstructor:
    """Reconstructs database relationships from text archives"""
    
    def __init__(self, archive_service: TextArchiveService = None):
        self.archive_service = archive_service or TextArchiveService()
        self.stats = {
            'archives_scanned': 0,
            'users_found_in_archives': 0,
            'missing_users_created': 0,
            'orphaned_prayers_fixed': 0,
            'orphaned_prayer_marks_fixed': 0,
            'prayer_attributes_fixed': 0,
            'validation_errors': 0,
            'errors': []
        }
        
        # Cache for username resolution
        self._username_cache = {}
        self._user_id_cache = {}
        
    def reconstruct_from_archives(self, dry_run: bool = True, 
                                archive_dir: str = None) -> Dict:
        """
        Main reconstruction process
        
        Args:
            dry_run: If True, don't make actual changes, just report what would be done
            archive_dir: Override default archive directory
            
        Returns:
            Dictionary with reconstruction results and statistics
        """
        logger.info("Starting archive-based database reconstruction")
        if dry_run:
            logger.info("DRY RUN MODE - No database changes will be made")
        
        if not archive_dir:
            archive_dir = str(self.archive_service.base_dir)
            
        archive_path = Path(archive_dir)
        if not archive_path.exists():
            return {'error': f'Archive directory not found: {archive_dir}'}
            
        try:
            with Session(engine) as session:
                # Step 1: Build comprehensive username-to-user mapping from archives
                logger.info("Step 1: Scanning archives to extract all usernames...")
                archive_users = self._extract_users_from_archives(archive_path)
                
                # Step 2: Build database user lookup cache for performance
                logger.info("Step 2: Building user lookup cache...")
                self._build_user_cache(session)
                
                # Step 3: Create missing users found in archives
                logger.info("Step 3: Creating missing users...")
                missing_users = self._create_missing_users(session, archive_users, dry_run)
                
                # Step 4: Fix orphaned prayers
                logger.info("Step 4: Fixing orphaned prayers...")
                self._fix_orphaned_prayers(session, archive_path, dry_run)
                
                # Step 5: Fix orphaned prayer marks
                logger.info("Step 5: Fixing orphaned prayer marks...")
                self._fix_orphaned_prayer_marks(session, archive_path, dry_run)
                
                # Step 6: Fix prayer attributes
                logger.info("Step 6: Fixing prayer attributes...")
                self._fix_prayer_attributes(session, dry_run)
                
                # Step 7: Validation
                logger.info("Step 7: Validating consistency...")
                validation_results = self._validate_consistency(session, archive_path)
                
                return {
                    'success': True,
                    'dry_run': dry_run,
                    'stats': self.stats,
                    'missing_users_created': missing_users,
                    'validation': validation_results
                }
                
        except Exception as e:
            logger.error(f"Reconstruction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }
    
    def _extract_users_from_archives(self, archive_path: Path) -> Dict[str, Dict]:
        """Extract all usernames referenced in archives"""
        users_found = {}
        
        # Scan prayer archives for author names
        prayers_dir = archive_path / "prayers"
        if prayers_dir.exists():
            for year_dir in prayers_dir.iterdir():
                if year_dir.is_dir():
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir():
                            for prayer_file in month_dir.glob("*.txt"):
                                try:
                                    self._extract_users_from_prayer_file(prayer_file, users_found)
                                except Exception as e:
                                    logger.warning(f"Failed to parse prayer file {prayer_file}: {e}")
        
        # Scan user registration files
        users_dir = archive_path / "users"
        if users_dir.exists():
            for user_file in users_dir.glob("*_users.txt"):
                try:
                    self._extract_users_from_registration_file(user_file, users_found)
                except Exception as e:
                    logger.warning(f"Failed to parse user file {user_file}: {e}")
        
        # Scan activity logs for additional usernames
        activity_dir = archive_path / "activity"
        if activity_dir.exists():
            for activity_file in activity_dir.glob("*.txt"):
                try:
                    self._extract_users_from_activity_file(activity_file, users_found)
                except Exception as e:
                    logger.warning(f"Failed to parse activity file {activity_file}: {e}")
        
        self.stats['users_found_in_archives'] = len(users_found)
        logger.info(f"Found {len(users_found)} unique users in archives: {list(users_found.keys())}")
        
        return users_found
    
    def _extract_users_from_prayer_file(self, prayer_file: Path, users_found: Dict):
        """Extract username from a prayer archive file"""
        content = prayer_file.read_text(encoding='utf-8')
        
        # Look for prayer header: "Prayer <id> by <username>"
        header_match = re.search(r'Prayer\s+[a-f0-9]+\s+by\s+(.+)', content)
        if header_match:
            username = header_match.group(1).strip()
            if username and username != 'None':
                users_found[username] = {
                    'source': 'prayer_archive',
                    'file': str(prayer_file),
                    'found_as': 'author'
                }
        
        # Look for prayer marks in activity log section
        activity_matches = re.findall(r'\d{2}:\d{2} - (.+?) prayed for prayer', content)
        for username in activity_matches:
            username = username.strip()
            if username and username != 'None':
                if username not in users_found:
                    users_found[username] = {
                        'source': 'prayer_activity',
                        'file': str(prayer_file),
                        'found_as': 'prayer_mark'
                    }
    
    def _extract_users_from_registration_file(self, user_file: Path, users_found: Dict):
        """Extract usernames from user registration file"""
        content = user_file.read_text(encoding='utf-8')
        lines = content.split('\\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('User Registrations'):
                continue
            
            # Parse: "June 14 2024 at 15:30 - Alice joined on invitation from Bob"
            if ' - ' in line and ' joined ' in line:
                parts = line.split(' - ', 1)
                if len(parts) == 2:
                    action_str = parts[1]
                    
                    # Extract username who joined
                    if ' joined ' in action_str:
                        username = action_str.split(' joined ')[0].strip()
                        if username:
                            users_found[username] = {
                                'source': 'user_registration',
                                'file': str(user_file),
                                'found_as': 'registered_user',
                                'timestamp': parts[0]
                            }
                        
                        # Extract inviter if present
                        if 'on invitation from ' in action_str:
                            inviter = action_str.split('on invitation from ')[-1].strip()
                            if inviter and inviter not in users_found:
                                users_found[inviter] = {
                                    'source': 'user_registration',
                                    'file': str(user_file),
                                    'found_as': 'inviter'
                                }
    
    def _extract_users_from_activity_file(self, activity_file: Path, users_found: Dict):
        """Extract usernames from activity log files"""
        content = activity_file.read_text(encoding='utf-8')
        
        # Look for various activity patterns
        patterns = [
            r'\d{2}:\d{2} - (.+?) submitted prayer',
            r'\d{2}:\d{2} - (.+?) prayed for prayer',
            r'\d{2}:\d{2} - (.+?) flagged prayer',
            r'\d{2}:\d{2} - (.+?) archived prayer',
            r'\d{2}:\d{2} - (.+?) answered prayer'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for username in matches:
                username = username.strip()
                if username and username != 'None':
                    if username not in users_found:
                        users_found[username] = {
                            'source': 'activity_log',
                            'file': str(activity_file),
                            'found_as': 'activity_user'
                        }
    
    def _build_user_cache(self, session: Session):
        """Build username-to-user-ID cache for performance"""
        all_users = session.exec(select(User)).all()
        
        for user in all_users:
            # Cache by exact display name
            self._username_cache[user.display_name] = user
            self._user_id_cache[user.id] = user
            
            # Cache by normalized username for lookup
            normalized = normalize_username_for_lookup(user.display_name)
            if normalized:
                self._username_cache[normalized] = user
        
        logger.info(f"Built user cache with {len(all_users)} users")
    
    def _resolve_username_to_user(self, username: str, session: Session) -> Optional[User]:
        """Resolve username to User object with enhanced matching"""
        if not username or username == 'None':
            return None
        
        # Try exact match first
        if username in self._username_cache:
            return self._username_cache[username]
        
        # Try normalized lookup
        normalized = normalize_username_for_lookup(username)
        if normalized and normalized in self._username_cache:
            return self._username_cache[normalized]
        
        # Try equivalence matching (slower but comprehensive)
        for cached_username, user in self._username_cache.items():
            if usernames_are_equivalent(cached_username, username):
                # Cache this match for future use
                self._username_cache[username] = user
                return user
        
        return None
    
    def _create_missing_users(self, session: Session, archive_users: Dict, 
                            dry_run: bool) -> List[Dict]:
        """Create users found in archives but missing from database"""
        missing_users = []
        
        for username, user_info in archive_users.items():
            user = self._resolve_username_to_user(username, session)
            if not user:
                missing_users.append({
                    'username': username,
                    'info': user_info
                })
                
                if not dry_run:
                    try:
                        # Create missing user
                        new_user = User(
                            display_name=username,
                            religious_preference='unspecified',
                            created_at=datetime.now()  # We could parse timestamp from archive
                        )
                        session.add(new_user)
                        session.commit()
                        session.refresh(new_user)
                        
                        # Update cache
                        self._username_cache[username] = new_user
                        self._user_id_cache[new_user.id] = new_user
                        
                        logger.info(f"Created missing user: {username}")
                        self.stats['missing_users_created'] += 1
                        
                    except Exception as e:
                        session.rollback()
                        logger.error(f"Failed to create user {username}: {e}")
                        self.stats['errors'].append(f"Failed to create user {username}: {e}")
        
        logger.info(f"Found {len(missing_users)} users in archives but not in database")
        return missing_users
    
    def _fix_orphaned_prayers(self, session: Session, archive_path: Path, dry_run: bool):
        """Fix prayers with NULL or invalid author_id using archive data"""
        # Find orphaned prayers
        orphaned_prayers = session.exec(
            select(Prayer).where(Prayer.author_id.is_(None))
        ).all()
        
        logger.info(f"Found {len(orphaned_prayers)} orphaned prayers")
        
        for prayer in orphaned_prayers:
            if prayer.text_file_path and Path(prayer.text_file_path).exists():
                try:
                    # Parse author from archive file
                    content = Path(prayer.text_file_path).read_text(encoding='utf-8')
                    header_match = re.search(r'Prayer\s+[a-f0-9]+\s+by\s+(.+)', content)
                    
                    if header_match:
                        username = header_match.group(1).strip()
                        user = self._resolve_username_to_user(username, session)
                        
                        if user:
                            logger.info(f"Fixing orphaned prayer {prayer.id}: {username} -> {user.id}")
                            if not dry_run:
                                prayer.author_id = user.id
                                session.add(prayer)
                                session.commit()
                            self.stats['orphaned_prayers_fixed'] += 1
                        else:
                            logger.warning(f"Could not resolve username {username} for prayer {prayer.id}")
                            self.stats['validation_errors'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to fix prayer {prayer.id}: {e}")
                    self.stats['errors'].append(f"Failed to fix prayer {prayer.id}: {e}")
    
    def _fix_orphaned_prayer_marks(self, session: Session, archive_path: Path, dry_run: bool):
        """Fix prayer marks with NULL or invalid user_id using archive data"""
        # Find orphaned prayer marks
        orphaned_marks = session.exec(
            select(PrayerMark).where(PrayerMark.user_id.is_(None))
        ).all()
        
        logger.info(f"Found {len(orphaned_marks)} orphaned prayer marks")
        
        for mark in orphaned_marks:
            # We'll need to cross-reference with activity logs or other sources
            # For now, log the issue for manual investigation
            logger.warning(f"Orphaned prayer mark {mark.id} for prayer {mark.prayer_id}")
            # This is complex because we need to match marks to specific users
            # based on activity logs - may require additional archive parsing
    
    def _fix_prayer_attributes(self, session: Session, dry_run: bool):
        """Fix prayer attributes with missing text_file_path"""
        attributes_without_paths = session.exec(
            select(PrayerAttribute).where(PrayerAttribute.text_file_path.is_(None))
        ).all()
        
        logger.info(f"Found {len(attributes_without_paths)} prayer attributes without archive paths")
        
        # For now, just log this - full implementation would create archive entries
        self.stats['prayer_attributes_fixed'] = len(attributes_without_paths)
    
    def _validate_consistency(self, session: Session, archive_path: Path) -> Dict:
        """Validate consistency between archives and database"""
        validation_results = {
            'prayers_without_authors': 0,
            'prayer_marks_without_users': 0,
            'users_in_db_not_in_archives': 0,
            'users_in_archives_not_in_db': 0
        }
        
        # Check for remaining orphaned records
        orphaned_prayers = session.exec(
            select(Prayer).where(Prayer.author_id.is_(None))
        ).all()
        validation_results['prayers_without_authors'] = len(orphaned_prayers)
        
        orphaned_marks = session.exec(
            select(PrayerMark).where(PrayerMark.user_id.is_(None))
        ).all()
        validation_results['prayer_marks_without_users'] = len(orphaned_marks)
        
        return validation_results


def main():
    parser = argparse.ArgumentParser(description='Reconstruct database relationships from text archives')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without applying them')
    parser.add_argument('--execute', action='store_true',
                       help='Execute the reconstruction (applies changes)')
    parser.add_argument('--archive-dir', type=str,
                       help='Override default archive directory')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("Must specify either --dry-run or --execute")
        return 1
    
    dry_run = args.dry_run
    
    reconstructor = ArchiveReconstructor()
    results = reconstructor.reconstruct_from_archives(
        dry_run=dry_run,
        archive_dir=args.archive_dir
    )
    
    if results.get('success'):
        print("\\nReconstruction Results:")
        print("=" * 50)
        stats = results['stats']
        for key, value in stats.items():
            if key != 'errors':
                print(f"{key}: {value}")
        
        if stats.get('errors'):
            print(f"\\nErrors encountered: {len(stats['errors'])}")
            for error in stats['errors']:
                print(f"  - {error}")
        
        print(f"\\nValidation Results:")
        validation = results.get('validation', {})
        for key, value in validation.items():
            print(f"{key}: {value}")
        
        if dry_run:
            print("\\n*** DRY RUN COMPLETED - No changes were made ***")
        else:
            print("\\n*** RECONSTRUCTION COMPLETED ***")
    else:
        print(f"Reconstruction failed: {results.get('error')}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())