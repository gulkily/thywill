# Text Archive System Implementation Plan

## Overview
Implement a comprehensive text archive system for the ThyWill prayer application. Text files become the **primary data store** and source of truth, with the database serving as a fast query interface. This provides ultimate data portability, human-readable records, and complete independence from database formats.

## Current State Analysis
- **Existing Infrastructure**: The app already has a sophisticated export/import system (`CommunityExportService` and import functionality) that handles JSON/ZIP exports
- **Database Models**: Well-structured models for Prayer, User, PrayerAttribute, PrayerMark, invite relationships, and activity logging
- **Architecture**: Modular FastAPI application with clear service separation

## Implementation Strategy

### Phase 1: Text Archive Format Design and Core Services

#### 1.1 Text File Format Specifications (Human-Readable & Append-Friendly)

**File Naming Convention:**
- **Prayer Files**: `2024_06_01_prayer_at_0655.txt` (with conflict resolution: `2024_06_01_prayer_at_0655_2.txt`)
- **User Files**: `2024_06_users.txt` (monthly user registrations)
- **Activity Files**: `activity_2024_06.txt` (monthly activity log)

**Prayer Request Files** (`/text_archives/prayers/2024/06/2024_06_01_prayer_at_0655.txt`)
```
Prayer 12345 by Mary1
Submitted June 1 2024 at 06:55
Project: family
Audience: general

Please pray for my mother's health recovery after surgery.

Generated Prayer:
Heavenly Father, we lift up Mary's mother to You...

Activity:
June 1 2024 at 14:45 - John1 prayed this prayer
June 1 2024 at 15:20 - Sarah2 prayed this prayer
June 2 2024 at 08:00 - Mary1 marked this prayer as answered
June 2 2024 at 08:01 - Mary1 added testimony: Mom is doing much better, thank you all!
```

**Monthly User Registration Files** (`/text_archives/users/2024_06_users.txt`)
```
User Registrations for June 2024

June 1 2024 at 09:15 - Sarah2 joined on invitation from Mary1
June 3 2024 at 14:22 - John3 joined on invitation from John1
June 7 2024 at 11:30 - David4 joined directly
June 15 2024 at 16:45 - Lisa5 joined on invitation from Sarah2
```

**Monthly Activity Log Files** (`/text_archives/activity/activity_2024_06.txt`)
```
Activity for June 2024

June 1 2024
06:55 - Mary1 submitted prayer 12345 (family)
14:45 - John1 prayed for prayer 12345
15:20 - Sarah2 prayed for prayer 12345

June 2 2024
08:00 - Mary1 marked prayer 12345 as answered
08:01 - Mary1 added testimony for prayer 12345
16:10 - David4 submitted prayer 12346 (work)

June 3 2024
14:22 - John3 registered via invitation from John1
```

**Format Design Principles:**
- **24-hour timestamps**: "June 14 2024 at 14:45" (parseable as "MMM DD YYYY at HH:MM")
- **Natural language**: "prayed this prayer", "marked as answered", "joined on invitation"
- **Minimal punctuation**: Colons for labels, dashes for chronological lists
- **Append-only structure**: New activities add new lines at the end
- **Consistent patterns**: Each file type follows predictable format for parsing
- **Clean spacing**: Blank lines separate sections for readability

#### 1.2 Text Archive Service Architecture

**New Service**: `app_helpers/services/text_archive_service.py`
- `TextArchiveService` class with methods for each data type
- Integration with existing database session patterns
- Atomic file operations with error handling
- Configurable archive directory and format options

**Key Archive Methods:**
```python
def append_prayer_activity(prayer_id: int, action: str, user: str, extra: str = ""):
    """Append single line to prayer activity archive"""
    
def append_user_registration(user_name: str, invite_source: str = ""):
    """Append single line to monthly user registration archive"""
    
def append_monthly_activity(action: str, user: str, prayer_id: int = None, tag: str = ""):
    """Append activity to monthly archive, adding date header if needed"""
```

