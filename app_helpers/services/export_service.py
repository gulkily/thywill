"""
Database export service for community cloning functionality.
Exports all public community data while excluding sensitive authentication data.
"""

import json
import zipfile
import io
import os
import hashlib
import tempfile
from datetime import datetime, timedelta
from sqlmodel import Session, select
from models import (
    User, Prayer, PrayerAttribute, PrayerMark, PrayerSkip, 
    PrayerActivityLog, Role, UserRole, ChangelogEntry,
    engine
)
from typing import Dict, Any, List


class CommunityExportService:
    """Service for exporting community database in JSON format for cloning."""
    
    def __init__(self):
        self.export_version = "1.0"
        self.cache_ttl_minutes = int(os.getenv("EXPORT_CACHE_TTL_MINUTES", "15"))  # Default 15 minutes
        self.cache_dir = os.path.join(tempfile.gettempdir(), "thywill_export_cache")
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Ensure cache directory exists."""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_key(self) -> str:
        """Generate cache key based on current data state."""
        with Session(engine) as session:
            # Get counts and latest timestamps to create a data fingerprint
            user_count = len(session.exec(select(User)).all())
            prayer_count = len(session.exec(select(Prayer)).all())
            
            # Get latest timestamps
            latest_user = session.exec(select(User).order_by(User.created_at.desc()).limit(1)).first()
            latest_prayer = session.exec(select(Prayer).order_by(Prayer.created_at.desc()).limit(1)).first()
            
            # Create fingerprint from counts and timestamps
            fingerprint_data = f"{user_count}:{prayer_count}"
            if latest_user:
                fingerprint_data += f":{latest_user.created_at.isoformat()}"
            if latest_prayer:
                fingerprint_data += f":{latest_prayer.created_at.isoformat()}"
            
            # Add export version to invalidate cache on version changes
            fingerprint_data += f":{self.export_version}"
            
            return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> str:
        """Get file path for cached export."""
        return os.path.join(self.cache_dir, f"export_{cache_key}.zip")
    
    def _is_cache_valid(self, cache_file_path: str) -> bool:
        """Check if cached file exists and is within TTL."""
        if not os.path.exists(cache_file_path):
            return False
        
        # Check if file is within TTL
        file_age = datetime.utcnow() - datetime.utcfromtimestamp(os.path.getmtime(cache_file_path))
        return file_age < timedelta(minutes=self.cache_ttl_minutes)
    
    def _cleanup_old_cache_files(self):
        """Remove old cache files to prevent disk space buildup."""
        if not os.path.exists(self.cache_dir):
            return
        
        cutoff_time = datetime.utcnow() - timedelta(hours=24)  # Remove files older than 24 hours
        
        for filename in os.listdir(self.cache_dir):
            if filename.startswith("export_") and filename.endswith(".zip"):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.exists(file_path):
                    file_time = datetime.utcfromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_time:
                        try:
                            os.remove(file_path)
                        except OSError:
                            pass  # Ignore file removal errors
    
    def export_community_data(self) -> Dict[str, Any]:
        """
        Export complete community database excluding sensitive data.
        
        Returns:
            Dict containing structured community data in JSON-serializable format
        """
        with Session(engine) as session:
            # Get export metadata
            export_data = {
                "export_metadata": self._get_export_metadata(session),
                "users": self._export_users(session),
                "prayers": self._export_prayers(session),
                "prayer_attributes": self._export_prayer_attributes(session),
                "prayer_marks": self._export_prayer_marks(session),
                "prayer_skips": self._export_prayer_skips(session),
                "prayer_activity_log": self._export_prayer_activity_log(session),
                "roles": self._export_roles(session),
                "user_roles": self._export_user_roles(session),
                "changelog_entries": self._export_changelog_entries(session)
            }
            
            return export_data
    
    def _get_export_metadata(self, session: Session) -> Dict[str, Any]:
        """Generate export metadata."""
        return {
            "version": self.export_version,
            "export_date": datetime.utcnow().isoformat() + "Z",
            "source_instance": "thywill_community",
            "schema_version": "current"
        }
    
    def _export_users(self, session: Session) -> List[Dict[str, Any]]:
        """Export all users with their profiles and invite tree relationships."""
        stmt = select(User)
        users = session.exec(stmt).all()
        
        return [
            {
                "id": user.id,
                "display_name": user.display_name,
                "created_at": user.created_at.isoformat() + "Z",
                "religious_preference": user.religious_preference,
                "prayer_style": user.prayer_style,
                "invited_by_user_id": user.invited_by_user_id,
                "welcome_message_dismissed": user.welcome_message_dismissed
            }
            for user in users
        ]
    
    def _export_prayers(self, session: Session) -> List[Dict[str, Any]]:
        """Export all non-flagged prayers."""
        # Exclude prayers that are flagged using the old flagged field
        # or have the 'flagged' attribute
        stmt = select(Prayer).where(Prayer.flagged == False)
        prayers = session.exec(stmt).all()
        
        # Filter out prayers with 'flagged' attribute
        non_flagged_prayers = []
        for prayer in prayers:
            if not prayer.has_attribute('flagged', session):
                non_flagged_prayers.append({
                    "id": prayer.id,
                    "author_id": prayer.author_id,
                    "text": prayer.text,
                    "generated_prayer": prayer.generated_prayer,
                    "project_tag": prayer.project_tag,
                    "created_at": prayer.created_at.isoformat() + "Z",
                    "target_audience": prayer.target_audience
                })
        
        return non_flagged_prayers
    
    def _export_prayer_attributes(self, session: Session) -> List[Dict[str, Any]]:
        """Export prayer attributes for non-flagged prayers only."""
        # Get all non-flagged prayer IDs
        stmt = select(Prayer.id).where(Prayer.flagged == False)
        non_flagged_prayer_ids = [row[0] for row in session.exec(stmt).all()]
        
        # Get attributes for non-flagged prayers, excluding 'flagged' attributes
        if not non_flagged_prayer_ids:
            return []
        
        stmt = select(PrayerAttribute).where(
            PrayerAttribute.prayer_id.in_(non_flagged_prayer_ids),
            PrayerAttribute.attribute_name != 'flagged'
        )
        attributes = session.exec(stmt).all()
        
        return [
            {
                "id": attr.id,
                "prayer_id": attr.prayer_id,
                "attribute_name": attr.attribute_name,
                "attribute_value": attr.attribute_value,
                "created_at": attr.created_at.isoformat() + "Z",
                "created_by": attr.created_by
            }
            for attr in attributes
        ]
    
    def _export_prayer_marks(self, session: Session) -> List[Dict[str, Any]]:
        """Export prayer marks for non-flagged prayers only."""
        # Get all non-flagged prayer IDs
        stmt = select(Prayer.id).where(Prayer.flagged == False)
        non_flagged_prayer_ids = [row[0] for row in session.exec(stmt).all()]
        
        if not non_flagged_prayer_ids:
            return []
        
        stmt = select(PrayerMark).where(
            PrayerMark.prayer_id.in_(non_flagged_prayer_ids)
        )
        marks = session.exec(stmt).all()
        
        return [
            {
                "id": mark.id,
                "user_id": mark.user_id,
                "prayer_id": mark.prayer_id,
                "created_at": mark.created_at.isoformat() + "Z"
            }
            for mark in marks
        ]
    
    def _export_prayer_skips(self, session: Session) -> List[Dict[str, Any]]:
        """Export prayer skips for non-flagged prayers only."""
        # Get all non-flagged prayer IDs
        stmt = select(Prayer.id).where(Prayer.flagged == False)
        non_flagged_prayer_ids = [row[0] for row in session.exec(stmt).all()]
        
        if not non_flagged_prayer_ids:
            return []
        
        stmt = select(PrayerSkip).where(
            PrayerSkip.prayer_id.in_(non_flagged_prayer_ids)
        )
        skips = session.exec(stmt).all()
        
        return [
            {
                "id": skip.id,
                "user_id": skip.user_id,
                "prayer_id": skip.prayer_id,
                "created_at": skip.created_at.isoformat() + "Z"
            }
            for skip in skips
        ]
    
    def _export_prayer_activity_log(self, session: Session) -> List[Dict[str, Any]]:
        """Export prayer activity logs for non-flagged prayers only."""
        # Get all non-flagged prayer IDs
        stmt = select(Prayer.id).where(Prayer.flagged == False)
        non_flagged_prayer_ids = [row[0] for row in session.exec(stmt).all()]
        
        if not non_flagged_prayer_ids:
            return []
        
        stmt = select(PrayerActivityLog).where(
            PrayerActivityLog.prayer_id.in_(non_flagged_prayer_ids)
        )
        logs = session.exec(stmt).all()
        
        return [
            {
                "id": log.id,
                "prayer_id": log.prayer_id,
                "user_id": log.user_id,
                "action": log.action,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "created_at": log.created_at.isoformat() + "Z"
            }
            for log in logs
        ]
    
    def _export_roles(self, session: Session) -> List[Dict[str, Any]]:
        """Export all role definitions."""
        stmt = select(Role)
        roles = session.exec(stmt).all()
        
        return [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "permissions": role.permissions,
                "created_at": role.created_at.isoformat() + "Z",
                "created_by": role.created_by,
                "is_system_role": role.is_system_role
            }
            for role in roles
        ]
    
    def _export_user_roles(self, session: Session) -> List[Dict[str, Any]]:
        """Export user role assignments."""
        stmt = select(UserRole)
        user_roles = session.exec(stmt).all()
        
        return [
            {
                "id": user_role.id,
                "user_id": user_role.user_id,
                "role_id": user_role.role_id,
                "granted_by": user_role.granted_by,
                "granted_at": user_role.granted_at.isoformat() + "Z",
                "expires_at": user_role.expires_at.isoformat() + "Z" if user_role.expires_at else None
            }
            for user_role in user_roles
        ]
    
    
    def _export_changelog_entries(self, session: Session) -> List[Dict[str, Any]]:
        """Export community development history."""
        stmt = select(ChangelogEntry)
        entries = session.exec(stmt).all()
        
        return [
            {
                "commit_id": entry.commit_id,
                "original_message": entry.original_message,
                "friendly_description": entry.friendly_description,
                "change_type": entry.change_type,
                "commit_date": entry.commit_date.isoformat() + "Z",
                "created_at": entry.created_at.isoformat() + "Z"
            }
            for entry in entries
        ]
    
    def export_to_json_string(self) -> str:
        """
        Export community data as formatted JSON string.
        
        Returns:
            JSON string with proper formatting for download
        """
        data = self.export_community_data()
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def export_to_zip(self, use_cache: bool = True) -> tuple[bytes, bool]:
        """
        Export community data as ZIP file containing separate JSON files per table.
        
        Args:
            use_cache: Whether to use caching (default True)
            
        Returns:
            Tuple of (ZIP file content as bytes, whether data was from cache)
        """
        # Clean up old cache files periodically
        self._cleanup_old_cache_files()
        
        if use_cache:
            # Check if we have a valid cached version
            cache_key = self._get_cache_key()
            cache_file_path = self._get_cache_file_path(cache_key)
            
            if self._is_cache_valid(cache_file_path):
                # Return cached version
                try:
                    with open(cache_file_path, 'rb') as f:
                        return f.read(), True
                except OSError:
                    # If cache file read fails, generate new export
                    pass
        
        # Generate new export
        zip_data = self._generate_zip_export()
        
        if use_cache:
            # Save to cache
            try:
                with open(cache_file_path, 'wb') as f:
                    f.write(zip_data)
            except OSError:
                # If cache write fails, continue without caching
                pass
        
        return zip_data, False
    
    def _generate_zip_export(self) -> bytes:
        """Generate fresh ZIP export."""
        # Get export data
        data = self.export_community_data()
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
            # Add export metadata as separate file
            metadata_content = json.dumps(data["export_metadata"], indent=2, ensure_ascii=False)
            zip_file.writestr("metadata.json", metadata_content.encode('utf-8'))
            
            # Add each table as separate JSON file
            table_files = {
                "users.json": data["users"],
                "prayers.json": data["prayers"],
                "prayer_attributes.json": data["prayer_attributes"],
                "prayer_marks.json": data["prayer_marks"],
                "prayer_skips.json": data["prayer_skips"],
                "prayer_activity_log.json": data["prayer_activity_log"],
                "roles.json": data["roles"],
                "user_roles.json": data["user_roles"],
                "changelog_entries.json": data["changelog_entries"]
            }
            
            for filename, table_data in table_files.items():
                table_json = json.dumps(table_data, indent=2, ensure_ascii=False)
                zip_file.writestr(filename, table_json.encode('utf-8'))
            
            # Add combined file for compatibility
            combined_json = self.export_to_json_string()
            combined_filename = f"community_export_{current_date}.json"
            zip_file.writestr(combined_filename, combined_json.encode('utf-8'))
            
            # Add README file with export information
            readme_content = self._generate_readme()
            zip_file.writestr("README.txt", readme_content.encode('utf-8'))
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    def _generate_readme(self) -> str:
        """Generate README content for the export ZIP file."""
        current_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        return f"""ThyWill Community Export
