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

#### Migration Strategy
```python
def migrate_existing_users():
    """Migrate existing religious_preference to new boolean fields"""
    with Session(engine) as db:
        users = db.exec(select(User).where(User.religious_preference == "christian")).all()
        
        for user in users:
            user.is_christian = True
            # Check if user has Catholic-related prayer style or context
            if user.prayer_style and "catholic" in user.prayer_style.lower():
                user.is_catholic = True
            db.add(user)
        
        db.commit()
```

## User Interface Design

### Simple Faith Profile Section
Add to existing preferences page:
```html
<!-- Add to templates/preferences.html -->
<div class="section faith-preferences">
    <h3>Faith Background <span class="optional">(Optional)</span></h3>
    <p class="help-text">This helps us connect you with compatible prayer partners.</p>
    
    <div class="faith-checkboxes">
        <label class="faith-checkbox">
            <input type="checkbox" name="is_christian" {% if user.is_christian %}checked{% endif %}>
            <span class="faith-label">I am Christian</span>
        </label>
        
        <div class="catholic-option" id="catholic-option" style="{% if not user.is_christian %}display: none;{% endif %}">
            <label class="denomination-checkbox">
                <input type="checkbox" name="is_catholic" {% if user.is_catholic %}checked{% endif %}>
                <span class="denomination-label">I am Catholic</span>
            </label>
        </div>
    </div>
    
    <!-- Keep existing prayer style field -->
    <div class="prayer-style-field">
        <label for="prayer_style">Prayer Style Preference:</label>
        <input type="text" name="prayer_style" value="{{ user.prayer_style or '' }}" 
               placeholder="e.g., traditional, contemporary, contemplative">
    </div>
</div>

<script>
// Show/hide Catholic option based on Christian selection
document.querySelector('input[name="is_christian"]').addEventListener('change', function() {
    const catholicOption = document.getElementById('catholic-option');
    const catholicCheckbox = document.querySelector('input[name="is_catholic"]');
    
    if (this.checked) {
        catholicOption.style.display = 'block';
    } else {
        catholicOption.style.display = 'none';
        catholicCheckbox.checked = false;
    }
});
</script>
```

### Simple Prayer Targeting Options
Add to existing prayer form:
```html
<!-- Add to templates/components/prayer_form.html -->
<div class="prayer-targeting-section">
    <h4>Who can pray for this request? <span class="optional">(Optional)</span></h4>
    
    <div class="targeting-options">
        <label class="targeting-option">
            <input type="radio" name="target_audience" value="everyone" 
                   {% if not prayer or prayer.target_audience == 'everyone' %}checked{% endif %}>
            <span class="option-title">Everyone Welcome</span>
        </label>
        
        <label class="targeting-option">
            <input type="radio" name="target_audience" value="christians_only"
                   {% if prayer and prayer.target_audience == 'christians_only' %}checked{% endif %}>
            <span class="option-title">Christians Only</span>
        </label>
    </div>
    
    <div class="catholic-preference" style="margin-top: 1rem;">
        <label class="preference-checkbox">
            <input type="checkbox" name="catholics_preferred" 
                   {% if prayer and prayer.catholics_preferred %}checked{% endif %}>
            <span class="preference-label">Catholics preferred (but welcome all Christians)</span>
        </label>
    </div>
</div>
```

## Backend Implementation

### Simple Faith Profile Update
Update existing preferences endpoint:
```python
# app.py - Update existing preferences endpoint

@app.post("/preferences")
async def update_preferences(
    request: Request,
    # ... existing parameters ...
    is_christian: bool = Form(False),
    is_catholic: bool = Form(False),
    user_session: tuple = Depends(current_user)
):
    """Update user preferences including faith"""
    user, session = user_session
    
    with Session(engine) as db:
        # Update faith fields
        user.is_christian = is_christian
        user.is_catholic = is_catholic and is_christian  # Catholic only if Christian
        
        # ... existing preference updates ...
        
        db.add(user)
        db.commit()
    
    return RedirectResponse("/preferences", status_code=303)
```

### Simple Prayer Filtering
Update existing filtering logic:
```python
def get_filtered_prayers_for_user(user: User, db: Session, include_archived: bool = False) -> list[Prayer]:
    """Get prayers compatible with user's faith preferences"""
    
    # Base query (existing logic)
    base_query = select(Prayer).where(Prayer.flagged == False)
    
    if not include_archived:
        base_query = base_query.where(
            ~Prayer.id.in_(
                select(PrayerAttribute.prayer_id).where(
                    PrayerAttribute.attribute_name == 'archived'
                )
            )
        )
    
    prayers = db.exec(base_query.order_by(Prayer.created_at.desc())).all()
    
    # Filter based on simple targeting
    compatible_prayers = []
    for prayer in prayers:
        if is_prayer_compatible_with_user(prayer, user):
            compatible_prayers.append(prayer)
    
    return compatible_prayers

def is_prayer_compatible_with_user(prayer: Prayer, user: User) -> bool:
    """Check if prayer is compatible with user's faith preferences"""
    
    # Everyone welcome prayers are always compatible
    if prayer.target_audience == "everyone":
        return True
    
    # Christians only prayers
    if prayer.target_audience == "christians_only":
        # Show to Christians or users who haven't specified (backward compatibility)
        if user.is_christian or user.religious_preference == "christian":
            return True
        # Also show to unspecified users for backward compatibility
        if user.religious_preference == "unspecified":
            return True
        return False
    
    return True

def find_compatible_prayer_partners(prayer: Prayer, db: Session, exclude_user_ids: list[str] = None) -> list[User]:
    """Find users compatible with prayer's targeting"""
    
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
    
    users = db.exec(base_query).all()
    compatible_users = []
    
    for user in users:
        if is_prayer_compatible_with_user(prayer, user):
            # Prioritize Catholics if prayer has catholics_preferred
            if prayer.catholics_preferred and user.is_catholic:
                compatible_users.insert(0, user)  # Add to front
            else:
                compatible_users.append(user)
    
    return compatible_users
```

