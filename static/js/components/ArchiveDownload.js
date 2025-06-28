class ArchiveDownload {
    constructor() {
        this.baseUrl = '/api/archive';
        this.currentUser = null;
        this.archiveMetadata = null;
    }
    
    async init() {
        console.log('Initializing ArchiveDownload component');
        this.currentUser = await this.getCurrentUser();
        console.log('Current user:', this.currentUser);
        
        if (this.currentUser) {
            await this.loadArchiveMetadata();
            this.render();
        } else {
            console.warn('No user found - showing guest message');
            this.renderGuestMessage();
        }
    }
    
    async getCurrentUser() {
        try {
            // Get current user info from the page context
            const userInfo = document.querySelector('meta[name="current-user"]');
            console.log('Found meta tag:', userInfo);
            
            if (userInfo) {
                console.log('Meta content:', userInfo.content);
                const parsed = JSON.parse(userInfo.content);
                console.log('Parsed user:', parsed);
                return parsed;
            }
            
            // Fallback: try to extract from page elements
            console.log('Trying fallback user detection');
            const userLinks = document.querySelectorAll('a[href^="/user/"], a[href^="/profile"]');
            console.log('Found user links:', userLinks.length);
            
            if (userLinks.length > 0) {
                const href = userLinks[0].href;
                console.log('Using href:', href);
                const userId = href.split('/user/')[1] || href.split('/profile')[0].split('/').pop();
                console.log('Extracted user ID:', userId);
                return { id: userId };
            }
            
            // Try to find user name from header
            const profileLink = document.querySelector('a[href="/profile"]');
            if (profileLink) {
                console.log('Found profile link, extracting from text');
                const headerText = profileLink.parentElement.textContent;
                console.log('Header text:', headerText);
                const match = headerText.match(/Hi\s+(\w+)/);
                if (match) {
                    return { id: 'unknown', display_name: match[1] };
                }
            }
            
            console.log('No user found through any method');
            return null;
        } catch (error) {
            console.error('Failed to get current user:', error);
            return null;
        }
    }
    
    async loadArchiveMetadata() {
        if (!this.currentUser) {
            console.log('No current user found for metadata loading');
            return;
        }
        
        try {
            console.log(`Loading metadata for user: ${this.currentUser.id}`);
            const response = await fetch(`${this.baseUrl}/user/${this.currentUser.id}/metadata`);
            if (response.ok) {
                this.archiveMetadata = await response.json();
                console.log('Archive metadata loaded:', this.archiveMetadata);
            } else {
                console.error('Failed to load metadata, status:', response.status);
                // Set default metadata to show something
                this.archiveMetadata = {
                    archive_statistics: {
                        total_prayers: 'Loading...',
                        total_activities: 'Loading...',
                        date_range: { earliest: null, latest: null }
                    }
                };
            }
        } catch (error) {
            console.error('Failed to load archive metadata:', error);
            // Set error state metadata
            this.archiveMetadata = {
                archive_statistics: {
                    total_prayers: 'Error',
                    total_activities: 'Error',
                    date_range: { earliest: null, latest: null }
                }
            };
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
    
    renderGuestMessage() {
        const container = document.getElementById('archive-download-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="archive-download-section">
                <h3>📁 Text Archives</h3>
                <p>Text archives provide human-readable access to all community data. Please log in to access download functionality.</p>
                <div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg p-4">
                    <p class="text-sm text-yellow-800 dark:text-yellow-200">
                        🔒 Login required to download archives. Once logged in, you'll be able to download your personal archives and complete community archives.
                    </p>
                </div>
            </div>
        `;
    }
    
    render() {
        const container = document.getElementById('archive-download-container');
        if (!container) {
            console.error('Archive download container not found');
            return;
        }
        
        const stats = this.archiveMetadata?.archive_statistics || {};
        console.log('Rendering with stats:', stats);
        
        container.innerHTML = `
            <div class="archive-download-section">
                <h3>📁 Personal Archive Options</h3>
                <p>Get your data in an organized personal folder structure.</p>
                
                <div class="archive-stats">
                    <div class="stat-item">
                        <strong>${stats.total_prayers || 0}</strong>
                        <span>Your Prayers</span>
                    </div>
                    <div class="stat-item">
                        <strong>${stats.total_activities || 0}</strong>
                        <span>Your Activities</span>
                    </div>
                    <div class="stat-item">
                        <strong>${this.formatDateRange(stats.date_range)}</strong>
                        <span>Date Range</span>
                    </div>
                </div>
                
                <div class="download-options">
                    <div class="download-option">
                        <h4>📂 Personal Archive</h4>
                        <p>Your prayers and activities in a personalized folder structure</p>
                        <button class="btn btn-primary" onclick="archiveDownload.downloadUserArchive(false)">
                            📥 Download My Data
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