**Date Header Detection for Monthly Activity Files:**
```python
def append_monthly_activity(action: str, user: str, prayer_id: int = None, tag: str = ""):
    activity_date = datetime.now().strftime("%B %d %Y")  # "June 1 2024"
    timestamp = datetime.now().strftime("%H:%M")  # "14:45" (24-hour format)
    file_path = get_monthly_activity_file_path()
    
    # Check if today's date header already exists
    needs_date_header = True
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
            if f"\n{activity_date}\n" in content or content.endswith(f"{activity_date}\n"):
                needs_date_header = False
    
    # Append date header if needed, then append activity
    with file_lock(file_path):
        with open(file_path, 'a') as f:
            if needs_date_header:
                f.write(f"\n{activity_date}\n")
            f.write(f"{timestamp} - {user} {action}\n")
```

**Prayer File Naming with Conflict Resolution:**
```python
def generate_prayer_filename(date: datetime, prayer_id: int) -> str:
    """Generate unique prayer filename with conflict resolution"""
    base_name = date.strftime("2024_%m_%d_prayer_at_%H%M")
    file_path = f"/text_archives/prayers/{date.year}/{date.month:02d}/{base_name}.txt"
    
    # Handle conflicts by appending number
    counter = 2
    while os.path.exists(file_path):
        conflict_name = f"{base_name}_{counter}"
        file_path = f"/text_archives/prayers/{date.year}/{date.month:02d}/{conflict_name}.txt"
        counter += 1
    
    return file_path
```

**Flexible Prayer File Import (Future-Proof):**
```python
def parse_prayer_filename(filename: str) -> dict:
    """Parse prayer filename flexibly to handle format changes"""
    # Current format: 2024_06_01_prayer_at_0655.txt
    # Future format: 2024_06_01_prayer_from_Mary.txt
    
    patterns = [
        r"(\d{4})_(\d{2})_(\d{2})_prayer_at_(\d{4})(?:_(\d+))?\.txt",  # time-based
        r"(\d{4})_(\d{2})_(\d{2})_prayer_from_(\w+)(?:_(\d+))?\.txt",   # author-based
    ]
    
    for pattern in patterns:
        match = re.match(pattern, filename)
        if match:
            return parse_matched_groups(match)
    
    raise ValueError(f"Unknown prayer filename format: {filename}")
```

**File Writing Strategy:**
- **Atomic appends**: Use file locking to prevent corruption during concurrent writes
- **Create if missing**: Automatically create directory structure and files as needed
- **Date header detection**: Check existing content before adding new date sections
- **Error recovery**: Failed writes are logged but don't block main application
- **Future-proof parsing**: Flexible filename parsing for format evolution

### Phase 2: Real-time Integration with Archive-First Strategy

#### 2.1 Integration Points with Archive-First Strategy
- **Prayer Submission**: Modify `submit_prayer()` to write text archive FIRST, then database
- **Prayer Interactions**: Write to text archive, then update database with file path
- **User Registration**: Write to monthly user archive, then create user record with file path
- **Activity Logging**: All database operations must reference their text archive source

#### 2.2 Modified Data Flow
**Before (Database-First):**
```
User Action → Database Write → Text Archive (optional)
```

**After (Archive-First):**
```
User Action → Text Archive Write → Database Write (with file path) → Success
```

**Critical Implementation Changes:**
```python
# OLD: Database-first approach
def submit_prayer(prayer_data):
    prayer = Prayer(text=prayer_data['text'])
    db.session.add(prayer)
    db.session.commit()
    archive_to_text(prayer)  # Optional archive

# NEW: Archive-first approach  
def submit_prayer(prayer_data):
    # Step 1: Write authoritative text archive
    text_file_path = create_prayer_archive_file(prayer_data)
    
    # Step 2: Create database record pointing to archive file
    prayer = Prayer(
        text=prayer_data['text'],
        text_file_path=text_file_path  # Critical reference to archive
    )
    db.session.add(prayer)
    db.session.commit()
    
    return prayer, text_file_path
```

### Phase 3: Import/Recovery System with Text Archive Tracking

#### 3.1 Database Schema Extensions
**Add text file tracking fields to existing models:**
```sql
-- Add to Prayer table
ALTER TABLE prayers ADD COLUMN text_file_path TEXT;

-- Add to User table  
ALTER TABLE users ADD COLUMN text_file_path TEXT;

-- Add to PrayerMark table
ALTER TABLE prayer_marks ADD COLUMN text_file_path TEXT;

-- Add to PrayerAttribute table
ALTER TABLE prayer_attributes ADD COLUMN text_file_path TEXT;

-- New table for tracking text archive metadata
CREATE TABLE text_archive_registry (
    id INTEGER PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    file_type TEXT NOT NULL, -- 'prayer', 'users', 'activity'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_modified DATETIME,
    record_count INTEGER DEFAULT 0
);
```

