# PrayerLift - Hackathon Implementation Plan
## "Augmenting prayer through AI and community"

### Project Overview
**PrayerLift** is a spiritual augmentation platform for AugHack (Augmentation Lab hackathon). The project explores how AI can enhance human prayer and community spiritual support, using technology to deepen rather than replace meaningful spiritual connections.

### Hackathon Pitch
*"What if AI could help us pray better together? PrayerLift augments personal prayer with thoughtful AI responses and connects community members through shared spiritual experiences, using voice synthesis and intelligent prayer generation to make spiritual support more accessible and meaningful."*

### Why Spiritual Augmentation?
- **Human-Centered**: Technology serves fundamental spiritual needs
- **Enhancement Not Replacement**: AI augments human prayer practices
- **Community Building**: Uses tech to strengthen bonds during difficult times
- **Accessibility**: Voice features make spiritual content universally accessible

---

## One-Night Prayer Platform MVP

### Tech Stack Recommendation
- **Backend**: FastAPI (Python) - Matches existing codebase knowledge
- **Database**: SQLite - Zero config, perfect for hackathon
- **Frontend**: HTML/CSS + HTMX - Fast development, no build step
- **AI**: Claude API (existing key available)
- **Auth**: Google OAuth + simple session cookies
- **Voice**: ElevenLabs API or Google Cloud TTS

---

## Stage 1: Essential MVP - Core Prayer Platform
**Goal**: Basic prayer submission and viewing

### Features
- Simple HTML form for prayer submission
- Prayer feed showing all requests
- Basic prayer cards with text display
- SQLite database with User and Prayer tables
- Basic FastAPI routes

### Database Schema (Minimal)
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    display_name TEXT UNIQUE,
    created_at TIMESTAMP
);

CREATE TABLE prayers (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    author_id TEXT REFERENCES users(id),
    created_at TIMESTAMP
);
```

### Routes
- `GET /` - Prayer feed
- `POST /prayers` - Submit prayer
- Basic HTML templates

---

## Stage 2: Basic Auth & Community Features
**Goal**: User accounts and prayer interaction

### Features
- User registration/login (simple form-based)
- "I prayed for this" button with counter
- My prayers view
- Basic session management

### Database Additions
```sql
CREATE TABLE prayer_marks (
    user_id TEXT REFERENCES users(id),
    prayer_id TEXT REFERENCES prayers(id),
    created_at TIMESTAMP,
    PRIMARY KEY (user_id, prayer_id)
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    expires_at TIMESTAMP
);
```

### New Routes
- `GET/POST /login` - Authentication
- `POST /mark/{prayer_id}` - Mark prayer as prayed
- `GET /my-prayers` - User's prayers

---

## Stage 3: AI Integration
**Goal**: AI-generated prayer responses

### Features
- Claude API integration for prayer generation
- Generated prayers displayed below original requests
- Simple prompt engineering for faith-appropriate responses
- Error handling if API fails

### Implementation
- Add `generated_prayer` column to prayers table
- Background task or immediate generation on submission
- Display generated content in prayer cards
- Fallback message if generation fails

---

## Stage 4: Google Auth & Text-to-Speech
**Goal**: Enhanced UX with voice and OAuth

### Google Authentication
- Replace form auth with Google OAuth
- Use Google's user info for display names
- Simpler user experience

### Text-to-Speech Integration
**API Recommendation**: ElevenLabs API
- More expressive voices than Google TTS
- Simple REST API
- Good free tier for hackathon
- Example: "Rachel" voice with emotional expressiveness

### Features
- "Listen" button on each prayer card
- Audio playback of both original request and generated prayer
- Voice selection (optional)
- Audio caching to avoid repeated API calls

### Alternative TTS Options
1. **ElevenLabs** (Recommended)
   - Most expressive voices
   - Good API design
   - Free tier: 10,000 characters/month

2. **Google Cloud TTS**
   - Reliable, good quality
   - WaveNet voices
   - More complex setup

3. **OpenAI TTS**
   - Good quality, simple API
   - Requires OpenAI key

---

## Stage 5: Polish & Demo Ready
**Goal**: Hackathon presentation ready

### UI Polish
- Clean, modern CSS (use Tailwind CDN)
- Mobile responsive design
- Loading states for AI generation
- Audio loading indicators

### Demo Features
- Seed data with sample prayers
- Clear navigation
- Error handling with user-friendly messages
- Basic favicon and branding

### Optional Enhancements (Time Permitting)
- Prayer categories with simple tags
- Search functionality
- Export prayers feature
- Simple admin panel

---

## Implementation Order Priority

### Hour 1-2: Core Foundation
1. FastAPI setup with SQLite
2. Basic User/Prayer models
3. Simple HTML templates
4. Prayer submission form
5. Prayer feed display

### Hour 3-4: User System
1. Simple login/register forms
2. Session management
3. Prayer marking system
4. User-specific views

### Hour 5-6: AI Integration
1. Claude API integration
2. Prayer generation
3. Display generated prayers
4. Error handling

### Hour 7-8: Enhanced Auth & Voice
1. Replace with Google OAuth
2. ElevenLabs TTS integration
3. Audio playback controls
4. UI polish

### Final Hour: Demo Prep
1. Seed realistic data
2. Final UI touches
3. Error handling
4. Demo script preparation

---

## File Structure
```
hackathon_thywill/
├── main.py              # FastAPI app
├── models.py            # Database models
├── auth.py              # Authentication logic
├── ai_service.py        # Claude API integration
├── tts_service.py       # Text-to-speech service
├── templates/
│   ├── base.html
│   ├── index.html       # Prayer feed
│   ├── login.html
│   └── my_prayers.html
├── static/
│   ├── style.css
│   └── app.js           # Minimal JavaScript
├── requirements.txt
└── database.db          # SQLite file
```

---

## API Keys Needed
1. **Claude API** - Already available
2. **Google OAuth** - Free, quick setup
3. **ElevenLabs** - Free tier sufficient

## Success Metrics for Demo
- Users can register with Google
- Submit prayer requests
- View all community prayers
- AI generates contextual prayers
- Audio playback works smoothly
- Clean, professional UI
- No crashes during demo