### Simple Validation
```python
def validate_faith_preferences(is_christian: bool, is_catholic: bool) -> tuple[bool, bool]:
    """Validate faith preferences - Catholic only if Christian"""
    return is_christian, is_catholic and is_christian
```

## Migration Strategy

### Simple Data Migration
```python
# migrate_to_simple_faith_system.py

def migrate_existing_users():
    """Migrate existing religious_preference to new boolean fields"""
    with Session(engine) as db:
        users = db.exec(select(User)).all()
        
        for user in users:
            if user.religious_preference == "christian":
                user.is_christian = True
                # Check if user has Catholic-related prayer style
                if user.prayer_style and "catholic" in user.prayer_style.lower():
                    user.is_catholic = True
            
            db.add(user)
        
        db.commit()
        print(f"Migrated {len(users)} users to simple faith system")
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_simple_faith_system.py

class TestSimpleFaithSystem:
    
    def test_faith_preferences_validation(self):
        """Test faith preference validation"""
        # Catholic only if Christian
        is_christian, is_catholic = validate_faith_preferences(True, True)
        assert is_christian == True
        assert is_catholic == True
        
        # Catholic cannot be true if not Christian
        is_christian, is_catholic = validate_faith_preferences(False, True)
        assert is_christian == False
        assert is_catholic == False
    
    def test_prayer_compatibility(self, test_session):
        """Test prayer compatibility with simple targeting"""
        # Create users
        christian_user = UserFactory.create(is_christian=True, is_catholic=False)
        catholic_user = UserFactory.create(is_christian=True, is_catholic=True)
        non_christian_user = UserFactory.create(is_christian=False, is_catholic=False)
        
        # Create prayers
        everyone_prayer = PrayerFactory.create(target_audience="everyone")
        christian_prayer = PrayerFactory.create(target_audience="christians_only")
        
        # Test compatibility
        assert is_prayer_compatible_with_user(everyone_prayer, christian_user)
        assert is_prayer_compatible_with_user(everyone_prayer, non_christian_user)
        
        assert is_prayer_compatible_with_user(christian_prayer, christian_user)
        assert is_prayer_compatible_with_user(christian_prayer, catholic_user)
        assert not is_prayer_compatible_with_user(christian_prayer, non_christian_user)
    
    def test_catholic_prioritization(self, test_session):
        """Test that Catholics are prioritized for prayers with catholics_preferred"""
        catholic_user = UserFactory.create(is_christian=True, is_catholic=True)
        christian_user = UserFactory.create(is_christian=True, is_catholic=False)
        
        prayer = PrayerFactory.create(catholics_preferred=True)
        
        partners = find_compatible_prayer_partners(prayer, test_session, [])
        
        # Catholic user should be first
        if len(partners) >= 2:
            assert partners[0] == catholic_user
```

### Integration Tests
```python
# tests/integration/test_simple_faith_workflows.py

class TestSimpleFaithWorkflows:
    
    def test_faith_preferences_update_workflow(self, client, auth_headers):
        """Test updating faith preferences"""
        
        # Update preferences with faith info
        form_data = {
            "is_christian": True,
            "is_catholic": True,
            "prayer_style": "traditional"
        }
        
        response = client.post("/preferences", data=form_data, headers=auth_headers)
        assert response.status_code == 303  # Redirect
        
        # Verify preferences were updated
        # ... additional verification steps
    
    def test_prayer_creation_with_targeting(self, client, auth_headers):
        """Test creating prayer with simple targeting"""
        
        # Submit prayer with targeting
        form_data = {
            "text": "Please pray for my healing",
            "target_audience": "christians_only",
            "catholics_preferred": True
        }
        
        response = client.post("/prayers", data=form_data, headers=auth_headers)
        assert response.status_code == 303
        
        # Verify prayer was created with targeting
        # ... additional verification steps
```

## Implementation Timeline

### Phase 1: Database Changes (2-3 days)
- [ ] Add `is_christian` and `is_catholic` fields to User model
- [ ] Add `christians_only` and `catholics_preferred` fields to Prayer model  
- [ ] Create migration script
- [ ] Update unit tests

### Phase 2: Backend Logic (2-3 days)
- [ ] Update preferences endpoint to handle new fields
- [ ] Modify prayer filtering logic
- [ ] Update prayer creation to handle new targeting
- [ ] Add simple validation function

### Phase 3: Frontend Updates (2-3 days)
- [ ] Add faith checkboxes to preferences page
- [ ] Add prayer targeting options to prayer form
- [ ] Add JavaScript for Catholic/Christian dependency
- [ ] Test UI interactions

### Phase 4: Integration & Testing (2-3 days)
- [ ] Run migration on test data
- [ ] Write integration tests
- [ ] Test backward compatibility
- [ ] Performance testing

## Success Metrics

### User Adoption
- % of Christian users who specify Catholic denomination
- % of prayers using Christian-only targeting
- User feedback on simplified options

### Prayer Matching Quality
- Improved targeting for Christian prayers
- Catholic users seeing more relevant prayers
- Maintained inclusivity for general prayers

## Conclusion

This simplified faith specification system focuses specifically on Christian users while maintaining simplicity. It provides basic denomination specification (Catholic) and simple prayer targeting without over-complicating the interface or backend systems.