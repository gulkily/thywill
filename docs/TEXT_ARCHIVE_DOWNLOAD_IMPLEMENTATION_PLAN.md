# Text Archive Download Implementation Plan

## Overview
Implement user-facing download functionality for the ThyWill text archive system. This builds on the existing text archive infrastructure (~75% complete) to provide users with complete access to human-readable data archives. **Key Requirement**: All users should be able to download the entire site's text archive, and individual prayer pages should include direct links to their corresponding text files.

## Current State Analysis
- **✅ Core Text Archive System**: TextArchiveService and ArchiveFirstService are fully implemented
- **✅ Archive Files**: Live text archives are being created and maintained in `/text_archives/`
- **✅ Database Integration**: Schema includes `text_file_path` fields linking records to archives
- **✅ Archive-First Data Flow**: Prayers, users, and activities write to text archives first
- **❌ User Download Access**: No way for users to access or download archives
- **❌ Full Site Archive Download**: No endpoint for downloading complete community archives
- **❌ Prayer Page Archive Links**: No links from prayer pages to their text files
- **❌ Compression System**: Monthly compression is configured but not implemented
- **❌ Management Interface**: No web UI or API for archive access

## Implementation Strategy

### Phase 1: Core Download API (Priority: High)
**Estimated Time**: 2-3 days

#### 1.1 Download Service (`app_helpers/services/archive_download_service.py`)

```python
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import shutil

class ArchiveDownloadService:
    def __init__(self, archive_base_dir: str):
        self.archive_dir = Path(archive_base_dir)
        
    def create_user_archive_zip(self, user_id: int, include_community: bool = True) -> str:
        """Create ZIP file containing all user's text archives"""
        
    def get_user_archive_metadata(self, user_id: int) -> Dict:
        """Get metadata about user's available archives"""
        
    def list_community_archives(self) -> List[Dict]:
        """List all community archive files with metadata"""
        
    def create_full_community_zip(self) -> str:
        """Create ZIP of entire community text archive"""
```

**Key Methods Implementation:**

```python
def create_user_archive_zip(self, user_id: int, include_community: bool = True) -> str:
    """Create comprehensive ZIP file of user's text archives"""
    
    # Get user info
    user = db.session.query(User).filter_by(id=user_id).first()
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
            (personal_dir / "registration.txt").write_text(registration_content)
        
        # 2. User's Prayers
        prayers_dir = user_archive_dir / "prayers"
        prayers_dir.mkdir()
        
        user_prayers = db.session.query(Prayer).filter_by(author_id=user_id).all()
        for prayer in user_prayers:
            if prayer.text_file_path and Path(prayer.text_file_path).exists():
                # Read from archive (handles compressed files)
                content = self._read_archive_file(prayer.text_file_path)
                filename = f"prayer_{prayer.id}_{prayer.created_at.strftime('%Y_%m_%d')}.txt"
                (prayers_dir / filename).write_text(content)
        
        # 3. User's Prayer Activities
        activities_dir = user_archive_dir / "activities"
        activities_dir.mkdir()
        
        # Get all prayers user has interacted with
        user_marks = db.session.query(PrayerMark).filter_by(user_id=user_id).all()
        activity_summary = self._create_user_activity_summary(user, user_marks)
        (activities_dir / "my_prayer_activities.txt").write_text(activity_summary)
        
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

def get_user_archive_metadata(self, user_id: int) -> Dict:
    """Get comprehensive metadata about user's archives"""
    
    user = db.session.query(User).filter_by(id=user_id).first()
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
    user_prayers = db.session.query(Prayer).filter_by(author_id=user_id).all()
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
    user_marks = db.session.query(PrayerMark).filter_by(user_id=user_id).all()
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
            if year_dir.is_dir():
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir():
                        file_count = len(list(month_dir.glob("*.txt")))
                        if file_count > 0:
                            archives.append({
                                "type": "prayers",
                                "period": f"{year_dir.name}-{month_dir.name}",
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
            archives.append({
                "type": "users",
                "period": user_file.stem.replace("_users", ""),
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
```