#### 3.2 Archive-First, Import-Second Strategy
**New Data Flow:**
1. **Write to text archive first** (creates the authoritative record)
2. **Store archive file path** in database record
3. **Import archive data** into database with file path reference
4. **All future updates** append to the same archive file

**Example Implementation:**
```python
def create_prayer_with_text_archive(prayer_data: dict):
    # Step 1: Write to text archive FIRST
    text_file_path = write_prayer_to_archive(prayer_data)
    
    # Step 2: Create database record with archive path reference
    prayer_record = Prayer(
        author_id=prayer_data['author_id'],
        text=prayer_data['text'],
        text_file_path=text_file_path,  # Track the source archive
        # ... other fields
    )
    
    # Step 3: Save to database
    db.session.add(prayer_record)
    db.session.commit()
    
    return prayer_record, text_file_path
```

#### 3.3 Text Archive Parser with Database Tracking
```python
def import_prayer_from_archive(file_path: str):
    """Import prayer from text archive, tracking the source"""
    prayer_data, activities = parse_prayer_archive(file_path)
    
    # Create prayer record with archive path
    prayer = Prayer(
        text=prayer_data['ORIGINAL_REQUEST'],
        generated_prayer=prayer_data['GENERATED_PRAYER'],
        text_file_path=file_path,  # Critical: track source archive
        # ... other fields
    )
    
    # Import activities with same archive path
    for activity in activities:
        if activity['action'] == 'PRAYED':
            prayer_mark = PrayerMark(
                prayer_id=prayer.id,
                user_id=get_user_by_name(activity['user']).id,
                text_file_path=file_path,  # All related records track same archive
                created_at=parse_timestamp(activity['timestamp'])
            )
            db.session.add(prayer_mark)
    
    db.session.commit()
    return prayer
```

#### 3.4 Append Strategy Using Archive Path Tracking
```python
def append_prayer_activity(prayer_id: int, action: str, user: str, extra: str = ""):
    """Append to the correct text archive using database tracking"""
    
    # Get the prayer record to find its text archive
    prayer = db.session.query(Prayer).filter_by(id=prayer_id).first()
    if not prayer or not prayer.text_file_path:
        raise ValueError(f"Prayer {prayer_id} has no associated text archive")
    
    # Append to the tracked text archive
    append_to_prayer_archive(prayer.text_file_path, action, user, extra)
    
    # Also create database record with same archive path
    activity_record = PrayerActivityLog(
        prayer_id=prayer_id,
        action=action,
        user_id=get_user_by_name(user).id,
        text_file_path=prayer.text_file_path,  # Same archive path
        created_at=datetime.now()
    )
    db.session.add(activity_record)
    db.session.commit()
```

### Phase 4: Session Management and Configuration

#### 4.1 Separate SQLite Session Database
**New Session Database** (`sessions.db`):
```sql
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY,
    session_token TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    display_name TEXT NOT NULL,
    user_text_file_path TEXT,  -- Reference to user's text file
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Text backup of session data for upgrade recovery
CREATE TABLE session_backups (
    id INTEGER PRIMARY KEY,
    backup_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_data TEXT NOT NULL  -- JSON of active sessions
);
```

#### 4.2 Hybrid Session Manager
```python
class HybridSessionManager:
    def __init__(self):
        self.session_db = sqlite3.connect('sessions.db')
        self.text_backup_enabled = True
    
    def create_session(self, user_data: dict) -> str:
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(days=7)
        
        # Store in separate session database
        self.session_db.execute("""
            INSERT INTO user_sessions 
            (session_token, user_id, display_name, user_text_file_path, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (session_token, user_data["id"], user_data["display_name"], 
              user_data["text_file_path"], expires_at))
        
        # Backup session data to text file for upgrade recovery
        if self.text_backup_enabled:
            self.backup_session_to_text(session_token, user_data, expires_at)
        
        return session_token
    
    def backup_session_to_text(self, token: str, user_data: dict, expires_at: datetime):
        """Backup session data for upgrade recovery"""
        session_backup = {
            "token": token,
            "user_id": user_data["id"],
            "display_name": user_data["display_name"],
            "user_text_file_path": user_data["text_file_path"],
            "expires_at": expires_at.isoformat()
        }
        
        # Store in session_backups table
        self.session_db.execute("""
            INSERT INTO session_backups (session_data) VALUES (?)
        """, (json.dumps(session_backup),))
    
    def upgrade_recovery(self):
        """Restore sessions from backups after upgrade"""
        cursor = self.session_db.execute("""
            SELECT session_data FROM session_backups 
            WHERE backup_date > datetime('now', '-7 days')
        """)
        
        for (session_json,) in cursor:
            session_data = json.loads(session_json)
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            
            # Only restore non-expired sessions
            if expires_at > datetime.now():
                # Validate user still exists in text files
                if os.path.exists(session_data["user_text_file_path"]):
                    self.restore_session(session_data)
```

