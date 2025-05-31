# Enhanced Faith Specification Feature Plan

## User Story
**As a user, I want to be able to specify my faith with checkboxes and multiple freeform fields.**

## Overview
This plan enhances the current binary religious preference system (Christian/All Faiths) to support a more nuanced and flexible faith specification system that accommodates diverse religious backgrounds, denominations, and spiritual practices.

## Current State Analysis
- Current system: Simple binary choice (Christian vs All Faiths Welcome)
- Current fields: `religious_preference` (enum), `prayer_style` (text)
- Current prayer targeting: `target_audience` (enum), `prayer_context` (text)

## Requirements

### Functional Requirements
1. **Multiple Faith Selection**: Users can select multiple faith traditions/denominations
2. **Freeform Faith Description**: Users can add custom faith descriptions
3. **Detailed Prayer Preferences**: Users can specify prayer styles, languages, traditions
4. **Flexible Prayer Targeting**: Prayer requestors can target specific faith combinations
5. **Inclusive Default Behavior**: Maintains current inclusive defaults
6. **Backward Compatibility**: Existing data and functionality preserved

### Non-Functional Requirements
1. **Privacy**: Faith information remains optional and user-controlled
2. **Performance**: Efficient filtering with complex faith criteria
3. **Accessibility**: Form accessible to users with disabilities
4. **Internationalization**: Support for non-English faith descriptions
5. **Data Integrity**: Validation and sanitization of user input

## Technical Architecture

### Database Schema Changes

#### New Faith Profile Model
```python
class UserFaithProfile(SQLModel, table=True):
    __tablename__ = 'user_faith_profiles'
    
    id: str = Field(default_factory=lambda: secrets.token_hex(16), primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Structured faith selections
    faith_traditions: str | None = Field(default=None, max_length=500)  # JSON array of selected faiths
    denominations: str | None = Field(default=None, max_length=500)     # JSON array of denominations
    
    # Freeform descriptions
    faith_description: str | None = Field(default=None, max_length=1000)  # User's own description
    spiritual_practices: str | None = Field(default=None, max_length=500) # Prayer practices, meditation, etc.
    
    # Prayer preferences
    preferred_prayer_styles: str | None = Field(default=None, max_length=500)  # JSON array
    prayer_languages: str | None = Field(default=None, max_length=200)         # Preferred languages
    sacred_texts: str | None = Field(default=None, max_length=300)             # Bible, Quran, Torah, etc.
    
    # Interaction preferences
    open_to_interfaith: bool = Field(default=True)                    # Willing to pray with other faiths
    comfortable_with_christian_prayer: bool = Field(default=True)     # For backward compatibility
    comfortable_with_secular_prayer: bool = Field(default=True)       # Non-religious prayer support
```

#### Enhanced Prayer Targeting Model
```python
class PrayerTargeting(SQLModel, table=True):
    __tablename__ = 'prayer_targeting'
    
    id: str = Field(default_factory=lambda: secrets.token_hex(16), primary_key=True)
    prayer_id: str = Field(foreign_key="prayer.id")
    
    # Faith targeting criteria
    required_faith_traditions: str | None = Field(default=None, max_length=500)  # JSON array
    preferred_faith_traditions: str | None = Field(default=None, max_length=500) # JSON array
    
    # Prayer style requirements
    required_prayer_styles: str | None = Field(default=None, max_length=500)     # JSON array
    exclude_prayer_styles: str | None = Field(default=None, max_length=500)      # JSON array
    
    # Language preferences
    preferred_languages: str | None = Field(default=None, max_length=200)        # JSON array
    
    # Openness settings
    interfaith_welcome: bool = Field(default=True)           # Open to all faiths
    specific_denominations_only: bool = Field(default=False) # Restrict to specific denominations
    
    # Targeting description
    targeting_description: str | None = Field(default=None, max_length=300) # Human-readable explanation
```

#### Migration Strategy for Existing User Model
```python
# Keep existing fields for backward compatibility
class User(SQLModel, table=True):
    # ... existing fields ...
    
    # Keep for backward compatibility (will be migrated to faith profile)
    religious_preference: str | None = Field(default="unspecified", max_length=50)
    prayer_style: str | None = Field(default=None, max_length=100)
    
    # Helper method to get faith profile
    def get_faith_profile(self, session: Session) -> UserFaithProfile | None:
        stmt = select(UserFaithProfile).where(UserFaithProfile.user_id == self.id)
        return session.exec(stmt).first()
    
    def ensure_faith_profile(self, session: Session) -> UserFaithProfile:
        profile = self.get_faith_profile(session)
        if not profile:
            profile = UserFaithProfile(user_id=self.id)
            session.add(profile)
            session.commit()
        return profile
```

### Faith Taxonomy System