========================

Export Date: {current_date}
Export Version: {self.export_version}
Source: ThyWill Prayer Community

CONTENTS
--------
This export contains both individual table files and a combined export:

INDIVIDUAL TABLE FILES:
- metadata.json: Export metadata and version information
- users.json: User profiles and preferences
- prayers.json: Prayer requests and generated prayers
- prayer_attributes.json: Prayer status and metadata
- prayer_marks.json: User prayer interactions
- prayer_skips.json: Prayers users have skipped
- prayer_activity_log.json: History of prayer status changes
- roles.json: User role definitions
- user_roles.json: User role assignments  
- changelog_entries.json: Development history

COMBINED FILES:
- community_export_*.json: Complete community data in single JSON file
- README.txt: This file with export information

DATA INCLUDED
-------------
✓ Users: All community members and their profiles
✓ Prayers: All public prayer requests and generated prayers  
✓ Prayer Activity: Prayer marks, skips, and status changes
✓ Community Structure: User roles and invite relationships
✓ Development History: Changelog entries and updates

DATA EXCLUDED (for privacy/security)
------------------------------------
✗ Flagged Content: Moderated prayers are excluded
✗ Authentication Data: Session tokens and passwords
✗ Invite Tokens: Private invitation codes
✗ Security Logs: Audit trails and monitoring data  
✗ Temporary Data: Notifications and ephemeral state

