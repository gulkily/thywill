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
    
    async getCurrentUser() {
        try {
            // Get current user info from the page context
            // This is a simple approach - in a real app you might have this in a global variable
            const userInfo = document.querySelector('meta[name="current-user"]');
            if (userInfo) {
                return JSON.parse(userInfo.content);
            }
            
            // Fallback: try to extract from page elements
            const userLinks = document.querySelectorAll('a[href^="/user/"]');
            if (userLinks.length > 0) {
                const href = userLinks[0].href;
                const userId = href.split('/user/')[1];
                return { id: parseInt(userId) };
            }
            
            return null;
        } catch (error) {
            console.error('Failed to get current user:', error);
            return null;
        }
    }
    
    async loadArchiveMetadata() {
        if (!this.currentUser) return;
        
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
        if (!this.currentUser) {
            this.showErrorMessage('User information not available');
            return;
        }
        
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
    
    showLoadingState(message = '📦 Creating your archive... This may take a moment.') {
        const status = document.getElementById('download-status');
        if (status) {
            status.innerHTML = `<div class="loading">${message}</div>`;
            status.className = 'download-status loading';
        }
    }
    
    hideLoadingState() {
        const status = document.getElementById('download-status');
        if (status) {
            status.innerHTML = '';
            status.className = 'download-status';
        }
    }
    
    showSuccessMessage(message) {
        const status = document.getElementById('download-status');
        if (status) {
            status.innerHTML = `<div class="success">✅ ${message}</div>`;
            status.className = 'download-status success';
            setTimeout(() => this.hideLoadingState(), 3000);
        }
    }
    
    showErrorMessage(message) {
        const status = document.getElementById('download-status');
        if (status) {
            status.innerHTML = `<div class="error">❌ ${message}</div>`;
            status.className = 'download-status error';
        }
    }
}

// Initialize when page loads
const archiveDownload = new ArchiveDownload();
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if we're on a page with the archive download container
    if (document.getElementById('archive-download-container')) {
        archiveDownload.init();
    }
});