#### 1.2 Download API Endpoints (`app/api/archive_routes.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer
from app_helpers.services.archive_download_service import ArchiveDownloadService
from app_helpers.config import TEXT_ARCHIVE_BASE_DIR
import os

router = APIRouter(prefix="/api/archive", tags=["archives"])
security = HTTPBearer()

@router.get("/user/{user_id}/download")
async def download_user_archive(
    user_id: int, 
    include_community: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Download user's complete text archive as ZIP file"""
    
    # Verify user can access this archive
    if current_user["user_id"] != user_id and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        download_service = ArchiveDownloadService(TEXT_ARCHIVE_BASE_DIR)
        zip_path = download_service.create_user_archive_zip(user_id, include_community)
        
        # Return file for download
        filename = os.path.basename(zip_path)
        return FileResponse(
            path=zip_path,
            filename=filename,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Archive creation failed: {str(e)}")

@router.get("/user/{user_id}/metadata")
async def get_user_archive_metadata(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get metadata about user's available archives"""
    
    # Verify user can access this metadata
    if current_user["user_id"] != user_id and not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        download_service = ArchiveDownloadService(TEXT_ARCHIVE_BASE_DIR)
        metadata = download_service.get_user_archive_metadata(user_id)
        return metadata
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata retrieval failed: {str(e)}")

@router.get("/community/list")
async def list_community_archives(
    current_user: dict = Depends(get_current_user)
):
    """List all community archive files (available to all users)"""
    
    try:
        download_service = ArchiveDownloadService(TEXT_ARCHIVE_BASE_DIR)
        archives = download_service.list_community_archives()
        return {"archives": archives}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Archive listing failed: {str(e)}")

@router.get("/community/download")
async def download_community_archive(
    current_user: dict = Depends(get_current_user)
):
    """Download complete community text archive (available to all users)"""
    
    try:
        download_service = ArchiveDownloadService(TEXT_ARCHIVE_BASE_DIR)
        zip_path = download_service.create_full_community_zip()
        
        filename = os.path.basename(zip_path)
        return FileResponse(
            path=zip_path,
            filename=filename,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Community archive creation failed: {str(e)}")

@router.get("/prayer/{prayer_id}/file")
async def get_prayer_archive_file(
    prayer_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get direct link to prayer's text archive file"""
    
    try:
        from app.models import Prayer
        prayer = db.session.query(Prayer).filter_by(id=prayer_id).first()
        
        if not prayer:
            raise HTTPException(status_code=404, detail="Prayer not found")
        
        if not prayer.text_file_path:
            raise HTTPException(status_code=404, detail="No archive file for this prayer")
        
        # Read the archive file content
        download_service = ArchiveDownloadService(TEXT_ARCHIVE_BASE_DIR)
        content = download_service._read_archive_file(prayer.text_file_path)
        
        # Return as plain text file
        filename = f"prayer_{prayer_id}_{prayer.created_at.strftime('%Y_%m_%d')}.txt"
        return Response(
            content=content,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Archive file access failed: {str(e)}")

@router.delete("/downloads/cleanup")
async def cleanup_old_downloads(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Clean up old download files (admin only)"""
    
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    def cleanup_downloads():
        download_service = ArchiveDownloadService(TEXT_ARCHIVE_BASE_DIR)
        download_service.cleanup_old_downloads(max_age_hours=24)
    
    background_tasks.add_task(cleanup_downloads)
    return {"message": "Download cleanup scheduled"}
```

### Phase 2: Prayer Page Integration (Priority: High)
**Estimated Time**: 1 day

#### 2.1 Prayer Page Archive Link Component

Add archive file links directly to individual prayer pages. Each prayer should show a link to download its text archive file.

**Add to prayer page template** (`templates/prayer_detail.html` or equivalent):

```html
<!-- Archive File Link Section -->
<div class="prayer-archive-section">
    <h4>📁 Text Archive</h4>
    <p>Download this prayer's complete activity log in human-readable format.</p>
    
    {% if prayer.text_file_path %}
        <a href="/api/archive/prayer/{{ prayer.id }}/file" 
           class="btn btn-sm btn-outline-secondary"
           download="prayer_{{ prayer.id }}_{{ prayer.created_at.strftime('%Y_%m_%d') }}.txt">
            📄 Download Text File
        </a>
        
        <div class="archive-info-small">
            <small class="text-muted">
                Contains: Original request, generated prayer, and complete activity timeline
            </small>
        </div>
    {% else %}
        <div class="archive-unavailable">
            <small class="text-muted">
                📄 Text archive not available for this prayer
            </small>
        </div>
    {% endif %}
</div>
```

#### 2.2 Prayer Page Archive CSS

**Add to main CSS file** (`static/css/main.css`):

```css
.prayer-archive-section {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 4px;
    padding: 15px;
    margin: 20px 0;
}

.prayer-archive-section h4 {
    margin: 0 0 8px 0;
    font-size: 1.1em;
    color: #495057;
}

.prayer-archive-section p {
    margin: 0 0 12px 0;
    color: #6c757d;
    font-size: 0.9em;
}

.archive-info-small {
    margin-top: 8px;
}

.archive-unavailable {
    color: #6c757d;
    font-style: italic;
}

.btn-outline-secondary {
    border-color: #6c757d;
    color: #6c757d;
}

.btn-outline-secondary:hover {
    background-color: #6c757d;
    color: white;
}
```

### Phase 3: Web Interface (Priority: High)
**Estimated Time**: 2 days

#### 3.1 Archive Download Component (`static/js/components/ArchiveDownload.js`)

```javascript
class ArchiveDownload {
    constructor() {
        this.baseUrl = '/api/archive';
        this.currentUser = null;
        this.archiveMetadata = null;
    }
    
    async init() {
        this.currentUser = await this.getCurrentUser();
        if (this.currentUser) {
            await this.loadArchiveMetadata();
            this.render();
        }
    }
    
    async loadArchiveMetadata() {
        try {
            const response = await fetch(`${this.baseUrl}/user/${this.currentUser.id}/metadata`);
            if (response.ok) {
                this.archiveMetadata = await response.json();
            }
        } catch (error) {
            console.error('Failed to load archive metadata:', error);
        }
    }
    
    async downloadUserArchive(includeCommunity = true) {
        try {
            const url = `${this.baseUrl}/user/${this.currentUser.id}/download?include_community=${includeCommunity}`;
            
            // Show loading state
            this.showLoadingState();
            
            const response = await fetch(url);
            if (response.ok) {
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'archive.zip';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                window.URL.revokeObjectURL(downloadUrl);
                this.showSuccessMessage('Archive downloaded successfully!');
            } else {
                throw new Error('Download failed');
            }
        } catch (error) {
            this.showErrorMessage('Failed to download archive: ' + error.message);
        } finally {
            this.hideLoadingState();
        }
    }
    
    async downloadFullSiteArchive() {
        try {
            const url = `${this.baseUrl}/community/download`;
            
            // Show loading state for potentially large download
            this.showLoadingState('Creating complete site archive... This may take several minutes for large communities.');
            
            const response = await fetch(url);
            if (response.ok) {
                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = response.headers.get('Content-Disposition')?.split('filename=')[1] || 'complete_site_archive.zip';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                window.URL.revokeObjectURL(downloadUrl);
                this.showSuccessMessage('Complete site archive downloaded successfully!');
            } else {
                throw new Error('Download failed');
            }
        } catch (error) {
            this.showErrorMessage('Failed to download site archive: ' + error.message);
        } finally {
            this.hideLoadingState();
        }
    }
    
    render() {
        const container = document.getElementById('archive-download-container');
        if (!container) return;
        
        const stats = this.archiveMetadata?.archive_statistics || {};
        
        container.innerHTML = `
            <div class="archive-download-section">
                <h3>📁 Your Text Archive</h3>
                <p>Download your complete prayer history and activities in human-readable text format.</p>
                
                <div class="archive-stats">
                    <div class="stat-item">
                        <strong>${stats.total_prayers || 0}</strong>
                        <span>Prayers</span>
                    </div>
                    <div class="stat-item">
                        <strong>${stats.total_activities || 0}</strong>
                        <span>Activities</span>
                    </div>
                    <div class="stat-item">
                        <strong>${this.formatDateRange(stats.date_range)}</strong>
                        <span>Date Range</span>
                    </div>
                </div>
                
                <div class="download-options">
                    <div class="download-option">
                        <h4>Personal Archive</h4>
                        <p>Your prayers and activities only</p>
                        <button class="btn btn-primary" onclick="archiveDownload.downloadUserArchive(false)">
                            📥 Download Personal Archive
                        </button>
                    </div>
                    
                    <div class="download-option">
                        <h4>Your Data + Community</h4>
                        <p>Your data plus community activity logs</p>
                        <button class="btn btn-primary" onclick="archiveDownload.downloadUserArchive(true)">
                            📥 Download Personal + Community
                        </button>
                    </div>
                    
                    <div class="download-option">
                        <h4>Complete Site Archive</h4>
                        <p>All prayers, users, and activity from the entire site</p>
                        <button class="btn btn-secondary" onclick="archiveDownload.downloadFullSiteArchive()">
                            📥 Download Complete Site Archive
                        </button>
                    </div>
                </div>
                
                <div class="archive-info">
                    <h4>📄 About Text Archives</h4>
                    <ul>
                        <li>Human-readable text format</li>
                        <li>Complete activity timeline</li>
                        <li>Portable and future-proof</li>
                        <li>No database required to read</li>
                    </ul>
                </div>
                
                <div id="download-status" class="download-status"></div>
            </div>
        `;
    }
    
    formatDateRange(range) {
        if (!range || !range.earliest) return 'No data';
        const start = new Date(range.earliest).toLocaleDateString();
        const end = new Date(range.latest).toLocaleDateString();
        return start === end ? start : `${start} - ${end}`;
    }
    
    showLoadingState() {
        const status = document.getElementById('download-status');
        status.innerHTML = '<div class="loading">📦 Creating your archive... This may take a moment.</div>';
        status.className = 'download-status loading';
    }
    
    hideLoadingState() {
        const status = document.getElementById('download-status');
        status.innerHTML = '';
        status.className = 'download-status';
    }
    
    showSuccessMessage(message) {
        const status = document.getElementById('download-status');
        status.innerHTML = `<div class="success">✅ ${message}</div>`;
        status.className = 'download-status success';
        setTimeout(() => this.hideLoadingState(), 3000);
    }
    
    showErrorMessage(message) {
        const status = document.getElementById('download-status');
        status.innerHTML = `<div class="error">❌ ${message}</div>`;
        status.className = 'download-status error';
    }
}

// Initialize when page loads
const archiveDownload = new ArchiveDownload();
document.addEventListener('DOMContentLoaded', () => archiveDownload.init());
```

#### 3.2 Archive Section in Settings Page

**Add to `templates/settings.html`:**

```html
<!-- Text Archive Section -->
<section class="settings-section">
    <h2>📁 Text Archive</h2>
    <p>Download your complete prayer history in human-readable text format.</p>
    
    <div id="archive-download-container">
        <!-- Archive download component will render here -->
    </div>
</section>

<script src="/static/js/components/ArchiveDownload.js"></script>
```

#### 3.3 CSS Styles (`static/css/archive.css`)

```css
.archive-download-section {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}

.archive-stats {
    display: flex;
    gap: 20px;
    margin: 15px 0;
    flex-wrap: wrap;
}

.stat-item {
    text-align: center;
    padding: 10px;
    background: white;
    border-radius: 4px;
    border: 1px solid #dee2e6;
    min-width: 100px;
}

.stat-item strong {
    display: block;
    font-size: 1.5em;
    color: #007bff;
}

.download-options {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin: 20px 0;
}

.download-option {
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 15px;
}

.download-option h4 {
    margin: 0 0 8px 0;
    color: #495057;
}

.download-option p {
    margin: 0 0 15px 0;
    color: #6c757d;
    font-size: 0.9em;
}

.archive-info {
    background: #e7f3ff;
    border: 1px solid #b8daff;
    border-radius: 4px;
    padding: 15px;
    margin: 20px 0;
}

.archive-info h4 {
    margin: 0 0 10px 0;
    color: #004085;
}

.archive-info ul {
    margin: 0;
    padding-left: 20px;
}

.archive-info li {
    color: #004085;
    margin: 5px 0;
}

.download-status {
    margin: 15px 0;
    padding: 10px;
    border-radius: 4px;
    text-align: center;
}

.download-status.loading {
    background: #fff3cd;
    border: 1px solid #ffeaa7;
    color: #856404;
}

.download-status.success {
    background: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
}

.download-status.error {
    background: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
}

@media (max-width: 768px) {
    .archive-stats {
        justify-content: center;
    }
    
    .download-options {
        grid-template-columns: 1fr;
    }
}
```

### Phase 4: Compression System (Priority: Medium)
**Estimated Time**: 3-4 days

#### 4.1 Monthly Compression Service (`app_helpers/services/archive_compression_service.py`)

```python
import zipfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

class ArchiveCompressionService:
    def __init__(self, archive_base_dir: str, compression_after_days: int = 365):
        self.archive_dir = Path(archive_base_dir)
        self.compression_threshold = timedelta(days=compression_after_days)
        
    def compress_old_archives(self) -> Dict:
        """Compress archives older than threshold"""
        
    def decompress_archive_for_reading(self, compressed_path: str) -> str:
        """Temporarily decompress for reading"""
        
    def append_to_compressed_prayer(self, prayer_file_path: str, new_activity: str):
        """Append activity to compressed prayer file"""
```

#### 4.2 Compressed File Reading Support

```python
def read_archive_file_with_compression(file_path: str) -> str:
    """Read archive file, handling both compressed and uncompressed"""
    
    path = Path(file_path)
    
    # Try uncompressed first
    if path.exists():
        return path.read_text(encoding='utf-8')
    
    # Try compressed archives
    return read_from_compressed_archive(path)

def read_from_compressed_archive(file_path: Path) -> str:
    """Read file from monthly compressed archive"""
    
    if "prayers" in str(file_path):
        # Look for monthly prayer zip
        month_dir = file_path.parent
        zip_path = month_dir.parent / f"{month_dir.name}_prayers.zip"
        
        if zip_path.exists():
            with zipfile.ZipFile(zip_path, 'r') as zf:
                with zf.open(file_path.name) as zf_file:
                    return zf_file.read().decode('utf-8')
    
    elif "users" in str(file_path) or "activity" in str(file_path):
        # Look for individual file zip
        zip_path = file_path.with_suffix('.zip')
        
        if zip_path.exists():
            with zipfile.ZipFile(zip_path, 'r') as zf:
                with zf.open(file_path.name) as zf_file:
                    return zf_file.read().decode('utf-8')
    
    raise FileNotFoundError(f"Archive file not found: {file_path}")
```

### Phase 5: CLI Extensions (Priority: Low)
**Estimated Time**: 1-2 days

#### 5.1 Archive CLI Commands (`thywill_cli/commands/archive.py`)

```python
import click
from app_helpers.services.archive_download_service import ArchiveDownloadService
from app_helpers.services.archive_compression_service import ArchiveCompressionService

@click.group()
def archive():
    """Text archive management commands"""
    pass

@archive.command()
@click.option('--user-id', type=int, help='User ID to create archive for')
@click.option('--output', '-o', help='Output directory for archive')
@click.option('--include-community/--personal-only', default=True, help='Include community archives')
def create_user_archive(user_id, output, include_community):
    """Create user archive ZIP file"""
    
@archive.command()
def list_archives():
    """List all available text archives"""
    
@archive.command()
@click.option('--dry-run', is_flag=True, help='Show what would be compressed without doing it')
def compress_old():
    """Compress old archive files to save space"""
    
@archive.command()
def status():
    """Show text archive system status"""
```

### Phase 6: Advanced Features (Future)
**Estimated Time**: 2-3 days

#### 6.1 Selective Download Options
- Download specific date ranges
- Download by prayer project/tag
- Download specific file types only

#### 6.2 Archive Streaming
- Stream large archives instead of creating temporary files
- Progressive download for very large communities

#### 6.3 Archive Analytics
- Archive size statistics
- Growth trends over time
- Most active periods

## Implementation Timeline

### Week 1: Core Download API
- **Day 1-2**: Implement `ArchiveDownloadService` class
- **Day 3**: Create download API endpoints
- **Day 4**: Add authentication and security
- **Day 5**: Testing and validation

### Week 2: Prayer Page Integration & Web Interface
- **Day 1**: Add archive links to prayer pages with CSS
- **Day 2**: Create `ArchiveDownload` JavaScript component  
- **Day 3**: Integrate with settings page and add CSS
- **Day 4**: User testing and mobile responsiveness
- **Day 5**: Cross-browser testing and refinement

### Week 3: Compression System (Optional)
- **Day 1-2**: Implement compression service
- **Day 3**: Add compressed file reading support
- **Day 4**: Update download service to handle compressed files
- **Day 5**: Testing compression/decompression

### Week 4: CLI and Polish
- **Day 1**: CLI archive commands
- **Day 2**: Error handling and edge cases
- **Day 3**: Performance optimization
- **Day 4**: Documentation
- **Day 5**: Production deployment

## Testing Strategy

### Unit Tests (`tests/test_archive_download.py`)
```python
class TestArchiveDownloadService:
    def test_create_user_archive_zip(self):
        """Test ZIP creation for user archives"""
        
    def test_user_archive_metadata(self):
        """Test metadata retrieval accuracy"""
        
    def test_permission_enforcement(self):
        """Test user can only access own archives"""
        
    def test_admin_community_access(self):
        """Test admin can access community archives"""

class TestDownloadAPI:
    def test_download_endpoint_auth(self):
        """Test download endpoint authentication"""
        
    def test_download_file_response(self):
        """Test proper file response headers"""
        
    def test_metadata_endpoint(self):
        """Test metadata endpoint response format"""
```

### Integration Tests (`tests/test_archive_integration.py`)
```python
class TestArchiveDownloadIntegration:
    def test_full_download_workflow(self):
        """Test complete download workflow"""
        
    def test_compressed_file_handling(self):
        """Test download with compressed archives"""
        
    def test_large_archive_creation(self):
        """Test performance with large archives"""
```

## Security Considerations

### Access Control
- Users can download their own personal archives
- **All users can download complete site archives** (community transparency)
- JWT token validation for all endpoints
- Rate limiting on download endpoints to prevent abuse

### Data Privacy
- Exclude sensitive authentication data
- Use display names only, not real names
- Optional anonymization for shared archives
- Respect user privacy preferences

### File System Security
- Temporary file cleanup
- Path traversal prevention
- File size limits for downloads
- Secure temporary directory usage

## Performance Optimization

### Caching Strategy
- Cache user metadata for 15 minutes
- Background ZIP creation for large archives
- Cleanup old download files automatically

### Memory Management
- Stream large files instead of loading into memory
- Use temporary directories for ZIP creation
- Limit concurrent download operations

### Storage Efficiency
- Compress old archives automatically
- Remove duplicate files in community archives
- Optimize ZIP compression settings

## Benefits

### Immediate User Value
- **Complete Data Access**: Users get their entire prayer history AND full site archives
- **Community Transparency**: Everyone can download complete community data
- **Human-Readable Format**: No database tools required to read archives
- **Data Portability**: Archives work independently of ThyWill application
- **Peace of Mind**: Users have their own copy of their data and can verify community activity

### Long-term Benefits
- **Transparency**: Users can verify their data is accurate
- **Trust Building**: Demonstrates commitment to user data ownership
- **Compliance**: Supports GDPR data portability requirements
- **Community Growth**: Users feel secure knowing they own their data

## Risk Mitigation

### Performance Risks
- **Large Archive Creation**: Use background tasks for large ZIP files
- **Storage Usage**: Implement automatic cleanup of old downloads
- **Memory Usage**: Stream files instead of loading into memory

### Security Risks
- **Unauthorized Access**: Strict authentication and authorization
- **Path Traversal**: Validate all file paths
- **Resource Exhaustion**: Rate limiting and file size limits

### Data Integrity Risks
- **Corruption During ZIP**: Verify ZIP integrity before serving
- **Missing Files**: Graceful handling of missing archive files
- **Encoding Issues**: Consistent UTF-8 encoding throughout

This implementation plan builds on the existing 75% complete text archive system to provide comprehensive user download functionality while maintaining security, performance, and data integrity.