FILE STRUCTURE
--------------
INDIVIDUAL FILES: Each table is exported as a separate JSON file containing
an array of objects. This makes it easy to import specific tables or analyze
individual data types.

COMBINED FILE: The community_export_*.json file contains all data in a single
structured JSON object with sections for each table type. This is compatible
with the original export format.

Each individual file contains:
- users.json: Array of user objects with profiles and settings
- prayers.json: Array of prayer objects with content and metadata
- prayer_attributes.json: Array of prayer attribute objects
- prayer_marks.json: Array of prayer mark interaction objects
- prayer_skips.json: Array of prayer skip interaction objects
- prayer_activity_log.json: Array of prayer activity log objects
- roles.json: Array of role definition objects
- user_roles.json: Array of user role assignment objects
- changelog_entries.json: Array of development history objects

USAGE
-----
This export can be used for:
- Community backup and disaster recovery
- Starting new ThyWill communities (forking)
- Data analysis and reporting (use individual table files)
- Development and testing with real data
- Database migration and ETL processes

IMPORT OPTIONS:
- Use individual JSON files for selective data import
- Use combined JSON file for complete community restoration
- Import into databases, spreadsheets, or analytics tools
- Process with any programming language that supports JSON

The JSON format is compatible with most programming languages and 
data analysis tools. Each file contains arrays of objects with
consistent field names and ISO 8601 datetime formatting.

