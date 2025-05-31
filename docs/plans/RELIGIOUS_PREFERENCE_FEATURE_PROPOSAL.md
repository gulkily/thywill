# Religious Preference Feature Design and Implementation Proposal

## Overview

This proposal outlines a feature to accommodate both Christian and non-Christian users in the prayer application, allowing for religious preference-based prayer filtering and matching.

## Requirements

### User Stories
1. **As a praying user (Christian)**: I want to specify that I am Christian and that I am praying in Jesus' name
2. **As a prayer requestor**: I want to be able to specify that my prayers should only be shown to Christians praying to Jesus
3. **As a non-Christian user**: I want to participate in the prayer community without religious barriers

## Design Approach

### 1. Database Schema Changes

#### User Model Enhancements
Add religious preference fields to the `User` model in `models.py:6`:

```python
class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    display_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # New fields
    religious_preference: str | None = Field(default="unspecified", max_length=50)  # "christian", "non_christian", "unspecified"
    prayer_style: str | None = Field(default=None, max_length=100)  # e.g., "in_jesus_name", "interfaith", "secular"
```

#### Prayer Model Enhancements
Add prayer targeting fields to the `Prayer` model in `models.py:11`:

```python
class Prayer(SQLModel, table=True):
    # ... existing fields ...
    # New fields
    target_audience: str | None = Field(default="all", max_length=50)  # "christians_only", "all", "non_christians_only"
    prayer_context: str | None = Field(default=None, max_length=100)  # Additional context for prayer style
```

### 2. Migration Strategy

Create a migration script to add the new fields without breaking existing data:

```python
# migrate_religious_preferences.py
def migrate_religious_preferences():
    with Session(engine) as db:
        # Add columns with default values for existing users
        db.execute(text("ALTER TABLE user ADD COLUMN religious_preference TEXT DEFAULT 'unspecified'"))
        db.execute(text("ALTER TABLE user ADD COLUMN prayer_style TEXT DEFAULT NULL"))
        db.execute(text("ALTER TABLE prayer ADD COLUMN target_audience TEXT DEFAULT 'all'"))
        db.execute(text("ALTER TABLE prayer ADD COLUMN prayer_context TEXT DEFAULT NULL"))
        db.commit()
```

### 3. UI/UX Design

#### User Profile Settings
Add religious preference settings to the profile page (`templates/profile.html`):

```html
<div class="preference-section">
    <h3>Prayer Preferences</h3>
    
    <div class="form-group">
        <label for="religious_preference">Religious Background:</label>
        <select name="religious_preference" id="religious_preference">
            <option value="unspecified">Prefer not to specify</option>
            <option value="christian">Christian</option>
            <option value="non_christian">Non-Christian</option>
        </select>
    </div>
    
    <div class="form-group" id="prayer_style_group" style="display: none;">
        <label for="prayer_style">Prayer Style:</label>
        <select name="prayer_style" id="prayer_style">
            <option value="">Default</option>
            <option value="in_jesus_name">Pray in Jesus' name</option>
            <option value="interfaith">Interfaith approach</option>
        </select>
    </div>
</div>

<script>
document.getElementById('religious_preference').addEventListener('change', function() {
    const prayerStyleGroup = document.getElementById('prayer_style_group');
    if (this.value === 'christian') {
        prayerStyleGroup.style.display = 'block';
    } else {
        prayerStyleGroup.style.display = 'none';
    }
});
</script>
```

#### Prayer Submission Form
Add targeting options to prayer submission (`templates/components/prayer_form.html`):

```html
<div class="targeting-options">
    <label for="target_audience">Who should see this prayer request?</label>
    <select name="target_audience" id="target_audience">
        <option value="all">Everyone</option>
        <option value="christians_only">Christians only</option>
        <option value="non_christians_only">Non-Christians only</option>
    </select>
    
    <div class="help-text">
        Selecting "Christians only" means only users who identify as Christian will see this prayer request.
    </div>
</div>
```

### 4. Filtering Logic Implementation

#### Feed Filtering Function
Add filtering logic to the prayer feed in `app.py`:

```python
def get_filtered_prayers_for_user(user: User, db: Session, include_archived: bool = False):
    """Get prayers filtered based on user's religious preferences"""
    
    # Base query for active prayers
    base_query = select(Prayer).where(Prayer.flagged == False)
    
    if not include_archived:
        # Exclude archived prayers
        base_query = base_query.where(
            ~Prayer.id.in_(
                select(PrayerAttribute.prayer_id).where(
                    PrayerAttribute.attribute_name == 'archived'
                )
            )
        )
    
    # Apply religious preference filtering
    if user.religious_preference == "christian":
        # Christians see: all prayers, christian-only prayers
        base_query = base_query.where(
            Prayer.target_audience.in_(["all", "christians_only"])
        )
    elif user.religious_preference == "non_christian":
        # Non-Christians see: all prayers, non-christian-only prayers
        base_query = base_query.where(
            Prayer.target_audience.in_(["all", "non_christians_only"])
        )
    else:
        # Unspecified users see only "all" prayers
        base_query = base_query.where(Prayer.target_audience == "all")
    
    return db.exec(base_query.order_by(Prayer.created_at.desc())).all()
```

