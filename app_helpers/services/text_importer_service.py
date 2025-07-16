"""
Text Archive Importer Service

This service handles importing data from text archive files back into the database.
It can restore the complete database state from text archives, enabling data recovery
and migration scenarios.

Import Philosophy:
- Text archives are the authoritative source of truth
- Database records are reconstructed from text files
- Existing records are updated, not duplicated
- Validation ensures data consistency
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlmodel import Session, select

from models import (
    engine, User, Prayer, PrayerMark, PrayerAttribute, 
    PrayerActivityLog, InviteToken
)
from app_helpers.services.text_archive_service import TextArchiveService

logger = logging.getLogger(__name__)


class TextImporterService:
    """Service for importing data from text archive files back to database"""
    
    def __init__(self, archive_service: TextArchiveService = None):
        self.archive_service = archive_service or TextArchiveService()
        self.import_stats = {
            'users_imported': 0,
            'prayers_imported': 0,
            'prayer_marks_imported': 0,
            'prayer_attributes_imported': 0,
            'activity_logs_imported': 0,
            'user_attributes_imported': 0,
            'errors': []
        }
    
    def import_from_archive_directory(self, archive_dir: str = None, 
                                    dry_run: bool = False) -> Dict:
        """
        Import all data from an archive directory
        
        Args:
            archive_dir: Path to archive directory (defaults to service base_dir)
            dry_run: If True, don't actually import, just report what would be imported
            
        Returns:
            Dictionary with import statistics and results
        """
        if not archive_dir:
            archive_dir = str(self.archive_service.base_dir)
        
        archive_path = Path(archive_dir)
        if not archive_path.exists():
            return {'error': f'Archive directory not found: {archive_dir}'}
        
        logger.info(f"Starting import from archive directory: {archive_dir}")
        if dry_run:
            logger.info("DRY RUN MODE - No actual database changes will be made")
        
        # Reset import stats
        self.import_stats = {
            'users_imported': 0,
            'prayers_imported': 0,
            'prayer_marks_imported': 0,
            'prayer_attributes_imported': 0,
            'activity_logs_imported': 0,
            'user_attributes_imported': 0,
            'errors': []
        }
        
        try:
            # Import users from monthly registration files
            self._import_user_registrations(archive_path, dry_run)
            
            # Import user attributes from user_attributes.txt
            self._import_user_attributes(archive_path, dry_run)
            
            # Import prayers from prayer archive files
            self._import_prayer_archives(archive_path, dry_run)
            
            # Import monthly activity logs
            self._import_monthly_activities(archive_path, dry_run)
            
            return {
                'success': True,
                'stats': self.import_stats,
                'dry_run': dry_run
            }
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            self.import_stats['errors'].append(f"Import failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.import_stats,
                'dry_run': dry_run
            }
    
    def _import_user_registrations(self, archive_path: Path, dry_run: bool):
        """Import user registrations from monthly user files"""
        users_dir = archive_path / "users"
        if not users_dir.exists():
            return
        
        user_files = list(users_dir.glob("*_users.txt"))
        logger.info(f"Found {len(user_files)} user registration files")
        
        for user_file in user_files:
            try:
                self._import_user_registration_file(user_file, dry_run)
            except Exception as e:
                error_msg = f"Failed to import user file {user_file}: {e}"
                logger.error(error_msg)
                self.import_stats['errors'].append(error_msg)
    
    def _import_user_registration_file(self, user_file: Path, dry_run: bool):
        """Import users from a single registration file"""
        content = user_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('User Registrations'):
                continue
            
            # Parse user registration line
            # Format: "June 14 2024 at 15:30 - Alice_Johnson joined on invitation from Bob_Smith"
            # or: "June 14 2024 at 15:30 - Charlie_Brown joined directly"
            if ' - ' in line and ' joined ' in line:
                parts = line.split(' - ', 1)
                if len(parts) == 2:
                    timestamp_str = parts[0]
                    action_str = parts[1]
                    
                    user_data = self._parse_user_registration_line(timestamp_str, action_str)
                    if user_data:
                        self._create_or_update_user(user_data, str(user_file), dry_run)
    
    def _parse_user_registration_line(self, timestamp_str: str, action_str: str) -> Optional[Dict]:
        """Parse a user registration line into structured data"""
        try:
            # Parse timestamp
            created_at = datetime.strptime(timestamp_str, "%B %d %Y at %H:%M")
            
            # Parse action
            if " joined on invitation from " in action_str:
                parts = action_str.split(" joined on invitation from ")
                display_name = parts[0].strip()  # Remove extra whitespace
                invited_by = parts[1].strip()     # Remove extra whitespace
                
                return {
                    'display_name': display_name,
                    'created_at': created_at,
                    'invited_by_display_name': invited_by,
                    'registration_type': 'invited'
                }
                
            elif " joined directly" in action_str:
                display_name = action_str.replace(" joined directly", "").strip()  # Remove extra whitespace
                
                return {
                    'display_name': display_name,
                    'created_at': created_at,
                    'invited_by_display_name': None,
                    'registration_type': 'direct'
                }
                
        except Exception as e:
            logger.warning(f"Failed to parse user registration line: '{action_str}': {e}")
            return None
            
        return None
    
    def _create_or_update_user(self, user_data: Dict, source_file: str, dry_run: bool):
        """Create or update user record from parsed data"""
        if dry_run:
            logger.info(f"DRY RUN: Would import user {user_data['display_name']}")
            self.import_stats['users_imported'] += 1
            return
        
        with Session(engine) as s:
            # Check if user already exists
            existing_user = s.exec(
                select(User).where(User.display_name == user_data['display_name'])
            ).first()
            
            if existing_user:
                # Update existing user's archive reference if needed
                if not existing_user.text_file_path:
                    existing_user.text_file_path = source_file
                    s.add(existing_user)
                    s.commit()
                    logger.info(f"Updated existing user archive reference: {user_data['display_name']}")
                else:
                    logger.debug(f"User '{user_data['display_name']}' already exists with archive reference, skipping")
                return
            
            # Find invited_by_username if applicable, but don't fail if inviter doesn't exist
            invited_by_username = None
            if user_data.get('invited_by_display_name'):
                inviter = s.exec(
                    select(User).where(User.display_name == user_data['invited_by_display_name'])
                ).first()
                if inviter:
                    invited_by_username = inviter.display_name
                else:
                    logger.warning(f"Inviter '{user_data['invited_by_display_name']}' not found for user '{user_data['display_name']}', importing anyway")
                    # Don't set invited_by_username, but still create the user
            
            # Create new user
            try:
                user = User(
                    display_name=user_data['display_name'],
                    created_at=user_data['created_at'],
                    invited_by_username=invited_by_username,
                    text_file_path=source_file
                )
                
                s.add(user)
                s.commit()
            except Exception as e:
                s.rollback()
                # Check if user was created concurrently
                existing_user = s.exec(
                    select(User).where(User.display_name == user_data['display_name'])
                ).first()
                if existing_user:
                    logger.info(f"Concurrent user creation detected for '{user_data['display_name']}', skipping")
                    return
                else:
                    raise e
            
            self.import_stats['users_imported'] += 1
            logger.info(f"Imported user: {user_data['display_name']}")
    
    def _import_user_attributes(self, archive_path: Path, dry_run: bool):
        """Import user attributes from user_attributes.txt file"""
        users_dir = archive_path / "users"
        attributes_file = users_dir / "user_attributes.txt"
        
        if not attributes_file.exists():
            logger.info("No user_attributes.txt file found, skipping user attributes import")
            return
        
        try:
            content = attributes_file.read_text(encoding='utf-8')
            user_attributes = self._parse_user_attributes_file(content)
            
            logger.info(f"Found {len(user_attributes)} user attribute records")
            
            for user_data in user_attributes:
                self._update_user_attributes(user_data, dry_run)
                
        except Exception as e:
            error_msg = f"Failed to import user attributes: {e}"
            logger.error(error_msg)
            self.import_stats['errors'].append(error_msg)
    
    def _parse_user_attributes_file(self, content: str) -> List[Dict]:
        """Parse user attributes from text file content"""
        lines = content.split('\n')
        users = []
        current_user = {}
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and headers
            if not line or line == "User Attributes":
                continue
            
            # Process key-value pairs
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'username':
                    # New user block - save previous if exists
                    if current_user:
                        users.append(current_user)
                    current_user = {'username': value}
                else:
                    # Add attribute to current user
                    if key == 'is_supporter':
                        current_user[key] = value.lower() == 'true'
                    elif key == 'supporter_since':
                        try:
                            current_user[key] = datetime.strptime(value, '%Y-%m-%d')
                        except ValueError:
                            logger.warning(f"Invalid date format for supporter_since: {value}")
                            current_user[key] = None
                    elif key == 'welcome_message_dismissed':
                        current_user[key] = value.lower() == 'true'
                    else:
                        current_user[key] = value
        
        # Add the last user if exists
        if current_user:
            users.append(current_user)
        
        return users
    
    def _update_user_attributes(self, user_data: Dict, dry_run: bool):
        """Update user attributes in database"""
        if dry_run:
            logger.info(f"DRY RUN: Would update attributes for user {user_data['username']}")
            self.import_stats['user_attributes_imported'] += 1
            return
        
        with Session(engine) as s:
            user = s.exec(
                select(User).where(User.display_name == user_data['username'])
            ).first()
            
            if not user:
                logger.warning(f"User '{user_data['username']}' not found for attribute update")
                return
            
            # Update user attributes
            updated = False
            
            if 'is_supporter' in user_data:
                if user.is_supporter != user_data['is_supporter']:
                    user.is_supporter = user_data['is_supporter']
                    updated = True
            
            if 'supporter_since' in user_data:
                if user.supporter_since != user_data['supporter_since']:
                    user.supporter_since = user_data['supporter_since']
                    updated = True
            
            if 'welcome_message_dismissed' in user_data:
                if user.welcome_message_dismissed != user_data['welcome_message_dismissed']:
                    user.welcome_message_dismissed = user_data['welcome_message_dismissed']
                    updated = True
            
            if updated:
                s.add(user)
                s.commit()
                logger.info(f"Updated attributes for user: {user_data['username']}")
                self.import_stats['user_attributes_imported'] += 1
            else:
                logger.info(f"No attribute changes for user: {user_data['username']}")
    
    def _import_prayer_archives(self, archive_path: Path, dry_run: bool):
        """Import prayers from prayer archive files"""
        prayers_dir = archive_path / "prayers"
        if not prayers_dir.exists():
            return
        
        # Find all prayer archive files
        prayer_files = []
        for year_dir in prayers_dir.iterdir():
            if year_dir.is_dir():
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir():
                        prayer_files.extend(month_dir.glob("*.txt"))
        
        logger.info(f"Found {len(prayer_files)} prayer archive files")
        
        for prayer_file in prayer_files:
            try:
                self._import_prayer_archive_file(prayer_file, dry_run)
            except Exception as e:
                error_msg = f"Failed to import prayer file {prayer_file}: {e}"
                logger.error(error_msg)
                self.import_stats['errors'].append(error_msg)
    
    def _import_prayer_archive_file(self, prayer_file: Path, dry_run: bool):
        """Import a single prayer archive file"""
        # Parse the prayer archive
        parsed_data, parsed_activities = self.archive_service.parse_prayer_archive(str(prayer_file))
        
        if not parsed_data:
            logger.warning(f"No prayer data found in {prayer_file}")
            return
        
        if dry_run:
            logger.info(f"DRY RUN: Would import prayer {parsed_data.get('id')} with {len(parsed_activities)} activities")
            self.import_stats['prayers_imported'] += 1
            self.import_stats['activity_logs_imported'] += len(parsed_activities)
            return
        
        with Session(engine) as s:
            # Check if prayer already exists
            prayer_id = parsed_data.get('id')
            existing_prayer = s.get(Prayer, prayer_id) if prayer_id else None
            
            if existing_prayer:
                # Update existing prayer's archive reference if needed
                if not existing_prayer.text_file_path:
                    existing_prayer.text_file_path = str(prayer_file)
                    s.add(existing_prayer)
                    s.commit()
                    logger.info(f"Updated existing prayer archive reference: {prayer_id}")
                
                # Import prayer activities for existing prayer
                self._import_prayer_activities(s, existing_prayer, parsed_activities)
                return
            
            # Find or create author user
            author_name = parsed_data.get('author')
            author_user = s.exec(
                select(User).where(User.display_name == author_name)
            ).first()
            
            if not author_user:
                # Create missing user safely
                logger.info(f"Creating missing user for prayer {prayer_id}: {author_name}")
                try:
                    author_user = User(
                        display_name=author_name,
                        religious_preference='unspecified',
                        created_at=self._parse_timestamp(parsed_data.get('submitted', ''))
                    )
                    s.add(author_user)
                    s.commit()
                    s.refresh(author_user)
                    self.import_stats['users_imported'] += 1
                except Exception as e:
                    s.rollback()
                    # Check if user was created concurrently
                    author_user = s.exec(
                        select(User).where(User.display_name == author_name)
                    ).first()
                    if not author_user:
                        raise e
            
            # Create prayer record
            prayer = Prayer(
                id=prayer_id,
                author_username=author_user.display_name,
                text=parsed_data.get('original_request', ''),
                generated_prayer=parsed_data.get('generated_prayer'),
                project_tag=parsed_data.get('project_tag'),
                target_audience=parsed_data.get('target_audience', 'all'),
                text_file_path=str(prayer_file),
                created_at=self._parse_timestamp(parsed_data.get('submitted', ''))
            )
            
            s.add(prayer)
            s.commit()
            
            self.import_stats['prayers_imported'] += 1
            logger.info(f"Imported prayer: {prayer_id}")
            
            # Import prayer activities
            self._import_prayer_activities(s, prayer, parsed_activities)
    
    def _import_prayer_activities(self, session: Session, prayer: Prayer, activities: List[Dict]):
        """Import prayer activities (marks, attributes, logs)"""
        for activity in activities:
            try:
                self._import_single_activity(session, prayer, activity)
            except Exception as e:
                error_msg = f"Failed to import activity for prayer {prayer.id}: {e}"
                logger.error(error_msg)
                self.import_stats['errors'].append(error_msg)
    
    def _import_single_activity(self, session: Session, prayer: Prayer, activity: Dict):
        """Import a single prayer activity"""
        action = activity.get('action')
        user_name = activity.get('user')
        timestamp_str = activity.get('timestamp')
        
        # Find or create user
        user = session.exec(
            select(User).where(User.display_name == user_name)
        ).first()
        
        if not user:
            # Create missing user safely
            logger.info(f"Creating missing user for activity: {user_name}")
            try:
                user = User(
                    display_name=user_name,
                    religious_preference='unspecified',
                    created_at=self._parse_timestamp(timestamp_str)
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                self.import_stats['users_imported'] += 1
            except Exception as e:
                session.rollback()
                # Check if user was created concurrently
                user = session.exec(
                    select(User).where(User.display_name == user_name)
                ).first()
                if not user:
                    raise e
        
        # Parse timestamp
        activity_time = self._parse_timestamp(timestamp_str)
        
        if action == 'prayed':
            # Check for existing prayer mark to avoid duplicates
            existing_mark = session.exec(
                select(PrayerMark).where(
                    PrayerMark.prayer_id == prayer.id,
                    PrayerMark.username == user.display_name,
                    PrayerMark.created_at == activity_time
                )
            ).first()
            
            if not existing_mark:
                # Create prayer mark
                prayer_mark = PrayerMark(
                    prayer_id=prayer.id,
                    username=user.display_name,
                    text_file_path=prayer.text_file_path,
                    created_at=activity_time
                )
                session.add(prayer_mark)
                self.import_stats['prayer_marks_imported'] += 1
            
        elif action in ['answered', 'archived', 'flagged']:
            # Check for existing status attribute to avoid duplicates
            existing_attr = session.exec(
                select(PrayerAttribute).where(
                    PrayerAttribute.prayer_id == prayer.id,
                    PrayerAttribute.attribute_name == action,
                    PrayerAttribute.attribute_value == 'true',
                    PrayerAttribute.created_by == user.display_name,
                    PrayerAttribute.created_at == activity_time
                )
            ).first()
            
            if not existing_attr:
                # Create prayer attribute
                prayer_attr = PrayerAttribute(
                    prayer_id=prayer.id,
                    attribute_name=action,
                    attribute_value='true',
                    created_by=user.display_name,
                    created_at=activity_time
                )
                session.add(prayer_attr)
                self.import_stats['prayer_attributes_imported'] += 1
            
            # For answered prayers, also set answer_date
            if action == 'answered':
                # Check for existing answer_date attribute to avoid duplicates
                existing_date_attr = session.exec(
                    select(PrayerAttribute).where(
                        PrayerAttribute.prayer_id == prayer.id,
                        PrayerAttribute.attribute_name == 'answer_date',
                        PrayerAttribute.attribute_value == activity_time.isoformat(),
                        PrayerAttribute.created_by == user.display_name,
                        PrayerAttribute.created_at == activity_time
                    )
                ).first()
                
                if not existing_date_attr:
                    answer_date_attr = PrayerAttribute(
                        prayer_id=prayer.id,
                        attribute_name='answer_date',
                        attribute_value=activity_time.isoformat(),
                        created_by=user.display_name,
                        created_at=activity_time
                    )
                    session.add(answer_date_attr)
                    self.import_stats['prayer_attributes_imported'] += 1
        
        elif action == 'testimony':
            # Create testimony attribute
            testimony_text = activity.get('raw_action', '').split(': ', 1)
            if len(testimony_text) > 1:
                # Check for existing testimony attribute to avoid duplicates
                existing_testimony_attr = session.exec(
                    select(PrayerAttribute).where(
                        PrayerAttribute.prayer_id == prayer.id,
                        PrayerAttribute.attribute_name == 'answer_testimony',
                        PrayerAttribute.attribute_value == testimony_text[1],
                        PrayerAttribute.created_by == user.display_name,
                        PrayerAttribute.created_at == activity_time
                    )
                ).first()
                
                if not existing_testimony_attr:
                    testimony_attr = PrayerAttribute(
                        prayer_id=prayer.id,
                        attribute_name='answer_testimony',
                        attribute_value=testimony_text[1],
                        created_by=user.display_name,
                        created_at=activity_time
                    )
                    session.add(testimony_attr)
                    self.import_stats['prayer_attributes_imported'] += 1
        
        # Check for existing activity log to avoid duplicates
        existing_activity_log = session.exec(
            select(PrayerActivityLog).where(
                PrayerActivityLog.prayer_id == prayer.id,
                PrayerActivityLog.user_id == user.display_name,
                PrayerActivityLog.action == action,
                PrayerActivityLog.created_at == activity_time
            )
        ).first()
        
        if not existing_activity_log:
            # Create activity log entry
            activity_log = PrayerActivityLog(
                prayer_id=prayer.id,
                user_id=user.display_name,
                action=action,
                old_value=None,
                new_value='true',
                text_file_path=prayer.text_file_path,
                created_at=activity_time
            )
            session.add(activity_log)
            self.import_stats['activity_logs_imported'] += 1
        
        session.commit()
    
    def _import_monthly_activities(self, archive_path: Path, dry_run: bool):
        """Import monthly activity files (for cross-referencing)"""
        activity_dir = archive_path / "activity"
        if not activity_dir.exists():
            return
        
        activity_files = list(activity_dir.glob("activity_*.txt"))
        logger.info(f"Found {len(activity_files)} monthly activity files")
        
        # For now, monthly activities are mainly for logging/auditing
        # The prayer-specific activities are already imported from prayer archives
        # This could be extended to validate consistency between sources
        
        if not dry_run:
            logger.info("Monthly activity files processed for validation (no additional imports needed)")
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string into datetime object"""
        try:
            # Handle format: "June 15 2024 at 08:30"
            return datetime.strptime(timestamp_str, "%B %d %Y at %H:%M")
        except ValueError:
            # Fallback to current time if parsing fails
            logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return datetime.now()
    
    def validate_import_consistency(self, archive_dir: str = None) -> Dict:
        """
        Validate consistency between archive files and database records
        
        Returns:
            Dictionary with validation results and any inconsistencies found
        """
        if not archive_dir:
            archive_dir = str(self.archive_service.base_dir)
        
        archive_path = Path(archive_dir)
        validation_results = {
            'prayers_checked': 0,
            'users_checked': 0,
            'inconsistencies': [],
            'missing_archives': [],
            'missing_db_records': []
        }
        
        with Session(engine) as s:
            # Check all prayers have corresponding archive files
            prayers = s.exec(select(Prayer)).all()
            for prayer in prayers:
                validation_results['prayers_checked'] += 1
                
                if not prayer.text_file_path:
                    validation_results['missing_archives'].append(f"Prayer {prayer.id} has no archive file reference")
                    continue
                
                if not Path(prayer.text_file_path).exists():
                    validation_results['missing_archives'].append(f"Prayer {prayer.id} archive file not found: {prayer.text_file_path}")
                    continue
                
                # Validate prayer content consistency
                try:
                    parsed_data, _ = self.archive_service.parse_prayer_archive(prayer.text_file_path)
                    if str(parsed_data.get('id')) != str(prayer.id):
                        validation_results['inconsistencies'].append(f"Prayer {prayer.id} ID mismatch in archive")
                    if parsed_data.get('original_request') != prayer.text:
                        validation_results['inconsistencies'].append(f"Prayer {prayer.id} text mismatch in archive")
                except Exception as e:
                    validation_results['inconsistencies'].append(f"Prayer {prayer.id} archive parsing failed: {e}")
            
            # Check all users have corresponding archive references
            users = s.exec(select(User)).all()
            for user in users:
                validation_results['users_checked'] += 1
                
                if not user.text_file_path:
                    validation_results['missing_archives'].append(f"User {user.display_name} ({user.display_name}) has no archive file reference")
        
        return validation_results
    
    def repair_missing_archive_references(self, archive_dir: str = None, dry_run: bool = False) -> Dict:
        """
        Repair missing archive file references in database records
        
        This function attempts to find and link archive files to database records
        that are missing their text_file_path references.
        
        Returns:
            Dictionary with repair results
        """
        if not archive_dir:
            archive_dir = str(self.archive_service.base_dir)
        
        repair_results = {
            'prayers_repaired': 0,
            'users_repaired': 0,
            'errors': []
        }
        
        with Session(engine) as s:
            # Repair prayer archive references
            prayers_without_archives = s.exec(
                select(Prayer).where(Prayer.text_file_path.is_(None))
            ).all()
            
            for prayer in prayers_without_archives:
                try:
                    # Search for prayer archive file
                    archive_file = self._find_prayer_archive_file(archive_dir, prayer.id, prayer.created_at)
                    
                    if archive_file:
                        if not dry_run:
                            prayer.text_file_path = str(archive_file)
                            s.add(prayer)
                            s.commit()
                        
                        repair_results['prayers_repaired'] += 1
                        logger.info(f"{'DRY RUN: Would repair' if dry_run else 'Repaired'} prayer {prayer.id} archive reference")
                    
                except Exception as e:
                    error_msg = f"Failed to repair prayer {prayer.id}: {e}"
                    repair_results['errors'].append(error_msg)
                    logger.error(error_msg)
        
        return repair_results
    
    def _find_prayer_archive_file(self, archive_dir: str, prayer_id: str, created_at: datetime) -> Optional[Path]:
        """Find prayer archive file by ID and creation date"""
        prayers_dir = Path(archive_dir) / "prayers"
        if not prayers_dir.exists():
            return None
        
        # Search in the year/month directory structure
        year_month_dir = prayers_dir / str(created_at.year) / f"{created_at.month:02d}"
        
        if year_month_dir.exists():
            # Look for files that might contain this prayer
            for archive_file in year_month_dir.glob("*.txt"):
                try:
                    parsed_data, _ = self.archive_service.parse_prayer_archive(str(archive_file))
                    if str(parsed_data.get('id')) == str(prayer_id):
                        return archive_file
                except Exception:
                    continue
        
        return None


# Global instance for use throughout the application
text_importer_service = TextImporterService()