#### Predefined Faith Categories
```python
FAITH_TRADITIONS = {
    "christianity": {
        "label": "Christianity",
        "denominations": [
            "catholic", "orthodox", "protestant", "evangelical", "pentecostal",
            "baptist", "methodist", "presbyterian", "anglican", "lutheran",
            "non_denominational", "other_christian"
        ]
    },
    "islam": {
        "label": "Islam",
        "denominations": [
            "sunni", "shia", "sufi", "other_islam"
        ]
    },
    "judaism": {
        "label": "Judaism",
        "denominations": [
            "orthodox", "conservative", "reform", "reconstructionist", "other_judaism"
        ]
    },
    "hinduism": {
        "label": "Hinduism",
        "denominations": [
            "vaishnavism", "shaivism", "shaktism", "smartism", "other_hinduism"
        ]
    },
    "buddhism": {
        "label": "Buddhism",
        "denominations": [
            "theravada", "mahayana", "vajrayana", "zen", "other_buddhism"
        ]
    },
    "other_faith": {
        "label": "Other Faith Tradition",
        "denominations": []
    },
    "spiritual_not_religious": {
        "label": "Spiritual but not Religious",
        "denominations": []
    },
    "secular": {
        "label": "Secular/Non-Religious",
        "denominations": []
    }
}

PRAYER_STYLES = [
    "in_jesus_name", "trinitarian", "islamic_prayer", "jewish_prayer",
    "meditation", "contemplative", "interfaith", "secular_mindfulness",
    "traditional", "contemporary", "silent", "spoken", "chanted"
]

LANGUAGES = [
    "english", "spanish", "arabic", "hebrew", "latin", "greek",
    "hindi", "sanskrit", "mandarin", "other"
]
```

## User Interface Design