#### 4.3 Configuration Options
```python
# Add to existing config
TEXT_ARCHIVE_ENABLED = True
TEXT_ARCHIVE_BASE_DIR = "./text_archives"
SESSION_DB_PATH = "./sessions.db"
SESSION_ARCHIVE_ENABLED = True
SESSION_EXPIRY_DAYS = 7
TEXT_ARCHIVE_COMPRESSION_AFTER_DAYS = 365  # Compress old files to .zip, never delete
TEXT_ARCHIVE_READONLY_AFTER_DAYS = 180     # Mark older files as read-only
```

#### 4.4 Upgrade Process with Session Preservation
```python
def upgrade_with_session_preservation():
    """Complete upgrade process preserving user sessions"""
    
    # Step 1: Backup current sessions
    session_manager = HybridSessionManager()
    session_manager.backup_all_active_sessions()
    
    # Step 2: Standard database upgrade
    backup_main_database()  # Traditional database backup
    run_database_migrations()
    import_from_text_archives()
    
    # Step 3: Restore sessions
    session_manager.upgrade_recovery()
    session_manager.cleanup_expired_sessions()
    
    print("Upgrade complete - user sessions preserved")
```

#### 4.5 Monthly Archive Compression Strategy
```python
import zipfile
from pathlib import Path

class MonthlyArchiveCompressor:
    def __init__(self, archive_base_dir: str, compression_after_days: int):
        self.archive_dir = Path(archive_base_dir)
        self.compression_threshold = timedelta(days=compression_after_days)
    
    def compress_old_months(self):
        """Compress entire months worth of files into monthly archives"""
        cutoff_date = datetime.now() - self.compression_threshold
        
        # Find months that need compression
        old_months = self.find_compressible_months(cutoff_date)
        
        for month_info in old_months:
            self.compress_month(month_info)
    
    def find_compressible_months(self, cutoff_date: datetime) -> list:
        """Find month directories that should be compressed"""
        compressible = []
        
        # Check prayer directories
        for year_dir in (self.archive_dir / "prayers").iterdir():
            if year_dir.is_dir():
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir() and self.is_month_old(month_dir, cutoff_date):
                        zip_path = month_dir.parent / f"{month_dir.name}_prayers.zip"
                        if not zip_path.exists():
                            compressible.append({
                                'type': 'prayers',
                                'path': month_dir,
                                'zip_path': zip_path
                            })
        
        # Check monthly user and activity files
        for file_type in ['users', 'activity']:
            type_dir = self.archive_dir / file_type
            if type_dir.exists():
                for txt_file in type_dir.glob("*.txt"):
                    if self.is_file_old(txt_file, cutoff_date):
                        zip_path = txt_file.with_suffix('.zip')
                        if not zip_path.exists():
                            compressible.append({
                                'type': file_type,
                                'path': txt_file,
                                'zip_path': zip_path
                            })
        
        return compressible
    
    def compress_month(self, month_info: dict):
        """Compress a month's worth of files into a single zip"""
        try:
            with zipfile.ZipFile(month_info['zip_path'], 'w', zipfile.ZIP_DEFLATED) as zf:
                if month_info['type'] == 'prayers':
                    # Compress all prayer files in the month directory
                    month_dir = month_info['path']
                    for txt_file in month_dir.glob("*.txt"):
                        zf.write(txt_file, txt_file.name)
                else:
                    # Compress single monthly file (users or activity)
                    txt_file = month_info['path']
                    zf.write(txt_file, txt_file.name)
            
            # Verify zip integrity before removing originals
            if self.verify_monthly_zip(month_info):
                self.remove_original_files(month_info)
                print(f"Compressed {month_info['type']} for {month_info['path'].name}")
            else:
                month_info['zip_path'].unlink()  # Remove bad zip
                print(f"Failed to compress {month_info['path']} - keeping originals")
                
        except Exception as e:
            print(f"Compression failed for {month_info['path']}: {e}")
    
    def verify_monthly_zip(self, month_info: dict) -> bool:
        """Verify monthly zip contains all expected files"""
        try:
            with zipfile.ZipFile(month_info['zip_path'], 'r') as zf:
                # Check zip integrity
                if zf.testzip() is not None:
                    return False
                
                # Verify all expected files are present
                if month_info['type'] == 'prayers':
                    month_dir = month_info['path']
                    expected_files = [f.name for f in month_dir.glob("*.txt")]
                else:
                    expected_files = [month_info['path'].name]
                
                zip_files = zf.namelist()
                return set(expected_files) == set(zip_files)
                
        except Exception:
            return False
    
    def remove_original_files(self, month_info: dict):
        """Remove original files after successful compression"""
        if month_info['type'] == 'prayers':
            # Remove all txt files in the month directory
            month_dir = month_info['path']
            for txt_file in month_dir.glob("*.txt"):
                txt_file.unlink()
            # Remove empty directory if no files left
            if not any(month_dir.iterdir()):
                month_dir.rmdir()
        else:
            # Remove single monthly file
            month_info['path'].unlink()
    
    def is_month_old(self, month_dir: Path, cutoff_date: datetime) -> bool:
        """Check if month directory is old enough to compress"""
        # Get most recent file modification time in the directory
        latest_mod = max(f.stat().st_mtime for f in month_dir.glob("*.txt"))
        return latest_mod < cutoff_date.timestamp()
    
    def is_file_old(self, file_path: Path, cutoff_date: datetime) -> bool:
        """Check if file is old enough to compress"""
        return file_path.stat().st_mtime < cutoff_date.timestamp()
```

