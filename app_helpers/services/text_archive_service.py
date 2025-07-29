"""
Text Archive Service

This service handles writing and reading the primary text archive files that serve as
the authoritative data store for the ThyWill prayer application. Text archives are
human-readable, append-friendly files that contain all essential site data.

Archive-First Philosophy:
- Text files are written FIRST, then database records are created
- Database records always reference their source text archive file
- Text archives can recreate the entire database if needed
"""

import os
import fcntl
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

# Import configuration (will be set when app starts)
try:
    from app import TEXT_ARCHIVE_ENABLED, TEXT_ARCHIVE_BASE_DIR, TEXT_ARCHIVE_COMPRESSION_AFTER_DAYS
except ImportError:
    # Fallback defaults for testing - NEVER use production directory
    import os
    TEXT_ARCHIVE_ENABLED = os.getenv('TEXT_ARCHIVE_ENABLED', 'true').lower() == 'true'
    TEXT_ARCHIVE_BASE_DIR = os.getenv('TEXT_ARCHIVE_BASE_DIR', '/tmp/test_archives_fallback')
    TEXT_ARCHIVE_COMPRESSION_AFTER_DAYS = int(os.getenv('TEXT_ARCHIVE_COMPRESSION_AFTER_DAYS', '365'))


class TextArchiveService:
    """Primary service for managing text archive files"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or TEXT_ARCHIVE_BASE_DIR)
        self.enabled = TEXT_ARCHIVE_ENABLED
        
        if self.enabled:
            self.base_dir.mkdir(exist_ok=True)
            
            # Create directory structure
            (self.base_dir / "prayers").mkdir(exist_ok=True)
            (self.base_dir / "users").mkdir(exist_ok=True)
            (self.base_dir / "activity").mkdir(exist_ok=True)
    
    def generate_prayer_filename(self, created_at: datetime, prayer_id: int) -> str:
        """Generate unique prayer filename with conflict resolution"""
        base_name = created_at.strftime("%Y_%m_%d_prayer_at_%H%M")
        year_month_dir = self.base_dir / "prayers" / str(created_at.year) / f"{created_at.month:02d}"
        year_month_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = year_month_dir / f"{base_name}.txt"
        
        # Handle conflicts by appending number
        counter = 2
        while file_path.exists():
            conflict_name = f"{base_name}_{counter}"
            file_path = year_month_dir / f"{conflict_name}.txt"
            counter += 1
        
        return str(file_path)
    
    def create_prayer_archive(self, prayer_data: Dict) -> str:
        """Create new prayer archive file with initial content"""
        if not self.enabled:
            return ""
            
        created_at = prayer_data.get('created_at', datetime.now())
        file_path = self.generate_prayer_filename(created_at, prayer_data['id'])
        
        # Format timestamps consistently
        submitted_time = created_at.strftime("%B %d %Y at %H:%M")
        
        # Build prayer archive content
        content = []
        content.append(f"Prayer {prayer_data['id']} by {prayer_data['author']}")
        content.append(f"Submitted {submitted_time}")
        
        if prayer_data.get('project_tag'):
            content.append(f"Project: {prayer_data['project_tag']}")
        
        if prayer_data.get('target_audience'):
            content.append(f"Audience: {prayer_data['target_audience']}")
        
        # Add categorization metadata if present
        categorization = prayer_data.get('categorization')
        if categorization:
            content.append(f"Safety Score: {categorization.get('safety_score', 1.0)}")
            content.append(f"Safety Flags: {json.dumps(categorization.get('safety_flags', []))}")
            content.append(f"Category: {categorization.get('subject_category', 'general')}")
            content.append(f"Specificity: {categorization.get('specificity_type', 'unknown')}")
            content.append(f"Categorization Method: {categorization.get('categorization_method', 'default')}")
            content.append(f"Categorization Confidence: {categorization.get('categorization_confidence', 0.0)}")
        
        content.append("")  # Blank line
        content.append(prayer_data['text'])  # Original request
        content.append("")  # Blank line
        
        if prayer_data.get('generated_prayer'):
            content.append("Generated Prayer:")
            content.append(prayer_data['generated_prayer'])
            content.append("")  # Blank line
        
        content.append("Activity:")
        content.append("")  # Ready for future activity
        
        # Write file atomically
        self._write_file_atomic(file_path, '\n'.join(content))
        
        logger.info(f"Created prayer archive: {file_path}")
        return file_path
    
    def parse_prayer_archive_categorization(self, archive_path: str) -> Dict:
        """Parse categorization metadata from prayer archive file"""
        if not self.enabled or not archive_path or not Path(archive_path).exists():
            # Return defaults for missing archives
            from app_helpers.services.prayer_categorization_service import DEFAULT_CATEGORIZATION
            return DEFAULT_CATEGORIZATION.copy()
        
        try:
            with open(archive_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            categorization = {}
            
            for line in lines:
                line = line.strip()
                if ':' not in line:
                    continue
                
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                try:
                    if key == 'Safety Score':
                        categorization['safety_score'] = float(value)
                    elif key == 'Safety Flags':
                        categorization['safety_flags'] = json.loads(value) if value != '[]' else []
                    elif key == 'Category':
                        categorization['subject_category'] = value
                    elif key == 'Specificity':
                        categorization['specificity_type'] = value
                    elif key == 'Categorization Method':
                        categorization['categorization_method'] = value
                    elif key == 'Categorization Confidence':
                        categorization['categorization_confidence'] = float(value)
                except (ValueError, json.JSONDecodeError) as e:
                    logger.warning(f"Failed to parse categorization field '{key}' from {archive_path}: {e}")
                    continue
            
            # Apply defaults for missing fields (backward compatibility)
            from app_helpers.services.prayer_categorization_service import DEFAULT_CATEGORIZATION
            for field, default_value in DEFAULT_CATEGORIZATION.items():
                if field not in categorization:
                    categorization[field] = default_value
            
            return categorization
            
        except Exception as e:
            logger.error(f"Failed to parse categorization from archive {archive_path}: {e}")
            from app_helpers.services.prayer_categorization_service import DEFAULT_CATEGORIZATION
            return DEFAULT_CATEGORIZATION.copy()
    
    def append_prayer_activity(self, file_path: str, action: str, user: str, extra: str = "", old_value: str = None, new_value: str = None):
        """Append activity to prayer archive file with complete metadata"""
        if not self.enabled or not file_path:
            return
            
        timestamp = datetime.now().strftime("%B %d %Y at %H:%M")
        
        self._append_activity_with_timestamp(file_path, action, user, timestamp, extra, old_value, new_value)
    
    def append_prayer_activity_with_timestamp(self, file_path: str, action: str, user: str, activity_timestamp: datetime, extra: str = "", old_value: str = None, new_value: str = None):
        """Append activity to prayer archive file with historical timestamp"""
        if not self.enabled or not file_path:
            return
            
        timestamp = activity_timestamp.strftime("%B %d %Y at %H:%M")
        
        self._append_activity_with_timestamp(file_path, action, user, timestamp, extra, old_value, new_value)
    
    def _append_activity_with_timestamp(self, file_path: str, action: str, user: str, timestamp: str, extra: str = "", old_value: str = None, new_value: str = None):
        """Internal method to append activity with formatted timestamp"""
        
        # Format activity line based on action type
        if action == "prayed":
            activity_line = f"{timestamp} - {user} prayed this prayer"
        elif action == "answered":
            activity_line = f"{timestamp} - {user} marked this prayer as answered"
        elif action == "testimony":
            activity_line = f"{timestamp} - {user} added testimony: {extra}"
        elif action == "archived":
            activity_line = f"{timestamp} - {user} archived this prayer"
        elif action == "restored":
            activity_line = f"{timestamp} - {user} restored this prayer"
        elif action == "flagged":
            activity_line = f"{timestamp} - {user} flagged this prayer"
        elif action.startswith("set_") or action.startswith("remove_"):
            # Attribute changes with old/new values for complete audit trail
            attribute_name = action.replace("set_", "").replace("remove_", "")
            if action.startswith("set_"):
                if old_value:
                    activity_line = f"{timestamp} - {user} set {attribute_name} from '{old_value}' to '{new_value}'"
                else:
                    activity_line = f"{timestamp} - {user} set {attribute_name} to '{new_value}'"
            else:  # remove_
                activity_line = f"{timestamp} - {user} removed {attribute_name} (was '{old_value}')"
        else:
            activity_line = f"{timestamp} - {user} {action}"
            if extra:
                activity_line += f": {extra}"
        
        self._append_to_file(file_path, activity_line)
        logger.info(f"Added activity to {file_path}: {action} by {user}")
    
    def append_user_registration(self, user_name: str, invite_source: str = ""):
        """Append user registration to monthly user file"""
        if not self.enabled:
            return ""
            
        now = datetime.now()
        return self.append_user_registration_with_timestamp(user_name, invite_source, now)
    
    def append_user_registration_with_timestamp(self, user_name: str, invite_source: str, registration_time: datetime):
        """Append user registration to monthly user file with historical timestamp"""
        if not self.enabled:
            return ""
            
        timestamp = registration_time.strftime("%B %d %Y at %H:%M")
        monthly_file = self.base_dir / "users" / f"{registration_time.year}_{registration_time.month:02d}_users.txt"
        
        # Create monthly file if it doesn't exist
        if not monthly_file.exists():
            header = f"User Registrations for {registration_time.strftime('%B %Y')}\n\n"
            self._write_file_atomic(str(monthly_file), header)
        
        # Format registration line
        if invite_source:
            registration_line = f"{timestamp} - {user_name} joined on invitation from {invite_source}"
        else:
            registration_line = f"{timestamp} - {user_name} joined directly"
        
        self._append_to_file(str(monthly_file), registration_line)
        logger.info(f"Added user registration: {user_name}")
        
        return str(monthly_file)
    
    def append_monthly_activity(self, action: str, user: str, prayer_id: int = None, tag: str = ""):
        """Append activity to monthly activity file, adding date header if needed"""
        if not self.enabled:
            return ""
            
        now = datetime.now()
        activity_date = now.strftime("%B %d %Y")
        timestamp = now.strftime("%H:%M")
        
        monthly_file = self.base_dir / "activity" / f"activity_{now.year}_{now.month:02d}.txt"
        
        # Create monthly file if it doesn't exist
        if not monthly_file.exists():
            header = f"Activity for {now.strftime('%B %Y')}\n\n"
            self._write_file_atomic(str(monthly_file), header)
        
        # Check if today's date header already exists
        needs_date_header = True
        if monthly_file.exists():
            content = monthly_file.read_text(encoding='utf-8')
            if f"\n{activity_date}\n" in content or content.endswith(f"{activity_date}\n"):
                needs_date_header = False
        
        # Build activity line
        activity_parts = [timestamp, "-", user]
        
        # Format action with prayer ID if provided
        if prayer_id and "prayer" not in action:
            action_with_prayer = action.replace(f" {prayer_id}", f" prayer {prayer_id}")
        else:
            action_with_prayer = action
            
        activity_parts.append(action_with_prayer)
        
        if tag:
            activity_parts.append(f"({tag})")
        
        activity_line = " ".join(activity_parts)
        
        # Append with date header if needed
        lines_to_add = []
        if needs_date_header:
            lines_to_add.append(f"\n{activity_date}")
        lines_to_add.append(activity_line)
        
        self._append_to_file(str(monthly_file), '\n'.join(lines_to_add))
        logger.info(f"Added monthly activity: {action} by {user}")
        
        return str(monthly_file)
    
    def append_prayer_attribute(self, prayer_id: str, attribute_name: str, attribute_value: str, user_id: str = None, created_at: datetime = None):
        """Append prayer attribute change to monthly archive"""
        if not self.enabled:
            return ""
        
        now = created_at or datetime.now()
        monthly_file = self.base_dir / "prayers" / "attributes" / f"{now.year}_{now.month:02d}_attributes.txt"
        
        # Create directory and file if needed
        monthly_file.parent.mkdir(parents=True, exist_ok=True)
        if not monthly_file.exists():
            header = f"Prayer Attributes for {now.strftime('%B %Y')}\n"
            header += "Format: timestamp|prayer_id|attribute_name|attribute_value|user_id\n\n"
            self._write_file_atomic(str(monthly_file), header)
        
        # Format attribute line
        timestamp = now.strftime("%B %d %Y at %H:%M")
        user_part = user_id or "system"
        
        attribute_line = f"{timestamp}|{prayer_id}|{attribute_name}|{attribute_value}|{user_part}"
        
        self._append_to_file(str(monthly_file), attribute_line)
        logger.info(f"Logged prayer attribute: {prayer_id}.{attribute_name} = {attribute_value}")
        
        return str(monthly_file)
    
    def append_prayer_mark(self, prayer_id: str, user_id: str, created_at: datetime = None):
        """Append prayer mark to monthly archive"""
        if not self.enabled:
            return ""
        
        now = created_at or datetime.now()
        monthly_file = self.base_dir / "prayers" / "marks" / f"{now.year}_{now.month:02d}_marks.txt"
        
        # Create directory and file if needed
        monthly_file.parent.mkdir(parents=True, exist_ok=True)
        if not monthly_file.exists():
            header = f"Prayer Marks for {now.strftime('%B %Y')}\n"
            header += "Format: timestamp|prayer_id|user_id\n\n"
            self._write_file_atomic(str(monthly_file), header)
        
        # Format mark line
        timestamp = now.strftime("%B %d %Y at %H:%M")
        
        mark_line = f"{timestamp}|{prayer_id}|{user_id}"
        
        self._append_to_file(str(monthly_file), mark_line)
        logger.info(f"Logged prayer mark: prayer {prayer_id} by user {user_id}")
        
        return str(monthly_file)
    
    def append_prayer_skip(self, prayer_id: str, user_id: str, created_at: datetime = None):
        """Append prayer skip to monthly archive"""
        if not self.enabled:
            return ""
        
        now = created_at or datetime.now()
        monthly_file = self.base_dir / "prayers" / "skips" / f"{now.year}_{now.month:02d}_skips.txt"
        
        # Create directory and file if needed
        monthly_file.parent.mkdir(parents=True, exist_ok=True)
        if not monthly_file.exists():
            header = f"Prayer Skips for {now.strftime('%B %Y')}\n"
            header += "Format: timestamp|prayer_id|user_id\n\n"
            self._write_file_atomic(str(monthly_file), header)
        
        # Format skip line
        timestamp = now.strftime("%B %d %Y at %H:%M")
        
        skip_line = f"{timestamp}|{prayer_id}|{user_id}"
        
        self._append_to_file(str(monthly_file), skip_line)
        logger.info(f"Logged prayer skip: prayer {prayer_id} by user {user_id}")
        
        return str(monthly_file)
    
    def _write_file_atomic(self, file_path: str, content: str):
        """Write file atomically using temporary file and rename"""
        temp_path = file_path + '.tmp'
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Atomic rename
            os.rename(temp_path, file_path)
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
    
    def _append_to_file(self, file_path: str, content: str):
        """Thread-safe append operation with file locking"""
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock
                f.write(content + '\n')
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
                
        except FileNotFoundError:
            logger.error(f"Archive file not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to append to archive file {file_path}: {e}")
            # Don't raise - archive failures shouldn't break the main application
    
    def read_archive_file(self, file_path: str) -> str:
        """Read archive file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Archive file not found: {file_path}")
            raise
    
    def parse_prayer_archive(self, file_path: str) -> tuple:
        """Parse prayer archive file into structured data"""
        content = self.read_archive_file(file_path)
        lines = content.split('\n')
        
        prayer_data = {}
        activities = []
        
        in_activity_section = False
        current_section = "header"
        
        for line in lines:
            line = line.strip()
            
            if line == "Activity:":
                in_activity_section = True
                continue
            
            if not in_activity_section:
                # Parse header section
                if line.startswith("Prayer ") and " by " in line:
                    parts = line.split(" by ")
                    id_str = parts[0].replace("Prayer ", "")
                    # Handle both numeric and string IDs
                    try:
                        prayer_data['id'] = int(id_str)
                    except ValueError:
                        prayer_data['id'] = id_str
                    prayer_data['author'] = parts[1]
                elif line.startswith("Submitted "):
                    prayer_data['submitted'] = line.replace("Submitted ", "")
                elif line.startswith("Project: "):
                    prayer_data['project_tag'] = line.replace("Project: ", "")
                elif line.startswith("Audience: "):
                    prayer_data['target_audience'] = line.replace("Audience: ", "")
                elif line == "Generated Prayer:":
                    current_section = "generated_prayer"
                elif current_section == "generated_prayer" and line:
                    prayer_data['generated_prayer'] = line
                elif line and current_section == "header" and ":" not in line:
                    # This is likely the original request text
                    prayer_data['original_request'] = line
            else:
                # Parse activity section
                if " - " in line and " at " in line:
                    # Parse activity line: "June 14 2024 at 14:45 - John1 prayed this prayer"
                    parts = line.split(" - ", 1)
                    if len(parts) == 2:
                        timestamp_part = parts[0]
                        action_part = parts[1]
                        
                        activities.append({
                            'timestamp': timestamp_part,
                            'raw_action': action_part,
                            'user': self._extract_user_from_action(action_part),
                            'action': self._extract_action_type(action_part)
                        })
        
        return prayer_data, activities
    
    def _extract_user_from_action(self, action_text: str) -> str:
        """Extract username from activity text"""
        # Examples: "John1 prayed this prayer", "Mary1 marked this prayer as answered"
        words = action_text.split()
        if words:
            return words[0]
        return ""
    
    def _extract_action_type(self, action_text: str) -> str:
        """Extract action type from activity text"""
        if "prayed this prayer" in action_text:
            return "prayed"
        elif "marked this prayer as answered" in action_text:
            return "answered"
        elif "added testimony" in action_text:
            return "testimony"
        elif "archived this prayer" in action_text:
            return "archived"
        elif "restored this prayer" in action_text:
            return "restored"
        elif "flagged this prayer" in action_text:
            return "flagged"
        else:
            return "unknown"


# Global instance for use throughout the application
text_archive_service = TextArchiveService()