### Enhanced Faith Profile Page
```html
<!-- templates/faith_profile.html -->
<div class="faith-profile-form">
    <h2>Your Faith & Prayer Preferences</h2>
    <p class="help-text">Share as much or as little as you're comfortable with. This helps us connect you with compatible prayer partners.</p>
    
    <!-- Faith Traditions Section -->
    <div class="section faith-traditions">
        <h3>Faith Traditions <span class="optional">(Optional)</span></h3>
        <p class="help-text">Select all that apply to you:</p>
        
        <div class="checkbox-grid">
            {% for tradition_key, tradition in faith_traditions.items() %}
            <div class="tradition-group">
                <label class="tradition-checkbox">
                    <input type="checkbox" name="faith_traditions" value="{{ tradition_key }}"
                           {% if tradition_key in user_selections.faith_traditions %}checked{% endif %}>
                    <span class="tradition-label">{{ tradition.label }}</span>
                </label>
                
                <!-- Denomination sub-checkboxes -->
                <div class="denomination-group" id="denom-{{ tradition_key }}" style="display: none;">
                    {% for denom in tradition.denominations %}
                    <label class="denomination-checkbox">
                        <input type="checkbox" name="denominations" value="{{ tradition_key }}.{{ denom }}"
                               {% if tradition_key + '.' + denom in user_selections.denominations %}checked{% endif %}>
                        <span class="denomination-label">{{ denom|title|replace('_', ' ') }}</span>
                    </label>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- Freeform Faith Description -->
    <div class="section faith-description">
        <h3>Describe Your Faith <span class="optional">(Optional)</span></h3>
        <p class="help-text">In your own words, describe your faith, spirituality, or worldview:</p>
        <textarea name="faith_description" rows="4" maxlength="1000" 
                  placeholder="e.g., I'm a progressive Christian who values social justice... or I practice mindfulness meditation... or I draw from multiple spiritual traditions...">{{ user_profile.faith_description or '' }}</textarea>
        <div class="char-count">{{ (user_profile.faith_description or '')|length }}/1000</div>
    </div>
    
    <!-- Spiritual Practices -->
    <div class="section spiritual-practices">
        <h3>Spiritual Practices <span class="optional">(Optional)</span></h3>
        <p class="help-text">What spiritual practices are meaningful to you?</p>
        <textarea name="spiritual_practices" rows="3" maxlength="500"
                  placeholder="e.g., Daily prayer, meditation, reading scripture, attending services, nature walks, journaling...">{{ user_profile.spiritual_practices or '' }}</textarea>
        <div class="char-count">{{ (user_profile.spiritual_practices or '')|length }}/500</div>
    </div>
    
    <!-- Prayer Preferences -->
    <div class="section prayer-preferences">
        <h3>Prayer Preferences</h3>
        
        <div class="prayer-styles">
            <h4>Prayer Styles You're Comfortable With:</h4>
            <div class="checkbox-grid">
                {% for style in prayer_styles %}
                <label class="style-checkbox">
                    <input type="checkbox" name="preferred_prayer_styles" value="{{ style }}"
                           {% if style in user_selections.preferred_prayer_styles %}checked{% endif %}>
                    <span class="style-label">{{ style|title|replace('_', ' ') }}</span>
                </label>
                {% endfor %}
            </div>
        </div>
        
        <div class="prayer-languages">
            <h4>Preferred Prayer Languages:</h4>
            <div class="checkbox-grid">
                {% for lang in languages %}
                <label class="language-checkbox">
                    <input type="checkbox" name="prayer_languages" value="{{ lang }}"
                           {% if lang in user_selections.prayer_languages %}checked{% endif %}>
                    <span class="language-label">{{ lang|title }}</span>
                </label>
                {% endfor %}
            </div>
            
            <div class="custom-language">
                <label for="custom_language">Other language:</label>
                <input type="text" name="custom_language" maxlength="50" 
                       placeholder="Enter language name">
            </div>
        </div>
        
        <div class="sacred-texts">
            <h4>Sacred Texts or Sources of Wisdom:</h4>
            <input type="text" name="sacred_texts" maxlength="300"
                   value="{{ user_profile.sacred_texts or '' }}"
                   placeholder="e.g., Bible, Quran, Torah, Bhagavad Gita, Buddhist sutras, poetry, philosophy...">
        </div>
    </div>
    
    <!-- Interaction Preferences -->
    <div class="section interaction-preferences">
        <h3>Prayer Community Preferences</h3>
        
        <label class="preference-checkbox">
            <input type="checkbox" name="open_to_interfaith" 
                   {% if user_profile.open_to_interfaith %}checked{% endif %}>
            <span class="preference-label">I'm open to praying with people from different faith traditions</span>
        </label>
        
        <label class="preference-checkbox">
            <input type="checkbox" name="comfortable_with_christian_prayer"
                   {% if user_profile.comfortable_with_christian_prayer %}checked{% endif %}>
            <span class="preference-label">I'm comfortable with Christian prayer styles (including "in Jesus' name")</span>
        </label>
        
        <label class="preference-checkbox">
            <input type="checkbox" name="comfortable_with_secular_prayer"
                   {% if user_profile.comfortable_with_secular_prayer %}checked{% endif %}>
            <span class="preference-label">I'm comfortable with non-religious meditation and mindfulness practices</span>
        </label>
    </div>
    
    <!-- Privacy Notice -->
    <div class="privacy-notice">
        <h4>Privacy Notice</h4>
        <p>Your faith information is private and will only be used to help match you with compatible prayer partners. You can update or remove this information at any time. Other users will only see general compatibility indicators, not your specific faith details.</p>
    </div>
    
    <div class="form-actions">
        <button type="submit" class="btn btn-primary">Save Faith Profile</button>
        <button type="button" class="btn btn-secondary" onclick="resetForm()">Reset</button>
    </div>
</div>

<style>
.faith-profile-form {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
}

.section {
    margin-bottom: 2rem;
    padding: 1.5rem;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #fafafa;
}

.dark .section {
    border-color: #374151;
    background: #1f2937;
}

.checkbox-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 0.5rem;
    margin: 1rem 0;
}

.tradition-group {
    margin-bottom: 1rem;
}

.denomination-group {
    margin-left: 1.5rem;
    margin-top: 0.5rem;
    padding-left: 1rem;
    border-left: 2px solid #d1d5db;
}

.char-count {
    text-align: right;
    font-size: 0.875rem;
    color: #6b7280;
    margin-top: 0.25rem;
}

.optional {
    font-size: 0.875rem;
    color: #6b7280;
    font-weight: normal;
}

.help-text {
    font-size: 0.875rem;
    color: #6b7280;
    margin-bottom: 1rem;
}

.privacy-notice {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    padding: 1rem;
    margin: 1.5rem 0;
}

.dark .privacy-notice {
    background: #1e3a8a;
    border-color: #3b82f6;
}
</style>

<script>
// Show/hide denomination checkboxes based on tradition selection
document.querySelectorAll('input[name="faith_traditions"]').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        const denomGroup = document.getElementById('denom-' + this.value);
        if (denomGroup) {
            denomGroup.style.display = this.checked ? 'block' : 'none';
            
            // Uncheck denomination boxes if tradition is unchecked
            if (!this.checked) {
                denomGroup.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    cb.checked = false;
                });
            }
        }
    });
    
    // Initial state
    if (checkbox.checked) {
        const denomGroup = document.getElementById('denom-' + checkbox.value);
        if (denomGroup) {
            denomGroup.style.display = 'block';
        }
    }
});

// Character counting for textareas
document.querySelectorAll('textarea[maxlength]').forEach(textarea => {
    const charCount = textarea.parentNode.querySelector('.char-count');
    if (charCount) {
        textarea.addEventListener('input', function() {
            charCount.textContent = this.value.length + '/' + this.maxLength;
        });
    }
});

function resetForm() {
    if (confirm('Are you sure you want to reset all fields? This will clear any unsaved changes.')) {
        document.querySelector('.faith-profile-form').reset();
        // Hide all denomination groups
        document.querySelectorAll('.denomination-group').forEach(group => {
            group.style.display = 'none';
        });
    }
}
</script>
```

