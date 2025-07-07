"""
Archive-First Service

This service implements the archive-first data flow where text archives are
written FIRST, then database records are created with references to the archives.
This ensures text files are always the authoritative source of truth.
"""

from datetime import datetime
from typing import Dict, Optional, Tuple
from sqlmodel import Session

from models import engine, Prayer, User, PrayerMark, PrayerAttribute, PrayerActivityLog
from app_helpers.services.text_archive_service import text_archive_service
import logging

logger = logging.getLogger(__name__)


def create_prayer_with_text_archive(prayer_data: Dict) -> Tuple[Prayer, str]:
    """
    Create prayer using archive-first approach:
    1. Write to text archive FIRST (creates authoritative record)
    2. Create database record pointing to archive file
    
    Args:
        prayer_data: Dictionary containing prayer information
        - author_id: User ID of prayer author
        - author_display_name: Display name for archive
        - text: Original prayer request text
        - generated_prayer: LLM-generated prayer
        - project_tag: Optional project tag
        - created_at: Optional timestamp (defaults to now)
    
    Returns:
        Tuple of (Prayer record, archive file path)
    """
    
    # Step 1: Write authoritative text archive FIRST
    archive_data = {
        'id': 'temp',  # Will be replaced with actual ID after database creation
        'author': prayer_data['author_display_name'],
        'text': prayer_data['text'],
        'generated_prayer': prayer_data.get('generated_prayer'),
        'project_tag': prayer_data.get('project_tag'),
        'created_at': prayer_data.get('created_at', datetime.now())
    }
    
    # Create archive file with temporary ID
    temp_file_path = text_archive_service.create_prayer_archive(archive_data)
    
    # Step 2: Create database record pointing to archive file
    with Session(engine) as s:
        prayer = Prayer(
            author_username=prayer_data['author_username'],
            text=prayer_data['text'],
            generated_prayer=prayer_data.get('generated_prayer'),
            project_tag=prayer_data.get('project_tag'),
            text_file_path=temp_file_path,  # Critical: track source archive
            created_at=prayer_data.get('created_at', datetime.now())
        )
        s.add(prayer)
        s.commit()
        s.refresh(prayer)  # Get the actual database ID
    
        # Step 3: Update archive file with actual prayer ID
        if temp_file_path:
            try:
                # Read the temporary file content
                content = text_archive_service.read_archive_file(temp_file_path)
                
                # Replace temporary ID with actual ID
                updated_content = content.replace("Prayer temp by", f"Prayer {prayer.id} by")
                
                # Write updated content
                text_archive_service._write_file_atomic(temp_file_path, updated_content)
                
                logger.info(f"Created prayer {prayer.id} with archive: {temp_file_path}")
                
            except Exception as e:
                logger.error(f"Failed to update prayer archive with actual ID: {e}")
    
    # Log to monthly activity
    if text_archive_service.enabled:
        text_archive_service.append_monthly_activity(
            f"submitted prayer {prayer.id}",
            prayer_data['author_display_name'],
            prayer.id,
            prayer_data.get('project_tag', '')
        )
    
    return prayer, temp_file_path


