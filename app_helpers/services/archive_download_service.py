import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import shutil
import os
import json
from sqlmodel import Session
from models import engine, User, Prayer, PrayerMark, PrayerAttribute


class ArchiveDownloadService:
    def __init__(self, archive_base_dir: str):
        self.archive_dir = Path(archive_base_dir)
        
    def create_user_archive_zip(self, user_id: str, include_community: bool = True) -> str:
        """Create ZIP file containing all user's text archives"""
        
        with Session(engine) as db:
            # Get user info
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Create temporary directory for ZIP creation
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                user_archive_dir = temp_path / f"{user.display_name}_text_archive"
                user_archive_dir.mkdir()
                
                # 1. User's Personal Files
                personal_dir = user_archive_dir / "personal"
                personal_dir.mkdir()
                
                # Copy user registration file if exists
                if user.text_file_path and Path(user.text_file_path).exists():
                    registration_content = self._extract_user_registration(user)
                    (personal_dir / "registration.txt").write_text(registration_content, encoding='utf-8')
                
                # 2. User's Prayers
                prayers_dir = user_archive_dir / "prayers"
                prayers_dir.mkdir()
                
                user_prayers = db.query(Prayer).filter_by(author_id=user_id).all()
                for prayer in user_prayers:
                    if prayer.text_file_path and Path(prayer.text_file_path).exists():
                        # Read from archive (handles compressed files)
                        content = self._read_archive_file(prayer.text_file_path)
                        filename = f"prayer_{prayer.id}_{prayer.created_at.strftime('%Y_%m_%d')}.txt"
                        (prayers_dir / filename).write_text(content, encoding='utf-8')
                
                # 3. User's Prayer Activities
                activities_dir = user_archive_dir / "activities"
                activities_dir.mkdir()
                
                # Get all prayers user has interacted with
                user_marks = db.query(PrayerMark).filter_by(user_id=user_id).all()
                activity_summary = self._create_user_activity_summary(user, user_marks)
                (activities_dir / "my_prayer_activities.txt").write_text(activity_summary, encoding='utf-8')
                
                # 4. Community Archives (if requested)
                if include_community:
                    community_dir = user_archive_dir / "community"
                    community_dir.mkdir()
                    
                    # Monthly activity logs
                    self._copy_monthly_activity_files(community_dir)
                    
                    # Monthly user registration files
                    self._copy_monthly_user_files(community_dir)
                
                # 5. Create ZIP file
                zip_filename = f"{user.display_name}_archive_{datetime.now().strftime('%Y_%m_%d')}.zip"
                zip_path = temp_path / zip_filename
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file_path in user_archive_dir.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(temp_path)
                            zf.write(file_path, arcname)
                
                # Move to permanent location
                permanent_zip_dir = self.archive_dir / "downloads"
                permanent_zip_dir.mkdir(exist_ok=True)
                permanent_zip_path = permanent_zip_dir / zip_filename
                shutil.move(zip_path, permanent_zip_path)
                
                return str(permanent_zip_path)

    def create_full_community_zip(self) -> str:
        """Create ZIP of entire community text archive"""
        
        # Create temporary directory for ZIP creation
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            community_archive_dir = temp_path / "complete_site_archive"
            community_archive_dir.mkdir()
            
            # Copy entire text_archives directory structure
            if self.archive_dir.exists():
                # Copy prayers directory
                prayers_src = self.archive_dir / "prayers"
                if prayers_src.exists():
                    prayers_dest = community_archive_dir / "prayers"
                    shutil.copytree(prayers_src, prayers_dest)
                
                # Copy users directory
                users_src = self.archive_dir / "users"
                if users_src.exists():
                    users_dest = community_archive_dir / "users"
                    shutil.copytree(users_src, users_dest)
                
                # Copy activity directory
                activity_src = self.archive_dir / "activity"
                if activity_src.exists():
                    activity_dest = community_archive_dir / "activity"
                    shutil.copytree(activity_src, activity_dest)
                
                # Copy foundational prayers if they exist
                foundational_src = self.archive_dir / "foundational_prayers"
                if foundational_src.exists():
                    foundational_dest = community_archive_dir / "foundational_prayers"
                    shutil.copytree(foundational_src, foundational_dest)
            
            # Add metadata file
            metadata = {
                "export_date": datetime.now().isoformat(),
                "export_type": "complete_site_archive",
                "archive_structure": {
                    "prayers": "All prayer requests and activities organized by year/month",
                    "users": "Monthly user registration logs",
                    "activity": "Monthly community activity summaries",
                    "foundational_prayers": "Built-in community prayers"
                },
                "format_info": {
                    "encoding": "UTF-8",
                    "timestamp_format": "Month DD YYYY at HH:MM",
                    "file_naming": "YYYY_MM_DD_prayer_at_HHMM.txt"
                }
            }
            
            metadata_file = community_archive_dir / "archive_metadata.json"
            metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            
            # Create README
            readme_content = self._create_archive_readme()
            (community_archive_dir / "README.txt").write_text(readme_content, encoding='utf-8')
            
            # Create ZIP file
            zip_filename = f"complete_site_archive_{datetime.now().strftime('%Y_%m_%d_%H%M')}.zip"
            zip_path = temp_path / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in community_archive_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_path)
                        zf.write(file_path, arcname)
            
            # Move to permanent location
            permanent_zip_dir = self.archive_dir / "downloads"
            permanent_zip_dir.mkdir(exist_ok=True)
            permanent_zip_path = permanent_zip_dir / zip_filename
            shutil.move(zip_path, permanent_zip_path)
            
            return str(permanent_zip_path)

    def get_user_archive_metadata(self, user_id: str) -> Dict:
        """Get comprehensive metadata about user's archives"""
        
        with Session(engine) as db:
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            metadata = {
                "user": {
                    "id": user.id,
                    "display_name": user.display_name,
                    "registration_date": user.created_at.isoformat() if user.created_at else None,
                    "text_file_path": user.text_file_path
                },
                "prayers": [],
                "activities": [],
                "archive_statistics": {
                    "total_prayers": 0,
                    "total_activities": 0,
                    "date_range": {"earliest": None, "latest": None},
                    "total_archive_files": 0
                }
            }
            
            # Get user's prayers with archive info
            user_prayers = db.query(Prayer).filter_by(author_id=user_id).all()
            for prayer in user_prayers:
                prayer_info = {
                    "id": prayer.id,
                    "created_at": prayer.created_at.isoformat() if prayer.created_at else None,
                    "project_tag": prayer.project_tag,
                    "text_file_path": prayer.text_file_path,
                    "archive_exists": prayer.text_file_path and Path(prayer.text_file_path).exists()
                }
                metadata["prayers"].append(prayer_info)
            
            # Get user's activities
            user_marks = db.query(PrayerMark).filter_by(user_id=user_id).all()
            for mark in user_marks:
                activity_info = {
                    "prayer_id": mark.prayer_id,
                    "created_at": mark.created_at.isoformat() if mark.created_at else None,
                    "text_file_path": mark.text_file_path,
                    "archive_exists": mark.text_file_path and Path(mark.text_file_path).exists()
                }
                metadata["activities"].append(activity_info)
            
            # Calculate statistics
            metadata["archive_statistics"]["total_prayers"] = len(user_prayers)
            metadata["archive_statistics"]["total_activities"] = len(user_marks)
            
            all_dates = []
            for prayer in user_prayers:
                if prayer.created_at:
                    all_dates.append(prayer.created_at)
            for mark in user_marks:
                if mark.created_at:
                    all_dates.append(mark.created_at)
            
            if all_dates:
                metadata["archive_statistics"]["date_range"]["earliest"] = min(all_dates).isoformat()
                metadata["archive_statistics"]["date_range"]["latest"] = max(all_dates).isoformat()
            
            return metadata

    def list_community_archives(self) -> List[Dict]:
        """List all community archive files with metadata"""
        
        archives = []
        
        # Prayer archives by month
        prayers_dir = self.archive_dir / "prayers"
        if prayers_dir.exists():
            for year_dir in prayers_dir.iterdir():
                if year_dir.is_dir() and year_dir.name.isdigit():
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir() and month_dir.name.isdigit():
                            file_count = len(list(month_dir.glob("*.txt")))
                            if file_count > 0:
                                archives.append({
                                    "type": "prayers",
                                    "period": f"{year_dir.name}-{month_dir.name.zfill(2)}",
                                    "path": str(month_dir),
                                    "file_count": file_count,
                                    "compressed": False
                                })
                        elif month_dir.name.endswith("_prayers.zip"):
                            # Handle compressed monthly archives
                            period = month_dir.name.replace("_prayers.zip", "")
                            archives.append({
                                "type": "prayers",
                                "period": f"{year_dir.name}-{period}",
                                "path": str(month_dir),
                                "file_count": self._count_zip_files(month_dir),
                                "compressed": True
                            })
        
        # Monthly user registration files
        users_dir = self.archive_dir / "users"
        if users_dir.exists():
            for user_file in users_dir.glob("*.txt"):
                period = user_file.stem.replace("_users", "")
                archives.append({
                    "type": "users",
                    "period": period,
                    "path": str(user_file),
                    "file_count": 1,
                    "compressed": False
                })
            
            for user_zip in users_dir.glob("*.zip"):
                period = user_zip.stem.replace("_users.txt", "")
                archives.append({
                    "type": "users", 
                    "period": period,
                    "path": str(user_zip),
                    "file_count": 1,
                    "compressed": True
                })
        
        # Monthly activity files
        activity_dir = self.archive_dir / "activity"
        if activity_dir.exists():
            for activity_file in activity_dir.glob("*.txt"):
                period = activity_file.stem.replace("activity_", "")
                archives.append({
                    "type": "activity",
                    "period": period,
                    "path": str(activity_file),
                    "file_count": 1,
                    "compressed": False
                })
            
            for activity_zip in activity_dir.glob("*.zip"):
                period = activity_zip.stem.replace("activity_", "").replace(".txt", "")
                archives.append({
                    "type": "activity",
                    "period": period,
                    "path": str(activity_zip),
                    "file_count": 1,
                    "compressed": True
                })
        
        return sorted(archives, key=lambda x: x["period"], reverse=True)

    def cleanup_old_downloads(self, max_age_hours: int = 24):
        """Clean up old download files"""
        
        downloads_dir = self.archive_dir / "downloads"
        if not downloads_dir.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        for file_path in downloads_dir.glob("*.zip"):
            if file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                except OSError:
                    pass  # File might be in use or already deleted

    def _read_archive_file(self, file_path: str) -> str:
        """Read archive file, handling both uncompressed and compressed"""
        
        path = Path(file_path)
        
        # First try to read uncompressed file
        if path.exists():
            return path.read_text(encoding='utf-8')
        
        # TODO: Add compressed file reading when compression is implemented
        raise FileNotFoundError(f"Archive file not found: {file_path}")

    def _extract_user_registration(self, user: User) -> str:
        """Extract user registration info from monthly file"""
        
        if not user.text_file_path:
            return f"User: {user.display_name}\nRegistered: {user.created_at}\nNo text archive available"
        
        try:
            full_content = self._read_archive_file(user.text_file_path)
            # Extract lines related to this user
            user_lines = []
            for line in full_content.split('\n'):
                if user.display_name in line:
                    user_lines.append(line)
            
            if user_lines:
                return f"User Registration Information:\n\n" + "\n".join(user_lines)
            else:
                return f"User: {user.display_name}\nRegistered: {user.created_at}\nDetails not found in archive"
        except:
            return f"User: {user.display_name}\nRegistered: {user.created_at}\nArchive file could not be read"

    def _create_user_activity_summary(self, user: User, user_marks: List[PrayerMark]) -> str:
        """Create summary of user's prayer activities"""
        
        content = f"Prayer Activities for {user.display_name}\n"
        content += "=" * 50 + "\n\n"
        
        if not user_marks:
            content += "No prayer activities found.\n"
            return content
        
        # Group by date
        activities_by_date = {}
        for mark in user_marks:
            if mark.created_at:
                date_str = mark.created_at.strftime("%B %d %Y")
                if date_str not in activities_by_date:
                    activities_by_date[date_str] = []
                
                time_str = mark.created_at.strftime("%H:%M")
                activities_by_date[date_str].append(f"{time_str} - Prayed for prayer {mark.prayer_id}")
        
        # Sort dates and output
        for date in sorted(activities_by_date.keys()):
            content += f"{date}\n"
            for activity in activities_by_date[date]:
                content += f"{activity}\n"
            content += "\n"
        
        return content

    def _copy_monthly_activity_files(self, dest_dir: Path):
        """Copy monthly activity files to destination"""
        
        activity_dir = self.archive_dir / "activity"
        if activity_dir.exists():
            activity_dest = dest_dir / "activity"
            activity_dest.mkdir(exist_ok=True)
            
            for activity_file in activity_dir.glob("*.txt"):
                shutil.copy2(activity_file, activity_dest)

    def _copy_monthly_user_files(self, dest_dir: Path):
        """Copy monthly user registration files to destination"""
        
        users_dir = self.archive_dir / "users"
        if users_dir.exists():
            users_dest = dest_dir / "users"
            users_dest.mkdir(exist_ok=True)
            
            for user_file in users_dir.glob("*.txt"):
                shutil.copy2(user_file, users_dest)

    def _count_zip_files(self, zip_path: Path) -> int:
        """Count files in a ZIP archive"""
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                return len(zf.namelist())
        except:
            return 0

    def _create_archive_readme(self) -> str:
        """Create README content for archive downloads"""
        
        return """ThyWill Text Archive
===================

This archive contains human-readable text files of all prayer requests, user activity, 
and community interactions from the ThyWill prayer application.

Directory Structure:
-------------------

prayers/
├── YYYY/
│   └── MM/
│       └── YYYY_MM_DD_prayer_at_HHMM.txt    # Individual prayer files

users/
└── YYYY_MM_users.txt                         # Monthly user registrations

activity/
└── activity_YYYY_MM.txt                      # Monthly activity summaries

foundational_prayers/
└── *.txt                                     # Built-in community prayers


File Format:
-----------

Prayer files contain:
- Original prayer request
- Generated prayer text  
- Complete activity timeline
- All user interactions

User files contain:
- Registration information
- Invitation relationships

Activity files contain:
- Daily activity summaries
- Community-wide interactions


Timestamps:
----------
All timestamps use the format: "Month DD YYYY at HH:MM" (24-hour time)

Example: "January 15 2024 at 14:30"


About This Archive:
------------------
- Files are UTF-8 encoded text
- Human-readable without special tools
- Complete audit trail of all activity
- Portable and future-proof format
- Can be opened with any text editor

Generated: """ + datetime.now().strftime("%B %d %Y at %H:%M")