### Enhanced Prayer Targeting Interface
```html
<!-- templates/components/enhanced_prayer_form.html -->
<div class="prayer-targeting-section">
    <h3>Who Would You Like to Pray for You?</h3>
    <p class="help-text">Choose who you'd like to see and respond to your prayer request:</p>
    
    <div class="targeting-options">
        <label class="targeting-option">
            <input type="radio" name="targeting_type" value="everyone" checked>
            <span class="option-title">Everyone Welcome</span>
            <span class="option-description">All community members can see and pray for this request</span>
        </label>
        
        <label class="targeting-option">
            <input type="radio" name="targeting_type" value="specific_faiths">
            <span class="option-title">Specific Faith Traditions</span>
            <span class="option-description">Only people from certain faith backgrounds</span>
        </label>
        
        <label class="targeting-option">
            <input type="radio" name="targeting_type" value="prayer_style">
            <span class="option-title">Specific Prayer Style</span>
            <span class="option-description">People comfortable with certain prayer approaches</span>
        </label>
        
        <label class="targeting-option">
            <input type="radio" name="targeting_type" value="custom">
            <span class="option-title">Custom Criteria</span>
            <span class="option-description">Define your own specific requirements</span>
        </label>
    </div>
    
    <!-- Specific Faiths Selection -->
    <div class="targeting-details" id="specific-faiths-details" style="display: none;">
        <h4>Select Faith Traditions:</h4>
        <div class="faith-selection-grid">
            {% for tradition_key, tradition in faith_traditions.items() %}
            <label class="faith-option">
                <input type="checkbox" name="required_faith_traditions" value="{{ tradition_key }}">
                <span class="faith-label">{{ tradition.label }}</span>
            </label>
            {% endfor %}
        </div>
        
        <label class="preference-option">
            <input type="checkbox" name="interfaith_welcome">
            <span class="preference-label">Also welcome people from other faith traditions</span>
        </label>
    </div>
    
    <!-- Prayer Style Selection -->
    <div class="targeting-details" id="prayer-style-details" style="display: none;">
        <h4>Required Prayer Styles:</h4>
        <div class="style-selection-grid">
            {% for style in prayer_styles %}
            <label class="style-option">
                <input type="checkbox" name="required_prayer_styles" value="{{ style }}">
                <span class="style-label">{{ style|title|replace('_', ' ') }}</span>
            </label>
            {% endfor %}
        </div>
        
        <h4>Exclude Prayer Styles:</h4>
        <div class="style-selection-grid">
            {% for style in prayer_styles %}
            <label class="style-option">
                <input type="checkbox" name="exclude_prayer_styles" value="{{ style }}">
                <span class="style-label">{{ style|title|replace('_', ' ') }}</span>
            </label>
            {% endfor %}
        </div>
    </div>
    
    <!-- Custom Criteria -->
    <div class="targeting-details" id="custom-details" style="display: none;">
        <div class="custom-criteria">
            <label for="targeting_description">Describe who you'd like to pray for you:</label>
            <textarea name="targeting_description" rows="3" maxlength="300"
                      placeholder="e.g., I'd like prayers from people who understand addiction recovery... or from parents who have experienced loss... or from people who share my cultural background..."></textarea>
        </div>
        
        <div class="language-preferences">
            <h4>Preferred Languages:</h4>
            <div class="language-grid">
                {% for lang in languages %}
                <label class="language-option">
                    <input type="checkbox" name="preferred_languages" value="{{ lang }}">
                    <span class="language-label">{{ lang|title }}</span>
                </label>
                {% endfor %}
            </div>
        </div>
    </div>
    
    <!-- Preview Section -->
    <div class="targeting-preview">
        <h4>Who Will See This Prayer:</h4>
        <div id="targeting-preview-text" class="preview-text">
            All community members will be able to see and pray for this request.
        </div>
    </div>
</div>

<script>
// Show/hide targeting details based on radio selection
document.querySelectorAll('input[name="targeting_type"]').forEach(radio => {
    radio.addEventListener('change', function() {
        // Hide all detail sections
        document.querySelectorAll('.targeting-details').forEach(section => {
            section.style.display = 'none';
        });
        
        // Show relevant section
        const targetSection = document.getElementById(this.value + '-details');
        if (targetSection) {
            targetSection.style.display = 'block';
        }
        
        updateTargetingPreview();
    });
});

// Update preview text based on selections
function updateTargetingPreview() {
    const targetingType = document.querySelector('input[name="targeting_type"]:checked').value;
    const previewElement = document.getElementById('targeting-preview-text');
    
    let previewText = '';
    
    switch (targetingType) {
        case 'everyone':
            previewText = 'All community members will be able to see and pray for this request.';
            break;
        case 'specific_faiths':
            const selectedFaiths = Array.from(document.querySelectorAll('input[name="required_faith_traditions"]:checked'))
                .map(cb => cb.nextElementSibling.textContent);
            if (selectedFaiths.length > 0) {
                previewText = `People from these faith traditions will see this: ${selectedFaiths.join(', ')}.`;
                if (document.querySelector('input[name="interfaith_welcome"]').checked) {
                    previewText += ' Others may also see it if they\'re open to interfaith prayer.';
                }
            } else {
                previewText = 'Please select at least one faith tradition.';
            }
            break;
        case 'prayer_style':
            const requiredStyles = Array.from(document.querySelectorAll('input[name="required_prayer_styles"]:checked'))
                .map(cb => cb.nextElementSibling.textContent);
            const excludedStyles = Array.from(document.querySelectorAll('input[name="exclude_prayer_styles"]:checked'))
                .map(cb => cb.nextElementSibling.textContent);
            
            if (requiredStyles.length > 0 || excludedStyles.length > 0) {
                previewText = 'People comfortable with';
                if (requiredStyles.length > 0) {
                    previewText += ` ${requiredStyles.join(', ')}`;
                }
                if (excludedStyles.length > 0) {
                    previewText += ` (but not ${excludedStyles.join(', ')})`;
                }
                previewText += ' will see this prayer.';
            } else {
                previewText = 'Please specify prayer style requirements.';
            }
            break;
        case 'custom':
            const description = document.querySelector('textarea[name="targeting_description"]').value;
            if (description.trim()) {
                previewText = `Custom criteria: ${description.trim()}`;
            } else {
                previewText = 'Please describe your targeting criteria.';
            }
            break;
    }
    
    previewElement.textContent = previewText;
}

// Add event listeners for real-time preview updates
document.addEventListener('change', updateTargetingPreview);
document.addEventListener('input', updateTargetingPreview);
</script>
```