def append_prayer_activity_with_archive(prayer_id: str, action: str, user: User, extra: str = "") -> None:
    """
    Append prayer activity using archive-first approach:
    1. Write to text archive FIRST
    2. Create database record with same archive reference
    
    Args:
        prayer_id: ID of the prayer
        action: Type of action ('prayed', 'answered', 'testimony', etc.)
        user: User performing the action
        extra: Extra data (testimony text, etc.)
    """
    
    with Session(engine) as s:
        # Get the prayer record to find its text archive
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise ValueError(f"Prayer {prayer_id} not found")
        
        if not prayer.text_file_path:
            # Create missing archive file for legacy/test prayers
            logger.info(f"Prayer {prayer_id} missing text archive - creating one now")
            
            # Get prayer author for archive
            author = s.get(User, prayer.author_username)
            author_name = author.display_name if author else "Unknown"
            
            # Create archive data from database prayer
            archive_data = {
                'id': prayer.id,
                'author': author_name,
                'text': prayer.text,
                'generated_prayer': prayer.generated_prayer,
                'project_tag': prayer.project_tag,
                'created_at': prayer.created_at
            }
            
            # Create the archive file (if text archives are enabled)
            if text_archive_service.enabled:
                archive_file_path = text_archive_service.create_prayer_archive(archive_data)
                
                # Update prayer record with archive path
                prayer.text_file_path = archive_file_path
                s.add(prayer)
                s.commit()
                
                logger.info(f"Created archive file for prayer {prayer_id}: {archive_file_path}")
            else:
                # In test environment or when archives are disabled, just set a placeholder
                prayer.text_file_path = f"disabled_archive_for_prayer_{prayer_id}"
                s.add(prayer)
                s.commit()
                logger.info(f"Text archives disabled - set placeholder path for prayer {prayer_id}")
        
        # Step 1: Write to text archive FIRST (if enabled)
        if text_archive_service.enabled and not prayer.text_file_path.startswith("disabled_archive_"):
            text_archive_service.append_prayer_activity(
                prayer.text_file_path, 
                action, 
                user.display_name, 
                extra
            )
        
        # Step 2: Create database record with same archive path
        if action == "prayed":
            # Create PrayerMark record
            prayer_mark = PrayerMark(
                prayer_id=prayer_id,
                username=user.display_name,
                text_file_path=prayer.text_file_path,  # Same archive path
                created_at=datetime.now()
            )
            s.add(prayer_mark)
            
        elif action in ["answered", "archived", "flagged"]:
            # Create or update PrayerAttribute
            prayer.set_attribute(action, "true", user.display_name, s)
            
            # For answered prayers, also set the answer date
            if action == "answered":
                answer_date = datetime.now().isoformat()
                prayer.set_attribute("answer_date", answer_date, user.display_name, s)
            
            # Set testimony if provided with answered action
            if action == "answered" and extra:
                prayer.set_attribute("answer_testimony", extra, user.display_name, s)
                
                # Also append testimony to the prayer's text archive file
                if text_archive_service.enabled and not prayer.text_file_path.startswith("disabled_archive_"):
                    text_archive_service.append_prayer_activity(
                        prayer.text_file_path,
                        "testimony",
                        user.display_name,
                        extra
                    )
                
                # Create separate testimony activity log
                testimony_log = PrayerActivityLog(
                    prayer_id=prayer_id,
                    user_id=user.display_name,
                    action="testimony",
                    old_value=None,
                    new_value=extra,
                    text_file_path=prayer.text_file_path,
                    created_at=datetime.now()
                )
                s.add(testimony_log)
                
        elif action == "restored":
            # Remove archived attribute
            prayer.remove_attribute('archived', s, user.display_name)
        
        # Create activity log entry only for actions that don't already create logs
        # set_attribute already creates logs, so we skip for those actions
        if action in ["prayed"]:  # Only actions that don't use set_attribute
            activity_record = PrayerActivityLog(
                prayer_id=prayer_id,
                user_id=user.display_name,
                action=action,
                old_value=None,
                new_value=extra if extra else "true",
                text_file_path=prayer.text_file_path,  # Same archive path
                created_at=datetime.now()
            )
            s.add(activity_record)
        
        s.commit()
        
        logger.info(f"Added {action} activity for prayer {prayer_id} by {user.display_name}")
    
    # Log to monthly activity
    if text_archive_service.enabled:
        if action == "prayed":
            activity_text = f"prayed for prayer {prayer_id}"
        elif action == "answered":
            activity_text = f"marked prayer {prayer_id} as answered"
        elif action == "testimony":
            activity_text = f"added testimony for prayer {prayer_id}"
        else:
            activity_text = f"{action} prayer {prayer_id}"
            
        text_archive_service.append_monthly_activity(
            activity_text,
            user.display_name,
            prayer_id
        )