#### 4.6 Archive Reading with Monthly Compression Support
```python
def read_archive_file(file_path: str) -> str:
    """Read archive file, handling both uncompressed and monthly zip formats"""
    path = Path(file_path)
    
    # First try to read uncompressed file
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # If file doesn't exist, check for monthly zip archive
    return read_from_monthly_zip(path)

def read_from_monthly_zip(file_path: Path) -> str:
    """Read file from monthly zip archive"""
    
    # Determine which monthly zip this file should be in
    if "prayers" in str(file_path):
        # Prayer file: look for YYYY/MM_prayers.zip
        month_dir = file_path.parent
        zip_path = month_dir.parent / f"{month_dir.name}_prayers.zip"
        
        if zip_path.exists():
            with zipfile.ZipFile(zip_path, 'r') as zf:
                try:
                    with zf.open(file_path.name) as zf_file:
                        return zf_file.read().decode('utf-8')
                except KeyError:
                    pass  # File not in this zip
    
    elif "users" in str(file_path) or "activity" in str(file_path):
        # Monthly user/activity file: look for filename.zip
        zip_path = file_path.with_suffix('.zip')
        
        if zip_path.exists():
            with zipfile.ZipFile(zip_path, 'r') as zf:
                try:
                    with zf.open(file_path.name) as zf_file:
                        return zf_file.read().decode('utf-8')
                except KeyError:
                    pass  # File not in this zip
    
    raise FileNotFoundError(f"Archive file not found: {file_path}")

def handle_compressed_prayer_append(prayer_file_path: str, new_activity: str):
    """Handle appending to a prayer file that might be in a monthly zip"""
    path = Path(prayer_file_path)
    
    # If file exists uncompressed, append normally
    if path.exists():
        with open(path, 'a', encoding='utf-8') as f:
            f.write(new_activity + '\n')
        return
    
    # If file is compressed, we need to extract, append, and re-compress
    month_dir = path.parent
    zip_path = month_dir.parent / f"{month_dir.name}_prayers.zip"
    
    if zip_path.exists():
        # Extract the specific file, append to it, then update the zip
        extract_append_recompress(zip_path, path.name, new_activity, month_dir)
    else:
        raise FileNotFoundError(f"Prayer file not found: {prayer_file_path}")

def extract_append_recompress(zip_path: Path, filename: str, new_content: str, temp_dir: Path):
    """Extract file from zip, append content, and update zip"""
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / filename
    
    # Extract specific file from zip
    with zipfile.ZipFile(zip_path, 'r') as zf:
        with zf.open(filename) as zf_file:
            content = zf_file.read().decode('utf-8')
    
    # Append new content
    updated_content = content + new_content + '\n'
    
    # Write updated content to temp file
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    # Update the zip file with the modified file
    with zipfile.ZipFile(zip_path, 'a') as zf:
        zf.write(temp_file, filename)
    
    # Clean up temp file
    temp_file.unlink()
```