## Backend Implementation

### Faith Profile Management
```python
# app.py - Faith profile endpoints

@app.get("/profile/faith", response_class=HTMLResponse)
async def faith_profile_page(request: Request, user_session: tuple = Depends(current_user)):
    """Display faith profile editing page"""
    user, session = user_session
    
    with Session(engine) as db:
        faith_profile = user.get_faith_profile(db)
        
        # Parse JSON fields for template
        user_selections = {
            'faith_traditions': json.loads(faith_profile.faith_traditions) if faith_profile and faith_profile.faith_traditions else [],
            'denominations': json.loads(faith_profile.denominations) if faith_profile and faith_profile.denominations else [],
            'preferred_prayer_styles': json.loads(faith_profile.preferred_prayer_styles) if faith_profile and faith_profile.preferred_prayer_styles else [],
            'prayer_languages': json.loads(faith_profile.prayer_languages) if faith_profile and faith_profile.prayer_languages else []
        }
        
        return templates.TemplateResponse("faith_profile.html", {
            "request": request,
            "user": user,
            "session": session,
            "user_profile": faith_profile,
            "user_selections": user_selections,
            "faith_traditions": FAITH_TRADITIONS,
            "prayer_styles": PRAYER_STYLES,
            "languages": LANGUAGES
        })

@app.post("/profile/faith")
async def update_faith_profile(
    request: Request,
    faith_traditions: list[str] = Form([]),
    denominations: list[str] = Form([]),
    faith_description: str = Form(""),
    spiritual_practices: str = Form(""),
    preferred_prayer_styles: list[str] = Form([]),
    prayer_languages: list[str] = Form([]),
    custom_language: str = Form(""),
    sacred_texts: str = Form(""),
    open_to_interfaith: bool = Form(False),
    comfortable_with_christian_prayer: bool = Form(False),
    comfortable_with_secular_prayer: bool = Form(False),
    user_session: tuple = Depends(current_user)
):
    """Update user's faith profile"""
    user, session = user_session
    
    # Validate and sanitize inputs
    faith_traditions = [ft for ft in faith_traditions if ft in FAITH_TRADITIONS]
    denominations = [d for d in denominations if validate_denomination(d)]
    preferred_prayer_styles = [ps for ps in preferred_prayer_styles if ps in PRAYER_STYLES]
    prayer_languages = [pl for pl in prayer_languages if pl in LANGUAGES or pl == 'other']
    
    # Add custom language if provided
    if custom_language.strip():
        prayer_languages.append(custom_language.strip()[:50])
    
    # Sanitize text fields
    faith_description = sanitize_text(faith_description, max_length=1000)
    spiritual_practices = sanitize_text(spiritual_practices, max_length=500)
    sacred_texts = sanitize_text(sacred_texts, max_length=300)
    
    with Session(engine) as db:
        faith_profile = user.ensure_faith_profile(db)
        
        # Update faith profile
        faith_profile.faith_traditions = json.dumps(faith_traditions) if faith_traditions else None
        faith_profile.denominations = json.dumps(denominations) if denominations else None
        faith_profile.faith_description = faith_description if faith_description.strip() else None
        faith_profile.spiritual_practices = spiritual_practices if spiritual_practices.strip() else None
        faith_profile.preferred_prayer_styles = json.dumps(preferred_prayer_styles) if preferred_prayer_styles else None
        faith_profile.prayer_languages = json.dumps(prayer_languages) if prayer_languages else None
        faith_profile.sacred_texts = sacred_texts if sacred_texts.strip() else None
        faith_profile.open_to_interfaith = open_to_interfaith
        faith_profile.comfortable_with_christian_prayer = comfortable_with_christian_prayer
        faith_profile.comfortable_with_secular_prayer = comfortable_with_secular_prayer
        faith_profile.updated_at = datetime.utcnow()
        
        db.add(faith_profile)
        db.commit()
        
        # Migrate legacy fields for backward compatibility
        migrate_legacy_preferences(user, faith_profile, db)
    
    return RedirectResponse("/profile", status_code=303)

def migrate_legacy_preferences(user: User, faith_profile: UserFaithProfile, db: Session):
    """Migrate old religious_preference field to new faith profile"""
    if user.religious_preference == "christian" and not faith_profile.faith_traditions:
        faith_profile.faith_traditions = json.dumps(["christianity"])
        faith_profile.comfortable_with_christian_prayer = True
        if user.prayer_style == "in_jesus_name":
            styles = json.loads(faith_profile.preferred_prayer_styles or "[]")
            if "in_jesus_name" not in styles:
                styles.append("in_jesus_name")
                faith_profile.preferred_prayer_styles = json.dumps(styles)
    
    # Mark as migrated
    user.religious_preference = "migrated"
    db.add(user)
```

