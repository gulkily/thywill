# Testimony Feature Implementation Plan

## Overview
Add a standalone testimony feature allowing users to share stories of answered prayers from before/outside the ThyWill system, with support for text, audio, and video testimonies.

## Core Requirements

### User Experience
- Standalone testimony posts (not linked to existing prayers)
- Separate "Testimonies" section in navigation
- Focus on sharing and encouragement rather than interaction
- Support for text, audio, and video testimonies
- Automatic transcription for audio/video content

### Content Moderation
- **Established Users**: Immediate visibility (auto-approved)
- **New Users**: Requires moderation before visibility
- Admin review panel for pending testimonies

### Optional Testimony Fields
- Date when prayer was answered (optional)
- Brief description of original prayer request (optional)
- Detailed testimony of how prayer was answered (required)
- Audio/video file upload (optional)
- Tags/categories (optional)

## Technical Implementation

### Database Schema

#### New Models
```sql
-- Testimony model
CREATE TABLE testimonies (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT,
    prayer_description TEXT,
    testimony_content TEXT NOT NULL,
    answered_date DATE,
    media_file_path TEXT,
    media_type TEXT, -- 'audio', 'video', or NULL
    transcription TEXT,
    status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Testimony moderation
CREATE TABLE testimony_moderation (
    id INTEGER PRIMARY KEY,
    testimony_id INTEGER NOT NULL,
    moderator_id INTEGER,
    action TEXT NOT NULL, -- 'approved', 'rejected'
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (testimony_id) REFERENCES testimonies (id),
    FOREIGN KEY (moderator_id) REFERENCES users (id)
);
```

#### User Status Tracking
- Add `established_user` field to users table
- Define criteria for "established" (e.g., account age > 30 days, min prayers shared)

### File Handling
- Create `media_uploads/testimonies/` directory structure
- Support common audio formats (MP3, WAV, M4A)
- Support common video formats (MP4, MOV, AVI)
- File size limits (audio: 50MB, video: 200MB)
- Automatic file cleanup for rejected testimonies

### Transcription Service
- **Option 1**: Integrate with Anthropic Claude for transcription
- **Option 2**: Use OpenAI Whisper API
- **Option 3**: Google Speech-to-Text API
- Store original media + transcription
- Fallback to manual transcription request

### Routes & Endpoints

#### Main Routes
```python
GET /testimonies                    # Browse testimonies page
POST /testimonies                   # Submit new testimony
GET /testimonies/new               # Create testimony form
GET /testimonies/{id}              # View individual testimony
PUT /testimonies/{id}              # Edit testimony (author only)
DELETE /testimonies/{id}           # Delete testimony (author/admin)
```

#### Admin Routes
```python
GET /admin/testimonies             # Moderation dashboard
POST /admin/testimonies/{id}/approve   # Approve testimony
POST /admin/testimonies/{id}/reject    # Reject testimony
GET /admin/testimonies/pending     # View pending testimonies
```

#### API Endpoints
```python
POST /api/testimonies/upload       # Handle file uploads
GET /api/testimonies/transcribe/{id}   # Check transcription status
```

### Frontend Components

#### Testimony Submission Form
- Rich text editor for testimony content
- Optional date picker for answered date
- File upload with drag-and-drop
- Real-time upload progress
- Preview functionality

#### Testimonies Browse Page
- Grid/list view toggle
- Filter by date range, media type
- Search functionality
- Pagination
- Sort by newest/oldest

#### Individual Testimony View
- Full testimony display
- Audio/video player with transcription
- Basic sharing options
- Report functionality

### Archive System Integration
- Text archive files for testimonies: `text_archives/testimonies/YYYY/MM/testimony_YYYYMMDD_HHMMSS_userid.txt`
- Include transcription in archive files
- Media files referenced in archive but stored separately

## Implementation Phases

### Phase 1: Core Text Testimonies
1. Database schema creation
2. Basic CRUD operations
3. Text-only testimony submission
4. Browse and view pages
5. Basic moderation system

### Phase 2: User Status & Auto-Approval
1. Established user detection logic
2. Auto-approval workflow
3. Admin moderation dashboard
4. Email notifications for moderation

### Phase 3: Media Upload & Transcription
1. File upload handling
2. Transcription service integration
3. Audio/video player components
4. Transcription display and editing

### Phase 4: Enhanced Features
1. Search and filtering
2. Advanced moderation tools
3. Bulk operations for admins
4. Analytics and reporting

## Security Considerations

### File Security
- Virus scanning for uploaded files
- File type validation beyond extension
- Path traversal protection
- Storage outside web root

### Content Security
- Input sanitization for all text fields
- XSS protection in rich text content
- Rate limiting for submissions
- CSRF protection on all forms

### Privacy
- Option to post anonymously
- Data retention policies for rejected content
- User consent for transcription storage

## Integration Points

### Existing System Integration
- Use existing authentication system
- Leverage current admin panel structure
- Integrate with notification system
- Follow established security patterns

### Archive System
- Extend text archive system for testimonies
- Include metadata and transcriptions
- Disaster recovery procedures

## Configuration Options

### Environment Variables
```bash
TESTIMONY_UPLOADS_ENABLED=true
TESTIMONY_MAX_AUDIO_SIZE_MB=50
TESTIMONY_MAX_VIDEO_SIZE_MB=200
TESTIMONY_TRANSCRIPTION_SERVICE=claude  # claude|whisper|google
TESTIMONY_AUTO_APPROVE_ESTABLISHED=true
ESTABLISHED_USER_MIN_DAYS=30
```

### Admin Settings
- Toggle testimony feature on/off
- Adjust file size limits
- Configure moderation requirements
- Set transcription preferences

## Success Metrics
- Number of testimonies submitted
- Engagement with testimony content
- Moderation efficiency (time to review)
- User satisfaction with transcription quality
- Community growth through testimony sharing

## Potential Challenges & Mitigation

### Storage Costs
- **Challenge**: Audio/video files consume significant storage
- **Mitigation**: Implement file retention policies, compress media files

### Transcription Accuracy
- **Challenge**: AI transcription may not be perfect
- **Mitigation**: Allow user editing of transcriptions, manual review option

### Moderation Scalability
- **Challenge**: Manual moderation may not scale with growth
- **Mitigation**: Auto-approval for established users, AI-assisted pre-screening

### Content Quality
- **Challenge**: Ensuring testimonies are appropriate and meaningful
- **Mitigation**: Clear submission guidelines, community reporting, admin tools

## Future Enhancements
- Testimony categories/tags
- Featured testimonies on homepage
- Testimony search with AI summarization
- Integration with prayer request matching
- Multi-language transcription support
- Mobile app optimization for audio/video recording

This implementation preserves ThyWill's core values of community, reverence, and meaningful sharing while adding a powerful new dimension for celebrating answered prayers and encouraging faith.