#### 4.7 Management Interface
- Extend existing CLI with text archive and session options
- Admin endpoints for text archive status and manual triggers
- Session management commands (list active, cleanup expired)
- Archive compression commands (compress now, check compression status)
- Health checks for archive directory, session database, and permissions

## File Structure (with Monthly Compression)
```
text_archives/
├── prayers/
│   ├── 2024/
│   │   ├── 06/                                      # Current month (uncompressed)
│   │   │   ├── 2024_06_15_prayer_at_0655.txt
│   │   │   └── 2024_06_15_prayer_at_0655_2.txt
│   │   ├── 01_prayers.zip                           # Old months (monthly zip archives)
│   │   ├── 02_prayers.zip                           # Contains all prayer .txt files for that month
│   │   └── 03_prayers.zip
│   └── 2023/
│       ├── 11_prayers.zip
│       └── 12_prayers.zip
├── users/
│   ├── 2024_06_users.txt                            # Current month (uncompressed)
│   ├── 2024_01_users.txt.zip                        # Old months (individual file zips)
│   ├── 2024_02_users.txt.zip
│   └── 2023_12_users.txt.zip
└── activity/
    ├── activity_2024_06.txt                         # Current month (uncompressed)
    ├── activity_2024_01.txt.zip                     # Old months (individual file zips)
    ├── activity_2024_02.txt.zip
    └── activity_2023_12.txt.zip
```

**Compression Strategy:**
- **Prayer files**: All prayer .txt files from a month get compressed into one `MM_prayers.zip`
- **Monthly files**: Single user/activity files get compressed individually (e.g., `2024_01_users.txt.zip`)
- **Current month**: Always remains uncompressed for fast append operations
- **Append to compressed**: Automatically extract → append → re-compress when needed

## Implementation Timeline

### Week 1: Foundation
- [ ] Create `TextArchiveService` class
- [ ] Implement prayer archive format and writer
- [ ] Add configuration options
- [ ] Test with sample data

### Week 2: Core Functionality  
- [ ] Implement monthly user registration archives
- [ ] Add monthly activity logging
- [ ] Integrate with existing prayer CRUD operations
- [ ] Add archive triggers to user registration

### Week 3: Import System
- [ ] Create text archive parsers
- [ ] Extend import service for text archive format
- [ ] Add validation and error handling
- [ ] Test round-trip archive/restore

### Week 4: Testing and Validation
- [ ] Write unit tests for TextArchiveService methods
- [ ] Write integration tests for archive-first data flow
- [ ] Write compression/decompression tests
- [ ] Write session management tests
- [ ] Test round-trip archive/restore with real data
- [ ] Performance testing and optimization

### Week 5: Polish and Deployment
- [ ] Add management commands and admin interface
- [ ] Documentation and deployment preparation
- [ ] Historical data migration
- [ ] Production readiness checklist

## Testing Strategy