### Enhanced Prayer Filtering
```python
def get_compatible_prayers_for_user(user: User, db: Session, include_archived: bool = False) -> list[Prayer]:
    """Get prayers compatible with user's faith profile"""
    
    faith_profile = user.get_faith_profile(db)
    
    # Base query
    base_query = select(Prayer).where(Prayer.flagged == False)
    
    if not include_archived:
        base_query = base_query.where(
            ~Prayer.id.in_(
                select(PrayerAttribute.prayer_id).where(
                    PrayerAttribute.attribute_name == 'archived'
                )
            )
        )
    
    # Get all prayers with their targeting criteria
    prayers_stmt = (
        base_query
        .outerjoin(PrayerTargeting, Prayer.id == PrayerTargeting.prayer_id)
        .order_by(Prayer.created_at.desc())
    )
    
    results = db.exec(prayers_stmt).all()
    compatible_prayers = []
    
    for prayer_result in results:
        if isinstance(prayer_result, tuple):
            prayer, targeting = prayer_result
        else:
            prayer = prayer_result
            targeting = None
        
        if is_prayer_compatible_with_user(prayer, targeting, faith_profile):
            compatible_prayers.append(prayer)
    
    return compatible_prayers

def is_prayer_compatible_with_user(prayer: Prayer, targeting: PrayerTargeting, faith_profile: UserFaithProfile) -> bool:
    """Check if a prayer is compatible with user's faith profile"""
    
    # If no targeting specified, prayer is open to everyone
    if not targeting:
        return True
    
    # If prayer welcomes interfaith and user is open to interfaith
    if targeting.interfaith_welcome and (not faith_profile or faith_profile.open_to_interfaith):
        return True
    
    # Check faith tradition compatibility
    if targeting.required_faith_traditions:
        required_faiths = json.loads(targeting.required_faith_traditions)
        if faith_profile and faith_profile.faith_traditions:
            user_faiths = json.loads(faith_profile.faith_traditions)
            if not any(faith in required_faiths for faith in user_faiths):
                return False
        else:
            # User has no specified faith, check if prayer accepts unspecified
            if 'unspecified' not in required_faiths and not targeting.interfaith_welcome:
                return False
    
    # Check prayer style compatibility
    if targeting.required_prayer_styles:
        required_styles = json.loads(targeting.required_prayer_styles)
        if faith_profile and faith_profile.preferred_prayer_styles:
            user_styles = json.loads(faith_profile.preferred_prayer_styles)
            if not any(style in required_styles for style in user_styles):
                return False
        else:
            # User has no style preferences - check if they're comfortable with required styles
            if not faith_profile:
                return True  # Default to compatible
            
            # Check specific comfort levels
            if 'in_jesus_name' in required_styles and not faith_profile.comfortable_with_christian_prayer:
                return False
            if 'secular_mindfulness' in required_styles and not faith_profile.comfortable_with_secular_prayer:
                return False
    
    # Check excluded prayer styles
    if targeting.exclude_prayer_styles:
        excluded_styles = json.loads(targeting.exclude_prayer_styles)
        if faith_profile and faith_profile.preferred_prayer_styles:
            user_styles = json.loads(faith_profile.preferred_prayer_styles)
            if any(style in excluded_styles for style in user_styles):
                return False
    
    return True

def find_compatible_prayer_partners(prayer: Prayer, targeting: PrayerTargeting, db: Session, exclude_user_ids: list[str] = None) -> list[User]:
    """Find users compatible with prayer's targeting criteria"""
    
    base_query = select(User)
    
    # Exclude users who already have this prayer
    assigned_user_ids = db.exec(
        select(PrayerMark.user_id).where(PrayerMark.prayer_id == prayer.id)
    ).all()
    
    if exclude_user_ids:
        assigned_user_ids.extend(exclude_user_ids)
    
    if assigned_user_ids:
        base_query = base_query.where(~User.id.in_(assigned_user_ids))
    
    # Exclude prayer author
    base_query = base_query.where(User.id != prayer.author_id)
    
    # Get all users with their faith profiles
    users_stmt = (
        base_query
        .outerjoin(UserFaithProfile, User.id == UserFaithProfile.user_id)
    )
    
    results = db.exec(users_stmt).all()
    compatible_users = []
    
    for user_result in results:
        if isinstance(user_result, tuple):
            user, faith_profile = user_result
        else:
            user = user_result
            faith_profile = user.get_faith_profile(db)
        
        if is_prayer_compatible_with_user(prayer, targeting, faith_profile):
            compatible_users.append(user)
    
    return compatible_users
```

### Validation and Sanitization
```python
def validate_denomination(denomination: str) -> bool:
    """Validate denomination format: tradition.denomination"""
    if '.' not in denomination:
        return False
    
    tradition, denom = denomination.split('.', 1)
    return tradition in FAITH_TRADITIONS and denom in FAITH_TRADITIONS[tradition].get('denominations', [])

def sanitize_text(text: str, max_length: int) -> str:
    """Sanitize user text input"""
    if not text:
        return ""
    
    # Remove harmful content
    import re
    text = re.sub(r'<[^>]*>', '', text)  # Remove HTML tags
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)  # Remove javascript
    text = text.strip()
    
    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text

def validate_faith_selections(faith_traditions: list[str], denominations: list[str]) -> tuple[list[str], list[str]]:
    """Validate and clean faith selections"""
    valid_traditions = [ft for ft in faith_traditions if ft in FAITH_TRADITIONS]
    valid_denominations = []
    
    for denom in denominations:
        if validate_denomination(denom):
            tradition = denom.split('.', 1)[0]
            if tradition in valid_traditions:
                valid_denominations.append(denom)
    
    return valid_traditions, valid_denominations
```