def create_user_with_text_archive(user_data: Dict, user_id: str = None) -> Tuple[User, str]:
    """
    Create user using archive-first approach:
    1. Write to text archive FIRST
    2. Create database record pointing to archive file
    
    Args:
        user_data: Dictionary containing user information
        - display_name: User's display name
        - invited_by_display_name: Display name of inviting user (if any)
        - invited_by_username: ID of inviting user
        - invite_token_used: Token used for registration
        user_id: Optional specific ID to use (if None, database will auto-generate)
    
    Returns:
        Tuple of (User record, archive file path)
    """
    
    # Step 1: Write to text archive FIRST
    invite_source = user_data.get('invited_by_display_name', '')
    archive_file_path = text_archive_service.append_user_registration(
        user_data['display_name'],
        invite_source
    )
    
    # Step 2: Create database record pointing to archive file
    with Session(engine) as s:
        user_kwargs = {
            'display_name': user_data['display_name'],
            'invited_by_username': user_data.get('invited_by_username'),
            'invite_token_used': user_data.get('invite_token_used'),
            'text_file_path': archive_file_path,  # Track source archive
            'created_at': datetime.now()
        }
        
        # Note: User model uses display_name as primary key, not separate id field
            
        # Check for existing user with same display_name
        from sqlmodel import select
        existing_user = s.exec(select(User).where(User.display_name == user_data['display_name'])).first()
        
        if existing_user:
            # User already exists - return existing user instead of creating duplicate
            logger.warning(f"User with display_name '{user_data['display_name']}' already exists (ID: {existing_user.display_name}). Returning existing user.")
            return existing_user, existing_user.text_file_path or archive_file_path
        
        try:
            user = User(**user_kwargs)
            s.add(user)
            s.commit()
            s.refresh(user)
        except Exception as e:
            # Handle potential constraint violation or other database errors
            s.rollback()
            # Check if another user was created concurrently
            existing_user = s.exec(select(User).where(User.display_name == user_data['display_name'])).first()
            if existing_user:
                logger.warning(f"Concurrent user creation detected for '{user_data['display_name']}'. Returning existing user.")
                return existing_user, existing_user.text_file_path or archive_file_path
            else:
                # Re-raise if it's not a duplicate user issue
                raise e
    
    logger.info(f"Created user {user.display_name} ({user.display_name}) with archive: {archive_file_path}")
    
    # Log to monthly activity
    if text_archive_service.enabled:
        if invite_source:
            activity_text = f"registered via invitation from {invite_source}"
        else:
            activity_text = "registered directly"
            
        text_archive_service.append_monthly_activity(
            activity_text,
            user_data['display_name']
        )
    
    return user, archive_file_path


def get_prayer_archive_content(prayer_id: str) -> Optional[str]:
    """
    Read the full text archive content for a prayer.
    
    Args:
        prayer_id: ID of the prayer
    
    Returns:
        Archive file content as string, or None if not found
    """
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer or not prayer.text_file_path:
            return None
        
        try:
            return text_archive_service.read_archive_file(prayer.text_file_path)
        except FileNotFoundError:
            logger.error(f"Archive file not found for prayer {prayer_id}: {prayer.text_file_path}")
            return None


def validate_archive_database_consistency(prayer_id: str) -> Dict:
    """
    Validate that database records match their text archive content.
    
    Args:
        prayer_id: ID of prayer to validate
    
    Returns:
        Dictionary with validation results
    """
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            return {'valid': False, 'error': 'Prayer not found in database'}
        
        if not prayer.text_file_path:
            return {'valid': False, 'error': 'Prayer has no archive file reference'}
        
        try:
            # Parse archive content
            archive_data, archive_activities = text_archive_service.parse_prayer_archive(prayer.text_file_path)
            
            # Validate basic prayer data
            issues = []
            
            if archive_data.get('id') != int(prayer_id):
                issues.append(f"ID mismatch: archive={archive_data.get('id')}, db={prayer_id}")
            
            if archive_data.get('original_request') != prayer.text:
                issues.append("Prayer text mismatch between archive and database")
            
            # Count activities
            db_marks = s.query(PrayerMark).filter_by(prayer_id=prayer_id).count()
            archive_prayed_count = sum(1 for a in archive_activities if a['action'] == 'prayed')
            
            if db_marks != archive_prayed_count:
                issues.append(f"Prayer mark count mismatch: archive={archive_prayed_count}, db={db_marks}")
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'archive_activities': len(archive_activities),
                'db_marks': db_marks
            }
            
        except Exception as e:
            return {'valid': False, 'error': f'Failed to read archive: {e}'}


# Convenience function for backward compatibility
def submit_prayer_archive_first(text: str, author: User,
                               generated_prayer: str = None) -> Prayer:
    """
    Submit prayer using archive-first approach - convenience wrapper.
    
    Args:
        text: Prayer request text
        author: User submitting the prayer
        generated_prayer: Pre-generated prayer text
    
    Returns:
        Created Prayer record
    """
    prayer_data = {
        'author_username': author.display_name,
        'author_display_name': author.display_name,
        'text': text,
        'generated_prayer': generated_prayer
    }
    
    prayer, _ = create_prayer_with_text_archive(prayer_data)
    return prayer