### Unit Tests (`tests/test_text_archive_service.py`)
```python
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from app_helpers.services.text_archive_service import TextArchiveService

class TestTextArchiveService:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.service = TextArchiveService(base_dir=self.temp_dir)
    
    def test_create_prayer_archive_file(self):
        """Test creating a new prayer archive file"""
        prayer_data = {
            'id': 12345,
            'author': 'Mary1',
            'text': 'Please pray for my family',
            'generated_prayer': 'Heavenly Father, we lift up...',
            'project_tag': 'family',
            'created_at': datetime(2024, 6, 15, 6, 55)
        }
        
        file_path = self.service.create_prayer_archive(prayer_data)
        
        # Verify file was created
        assert Path(file_path).exists()
        
        # Verify content format
        content = Path(file_path).read_text()
        assert 'Prayer 12345 by Mary1' in content
        assert 'Submitted June 15 2024 at 06:55' in content
        assert 'Please pray for my family' in content
        assert 'Activity:' in content
    
    def test_append_prayer_activity(self):
        """Test appending activity to existing prayer file"""
        # Create initial prayer file
        prayer_data = {'id': 12345, 'author': 'Mary1', 'text': 'Test prayer'}
        file_path = self.service.create_prayer_archive(prayer_data)
        
        # Append activity
        self.service.append_prayer_activity(file_path, 'prayed', 'John1')
        
        # Verify activity was appended
        content = Path(file_path).read_text()
        assert 'John1 prayed this prayer' in content
    
    def test_monthly_user_registration_append(self):
        """Test appending user registrations to monthly file"""
        self.service.append_user_registration('Sarah2', 'Mary1')
        self.service.append_user_registration('John3', 'Mary1')
        
        # Verify monthly file exists and has correct format
        monthly_files = list(Path(self.temp_dir).glob('users/*.txt'))
        assert len(monthly_files) == 1
        
        content = monthly_files[0].read_text()
        assert 'Sarah2 joined on invitation from Mary1' in content
        assert 'John3 joined on invitation from Mary1' in content
    
    def test_monthly_activity_with_date_headers(self):
        """Test monthly activity logging with automatic date headers"""
        # Add activities on same day
        self.service.append_monthly_activity('submitted prayer 123', 'Mary1')
        self.service.append_monthly_activity('prayed for prayer 123', 'John1')
        
        # Verify single date header
        activity_files = list(Path(self.temp_dir).glob('activity/*.txt'))
        content = activity_files[0].read_text()
        
        # Should have one date header for today
        today = datetime.now().strftime('%B %d %Y')
        assert content.count(today) == 1
        assert 'Mary1 submitted prayer 123' in content
        assert 'John1 prayed for prayer 123' in content

class TestMonthlyCompression:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.compressor = MonthlyArchiveCompressor(self.temp_dir, 30)  # 30 days for testing
    
    def test_compress_old_prayer_month(self):
        """Test compressing a month of prayer files"""
        # Create old prayer files
        old_month_dir = Path(self.temp_dir) / 'prayers' / '2024' / '01'
        old_month_dir.mkdir(parents=True)
        
        (old_month_dir / 'prayer1.txt').write_text('Prayer 1 content')
        (old_month_dir / 'prayer2.txt').write_text('Prayer 2 content')
        
        # Compress the month
        self.compressor.compress_old_months()
        
        # Verify zip was created and originals removed
        zip_path = old_month_dir.parent / '01_prayers.zip'
        assert zip_path.exists()
        assert not (old_month_dir / 'prayer1.txt').exists()
        
        # Verify zip contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            assert 'prayer1.txt' in zf.namelist()
            assert 'prayer2.txt' in zf.namelist()
    
    def test_read_from_compressed_archive(self):
        """Test reading files from compressed monthly archives"""
        # Create and compress files
        # ... compression setup ...
        
        # Test reading from compressed archive
        content = read_archive_file(str(old_month_dir / 'prayer1.txt'))
        assert content == 'Prayer 1 content'
    
    def test_append_to_compressed_prayer(self):
        """Test appending activity to a compressed prayer file"""
        # Create, compress, then try to append
        # ... setup compressed file ...
        
        handle_compressed_prayer_append(
            str(old_month_dir / 'prayer1.txt'),
            'June 15 2024 at 14:30 - John1 prayed this prayer'
        )
        
        # Verify content was appended and zip updated
        content = read_archive_file(str(old_month_dir / 'prayer1.txt'))
        assert 'John1 prayed this prayer' in content
```