## Migration Strategy

### Data Migration Plan
```python
# migrate_to_enhanced_faith_system.py

def migrate_existing_faith_data():
    """Migrate existing religious preference data to new faith profile system"""
    
    with Session(engine) as db:
        users = db.exec(select(User).where(User.religious_preference != "migrated")).all()
        
        for user in users:
            print(f"Migrating user {user.id}: {user.religious_preference}")
            
            # Create faith profile
            faith_profile = UserFaithProfile(user_id=user.id)
            
            # Migrate based on existing preference
            if user.religious_preference == "christian":
                faith_profile.faith_traditions = json.dumps(["christianity"])
                faith_profile.comfortable_with_christian_prayer = True
                faith_profile.open_to_interfaith = True
                
                if user.prayer_style == "in_jesus_name":
                    faith_profile.preferred_prayer_styles = json.dumps(["in_jesus_name", "trinitarian"])
                elif user.prayer_style == "interfaith":
                    faith_profile.preferred_prayer_styles = json.dumps(["interfaith", "contemplative"])
                    
            elif user.religious_preference == "unspecified":
                faith_profile.open_to_interfaith = True
                faith_profile.comfortable_with_christian_prayer = True
                faith_profile.comfortable_with_secular_prayer = True
                
            # Set defaults
            if not faith_profile.open_to_interfaith:
                faith_profile.open_to_interfaith = True
                
            db.add(faith_profile)
            
            # Mark as migrated
            user.religious_preference = "migrated"
            db.add(user)
        
        db.commit()
        print(f"Migrated {len(users)} users to enhanced faith system")

def migrate_prayer_targeting():
    """Migrate existing prayer target_audience to new targeting system"""
    
    with Session(engine) as db:
        prayers = db.exec(
            select(Prayer).where(Prayer.target_audience.in_(["christians_only", "non_christians_only"]))
        ).all()
        
        for prayer in prayers:
            targeting = PrayerTargeting(prayer_id=prayer.id)
            
            if prayer.target_audience == "christians_only":
                targeting.required_faith_traditions = json.dumps(["christianity"])
                targeting.interfaith_welcome = False
                targeting.targeting_description = "This prayer is specifically for Christian community members"
                
            elif prayer.target_audience == "non_christians_only":
                targeting.required_faith_traditions = json.dumps([
                    "islam", "judaism", "hinduism", "buddhism", "other_faith", 
                    "spiritual_not_religious", "secular"
                ])
                targeting.interfaith_welcome = False
                targeting.targeting_description = "This prayer is for non-Christian community members"
            
            db.add(targeting)
            
            # Update prayer to use new system
            prayer.target_audience = "targeted"
            db.add(prayer)
        
        db.commit()
        print(f"Migrated {len(prayers)} prayers to enhanced targeting system")
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_enhanced_faith_system.py

class TestEnhancedFaithSystem:
    
    def test_faith_profile_creation(self, test_session):
        """Test creating a comprehensive faith profile"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        faith_profile = UserFaithProfile(
            user_id=user.id,
            faith_traditions=json.dumps(["christianity", "other_faith"]),
            denominations=json.dumps(["christianity.progressive", "other_faith"]),
            faith_description="I draw from Christian tradition and indigenous spirituality",
            spiritual_practices="Daily prayer, meditation, nature connection",
            preferred_prayer_styles=json.dumps(["contemplative", "interfaith"]),
            prayer_languages=json.dumps(["english", "spanish"]),
            sacred_texts="Bible, poetry, nature",
            open_to_interfaith=True,
            comfortable_with_christian_prayer=True,
            comfortable_with_secular_prayer=True
        )
        
        test_session.add(faith_profile)
        test_session.commit()
        
        # Verify creation
        retrieved_profile = test_session.get(UserFaithProfile, faith_profile.id)
        assert retrieved_profile.user_id == user.id
        assert json.loads(retrieved_profile.faith_traditions) == ["christianity", "other_faith"]
        assert retrieved_profile.open_to_interfaith == True
    
    def test_complex_prayer_compatibility(self, test_session):
        """Test prayer compatibility with complex targeting"""
        # Create users with different faith profiles
        christian_user = create_user_with_faith_profile(
            test_session,
            faith_traditions=["christianity"],
            denominations=["christianity.progressive"],
            prayer_styles=["contemplative", "in_jesus_name"]
        )
        
        muslim_user = create_user_with_faith_profile(
            test_session,
            faith_traditions=["islam"],
            prayer_styles=["islamic_prayer"],
            comfortable_with_christian_prayer=False
        )
        
        interfaith_user = create_user_with_faith_profile(
            test_session,
            faith_traditions=["christianity", "buddhism"],
            prayer_styles=["interfaith", "meditation"],
            open_to_interfaith=True
        )
        
        # Create prayer with specific targeting
        prayer = PrayerFactory.create()
        targeting = PrayerTargeting(
            prayer_id=prayer.id,
            required_faith_traditions=json.dumps(["christianity"]),
            required_prayer_styles=json.dumps(["contemplative"]),
            interfaith_welcome=True
        )
        
        test_session.add_all([prayer, targeting])
        test_session.commit()
        
        # Test compatibility
        assert is_prayer_compatible_with_user(prayer, targeting, christian_user.get_faith_profile(test_session))
        assert not is_prayer_compatible_with_user(prayer, targeting, muslim_user.get_faith_profile(test_session))
        assert is_prayer_compatible_with_user(prayer, targeting, interfaith_user.get_faith_profile(test_session))
    
    def test_backward_compatibility(self, test_session):
        """Test that old system still works during migration"""
        # Create old-style user
        old_user = User(
            display_name="Old User",
            religious_preference="christian",
            prayer_style="in_jesus_name"
        )
        test_session.add(old_user)
        test_session.commit()
        
        # Create old-style prayer
        old_prayer = Prayer(
            author_id=old_user.id,
            text="Old prayer",
            target_audience="christians_only"
        )
        test_session.add(old_prayer)
        test_session.commit()
        
        # Test that filtering still works
        prayers = get_filtered_prayers_for_user(old_user, test_session)
        assert old_prayer in prayers
```