For import instructions and technical documentation, please refer to
the ThyWill documentation or community forums.

---
Generated by ThyWill Community Export v{self.export_version}
"""
    
    def get_export_info(self) -> dict:
        """
        Get summary information about the export without generating it.
        
        Returns:
            Dictionary with export statistics and estimated size
        """
        with Session(engine) as session:
            # Count various data types
            user_count = len(session.exec(select(User)).all())
            
            # Count non-flagged prayers
            prayers = session.exec(select(Prayer).where(Prayer.flagged == False)).all()
            prayer_count = len([p for p in prayers if not p.has_attribute('flagged', session)])
            
            role_count = len(session.exec(select(Role)).all())
            changelog_count = len(session.exec(select(ChangelogEntry)).all())
            
            # Estimate size (rough calculation)
            estimated_json_size = (
                user_count * 200 +  # ~200 bytes per user
                prayer_count * 500 +  # ~500 bytes per prayer
                role_count * 150 +  # ~150 bytes per role
                changelog_count * 300  # ~300 bytes per changelog entry
            )
            
            # ZIP compression typically reduces JSON by 60-80%
            estimated_zip_size = int(estimated_json_size * 0.3)
            
            # Format size for display
            if estimated_zip_size < 1024:
                size_display = f"{estimated_zip_size} bytes"
            elif estimated_zip_size < 1024 * 1024:
                size_display = f"{estimated_zip_size // 1024} KB"
            else:
                size_display = f"{estimated_zip_size // (1024 * 1024)} MB"
            
            # Check cache status
            cache_key = self._get_cache_key()
            cache_file_path = self._get_cache_file_path(cache_key)
            cache_available = self._is_cache_valid(cache_file_path)
            cache_age_minutes = 0
            
            if cache_available:
                file_age = datetime.utcnow() - datetime.utcfromtimestamp(os.path.getmtime(cache_file_path))
                cache_age_minutes = int(file_age.total_seconds() / 60)
            
            return {
                "users": user_count,
                "prayers": prayer_count,
                "roles": role_count,
                "changelog_entries": changelog_count,
                "estimated_size": size_display,
                "estimated_bytes": estimated_zip_size,
                "cache_available": cache_available,
                "cache_age_minutes": cache_age_minutes,
                "cache_ttl_minutes": self.cache_ttl_minutes
            }