#### Prayer Matching for Assignments
Enhance prayer assignment logic:

```python
def find_compatible_prayer_partner(prayer: Prayer, db: Session) -> User | None:
    """Find a user compatible with the prayer's requirements"""
    
    # Build user query based on prayer target audience
    user_query = select(User)
    
    if prayer.target_audience == "christians_only":
        user_query = user_query.where(User.religious_preference == "christian")
    elif prayer.target_audience == "non_christians_only":
        user_query = user_query.where(User.religious_preference == "non_christian")
    # For "all", no additional filtering needed
    
    # Exclude users who have already been assigned this prayer
    assigned_users = db.exec(
        select(PrayerMark.user_id).where(PrayerMark.prayer_id == prayer.id)
    ).all()
    
    if assigned_users:
        user_query = user_query.where(~User.id.in_(assigned_users))
    
    return db.exec(user_query).first()
```

### 5. API Endpoints

#### Update User Preferences
```python
@app.post("/profile/preferences")
async def update_religious_preferences(
    request: Request,
    religious_preference: str = Form(...),
    prayer_style: str = Form(None)
):
    user = require_full_auth(request)
    
    with Session(engine) as db:
        db_user = db.get(User, user.id)
        db_user.religious_preference = religious_preference
        if religious_preference == "christian":
            db_user.prayer_style = prayer_style
        else:
            db_user.prayer_style = None
        
        db.add(db_user)
        db.commit()
    
    return RedirectResponse("/profile", status_code=303)
```

#### Enhanced Prayer Submission
```python
@app.post("/prayers")
async def create_prayer(
    request: Request,
    text: str = Form(...),
    target_audience: str = Form("all"),
    project_tag: str = Form(None)
):
    user = require_full_auth(request)
    
    # Validate target_audience
    valid_audiences = ["all", "christians_only", "non_christians_only"]
    if target_audience not in valid_audiences:
        target_audience = "all"
    
    with Session(engine) as db:
        prayer = Prayer(
            author_id=user.id,
            text=text,
            target_audience=target_audience,
            project_tag=project_tag
        )
        db.add(prayer)
        db.commit()
    
    return RedirectResponse("/feed", status_code=303)
```

### 6. Privacy and Sensitivity Considerations

#### Default Behavior
- New users default to "unspecified" religious preference
- All prayers default to "all" target audience
- Existing data remains unchanged during migration

#### User Education
- Add help text explaining the purpose of religious preferences
- Emphasize that preferences are optional and can be changed
- Clarify that "Christians only" filtering is for prayer style compatibility, not exclusion

#### Respectful Implementation
- Use inclusive language throughout the interface
- Avoid making assumptions about user beliefs
- Provide clear explanations for why these options exist

### 7. Testing Strategy

#### Unit Tests
```python
# test_religious_preferences.py
def test_christian_user_sees_christian_only_prayers():
    """Christian users should see prayers targeted to Christians"""
    
def test_non_christian_user_filters_christian_only_prayers():
    """Non-Christian users should not see Christian-only prayers"""
    
def test_unspecified_user_sees_all_audience_prayers():
    """Users with unspecified preference see only 'all' prayers"""
```

#### Integration Tests
- Test prayer feed filtering across different user types
- Test prayer assignment compatibility
- Test preference update workflows

### 8. Implementation Plan

#### Phase 1: Database Schema (Week 1)
1. Add new fields to User and Prayer models
2. Create migration script
3. Test migration on development database

#### Phase 2: Backend Logic (Week 1-2)
1. Implement filtering functions
2. Update prayer creation and assignment logic
3. Add preference update endpoints

#### Phase 3: Frontend Interface (Week 2)
1. Add preference settings to profile page
2. Update prayer submission form
3. Test user workflows

#### Phase 4: Testing and Deployment (Week 3)
1. Comprehensive testing
2. User acceptance testing
3. Production deployment with migration

### 9. Migration Plan

```python
# One-time migration script
def migrate_existing_data():
    """Migrate existing users and prayers to new schema"""
    with Session(engine) as db:
        # Set all existing users to 'unspecified' preference
        users = db.exec(select(User)).all()
        for user in users:
            user.religious_preference = 'unspecified'
            db.add(user)
        
        # Set all existing prayers to 'all' target audience
        prayers = db.exec(select(Prayer)).all()
        for prayer in prayers:
            prayer.target_audience = 'all'
            db.add(prayer)
        
        db.commit()
```

## Expected Impact

### Benefits
- **Inclusivity**: Accommodates diverse religious backgrounds
- **Relevance**: Matches prayers with compatible prayer partners
- **Respect**: Honors specific religious practices like praying in Jesus' name
- **Choice**: Gives users control over their prayer experience

### Metrics to Track
- User adoption of religious preference settings
- Distribution of prayer target audiences
- User engagement before/after implementation
- User feedback on prayer relevance and satisfaction

## Conclusion

This feature enhances the prayer application's inclusivity while respecting specific religious practices. The implementation leverages the existing attribute system and maintains backward compatibility. The phased approach ensures careful testing and user education throughout the rollout process.