### Integration Tests
```python
# tests/integration/test_faith_profile_workflows.py

class TestFaithProfileWorkflows:
    
    def test_complete_faith_profile_creation_workflow(self, client, auth_headers):
        """Test full workflow of creating and updating faith profile"""
        
        # Get faith profile page
        response = client.get("/profile/faith", headers=auth_headers)
        assert response.status_code == 200
        assert "Faith & Prayer Preferences" in response.text
        
        # Submit faith profile
        form_data = {
            "faith_traditions": ["christianity", "other_faith"],
            "denominations": ["christianity.progressive"],
            "faith_description": "Progressive Christian with interfaith interests",
            "spiritual_practices": "Prayer, meditation, service",
            "preferred_prayer_styles": ["contemplative", "interfaith"],
            "prayer_languages": ["english"],
            "sacred_texts": "Bible, spiritual poetry",
            "open_to_interfaith": True,
            "comfortable_with_christian_prayer": True,
            "comfortable_with_secular_prayer": True
        }
        
        response = client.post("/profile/faith", data=form_data, headers=auth_headers)
        assert response.status_code == 303  # Redirect
        
        # Verify profile was created
        # ... additional verification steps
    
    def test_prayer_targeting_workflow(self, client, auth_headers):
        """Test creating prayer with complex targeting"""
        
        # Submit prayer with targeting
        form_data = {
            "text": "Please pray for my job search",
            "targeting_type": "specific_faiths",
            "required_faith_traditions": ["christianity", "judaism"],
            "interfaith_welcome": True,
            "targeting_description": "Looking for prayers from people of Abrahamic faiths"
        }
        
        response = client.post("/prayers", data=form_data, headers=auth_headers)
        assert response.status_code == 303
        
        # Verify targeting was applied
        # ... additional verification steps
```

## Implementation Timeline

### Phase 1: Database & Core Models (Week 1)
- [ ] Create `UserFaithProfile` and `PrayerTargeting` models
- [ ] Implement faith taxonomy constants
- [ ] Create database migration scripts
- [ ] Add helper methods to User model
- [ ] Write unit tests for new models

### Phase 2: Backend Logic (Week 2)
- [ ] Implement faith profile management endpoints
- [ ] Create enhanced prayer filtering logic
- [ ] Add prayer compatibility checking
- [ ] Implement validation and sanitization
- [ ] Write unit tests for filtering logic

### Phase 3: Frontend Interface (Week 3)
- [ ] Create enhanced faith profile page
- [ ] Build complex prayer targeting interface
- [ ] Add JavaScript for dynamic form behavior
- [ ] Implement responsive design
- [ ] Add accessibility features

### Phase 4: Integration & Migration (Week 4)
- [ ] Write data migration scripts
- [ ] Implement backward compatibility layer
- [ ] Create integration tests
- [ ] Test migration process
- [ ] Performance optimization

### Phase 5: Testing & Deployment (Week 5)
- [ ] Comprehensive testing across all workflows
- [ ] User acceptance testing
- [ ] Security review
- [ ] Performance testing
- [ ] Documentation completion

## Success Metrics

### User Adoption
- % of users who complete enhanced faith profiles
- % of users who use targeting features
- User retention after feature launch

### Prayer Matching Quality
- Reduction in prayer assignment mismatches
- Increase in prayer response rates
- User satisfaction with prayer partner compatibility

### Community Engagement
- Diversity of faith representations in community
- Cross-faith interaction rates
- User feedback on inclusivity

## Risk Mitigation

### Technical Risks
- **Complex Database Migration**: Extensive testing in staging environment
- **Performance Impact**: Query optimization and caching strategies
- **Data Validation**: Comprehensive input sanitization and validation

### User Experience Risks
- **Feature Complexity**: Progressive disclosure and helpful defaults
- **Migration Confusion**: Clear communication and gradual rollout
- **Privacy Concerns**: Transparent privacy policies and user control

### Community Risks
- **Faith Misrepresentation**: Community moderation and reporting tools
- **Exclusivity**: Emphasis on inclusivity and interfaith welcome defaults
- **Cultural Sensitivity**: Diverse beta testing and cultural review

## Conclusion

This enhanced faith specification system will provide users with much greater flexibility and control over their faith expression and prayer preferences, while maintaining the inclusive spirit of the prayer community. The implementation plan ensures backward compatibility, thorough testing, and a smooth migration path from the current system.