### Integration Tests (`tests/test_archive_integration.py`)
```python
class TestArchiveFirstDataFlow:
    def test_complete_prayer_lifecycle(self):
        """Test full prayer lifecycle with archive-first approach"""
        # Submit prayer (archive-first)
        prayer_data = {
            'author_id': 1,
            'text': 'Test prayer request',
            'project_tag': 'family'
        }
        
        prayer, archive_path = create_prayer_with_text_archive(prayer_data)
        
        # Verify archive file exists and has correct content
        assert Path(archive_path).exists()
        content = Path(archive_path).read_text()
        assert 'Test prayer request' in content
        
        # Verify database record points to archive
        assert prayer.text_file_path == archive_path
        
        # Add prayer activity
        append_prayer_activity(prayer.id, 'prayed', 'John1')
        
        # Verify activity in both archive and database
        archive_content = Path(archive_path).read_text()
        assert 'John1 prayed this prayer' in archive_content
        
        activity_record = db.session.query(PrayerActivityLog).filter_by(
            prayer_id=prayer.id
        ).first()
        assert activity_record.text_file_path == archive_path
    
    def test_database_recreation_from_archives(self):
        """Test recreating database from text archives"""
        # Create sample data with archives
        # ... create prayers, users, activities ...
        
        # Clear database
        db.session.query(Prayer).delete()
        db.session.query(User).delete()
        db.session.commit()
        
        # Recreate from archives
        import_from_text_archives()
        
        # Verify all data was restored correctly
        prayers = db.session.query(Prayer).all()
        assert len(prayers) > 0
        
        for prayer in prayers:
            assert prayer.text_file_path is not None
            assert Path(prayer.text_file_path).exists()

class TestSessionManagement:
    def test_session_preservation_during_upgrade(self):
        """Test that sessions survive database upgrades"""
        session_manager = HybridSessionManager()
        
        # Create active session
        user_data = {'id': 1, 'display_name': 'Mary1', 'text_file_path': '/path/to/user.txt'}
        session_token = session_manager.create_session(user_data)
        
        # Simulate upgrade process
        session_manager.backup_all_active_sessions()
        
        # Clear session storage (simulating upgrade)
        session_manager.session_db.execute("DELETE FROM user_sessions")
        
        # Restore from backup
        session_manager.upgrade_recovery()
        
        # Verify session was restored
        restored_session = session_manager.get_session(session_token)
        assert restored_session['display_name'] == 'Mary1'
```

### Performance Tests (`tests/test_archive_performance.py`)
```python
class TestArchivePerformance:
    def test_large_prayer_file_append_performance(self):
        """Test performance of appending to large prayer files"""
        # Create large prayer file (simulate months of activity)
        large_content = "\\n".join([f"Activity {i}" for i in range(10000)])
        
        start_time = time.time()
        append_prayer_activity(file_path, 'prayed', 'TestUser')
        append_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert append_time < 0.1  # 100ms
    
    def test_compressed_file_access_performance(self):
        """Test performance of reading compressed archive files"""
        # Create and compress large archive
        # ... setup ...
        
        start_time = time.time()
        content = read_archive_file(compressed_file_path)
        read_time = time.time() - start_time
        
        # Should be reasonably fast even for compressed files
        assert read_time < 1.0  # 1 second
    
    def test_monthly_compression_performance(self):
        """Test performance of monthly compression operation"""
        # Create month with many prayer files
        # ... setup 1000+ files ...
        
        start_time = time.time()
        compressor.compress_old_months()
        compression_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert compression_time < 30.0  # 30 seconds for large month
```

## Risk Mitigation

### Data Integrity
- Atomic file operations with temporary files
- File locking to prevent corruption
- Checksums or validation for critical files
- Regular archive verification

### Performance Impact
- Asynchronous text file writing
- Batch operations for activity logs
- Configurable archive frequency
- Optional compression for large files

### Storage Management
- Configurable retention policies
- Automatic cleanup of old files
- Compression options for archival
- Directory structure optimization

## Benefits

### Immediate
- **Human-readable archives**: Easy to review and understand without database tools
- **Data loss protection**: Independent of database format and application code
- **Migration flexibility**: Can reconstruct database in any format
- **Audit trail**: Clear timeline of all site activity

### Long-term
- **Database independence**: Not tied to SQLite or any specific database
- **Debugging aid**: Easy to trace issues through readable logs
- **Compliance**: Clear records for privacy or legal requirements
- **Community transparency**: Exportable community activity summaries

## Additional Considerations

### Privacy and Security
- Exclude sensitive authentication data (passwords, tokens)
- Include only display names, not real names
- Option to anonymize or pseudonymize exports
- Respect user privacy preferences

### Extensibility
- Plugin architecture for custom export formats
- API endpoints for third-party archive tools  
- Webhook support for real-time archive triggers
- Integration with cloud storage services

This plan leverages your existing robust export/import infrastructure while adding the human-readable text format you requested. The modular approach allows for incremental implementation and testing at each phase.