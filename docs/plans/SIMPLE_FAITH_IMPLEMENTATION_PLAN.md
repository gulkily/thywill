# 3-Stage Implementation Plan: Simple Faith Specification

## Stage 1: Database Foundation (2-3 days)

### Database Changes
- Add two boolean fields to User model:
  - `is_christian: bool = Field(default=False)`
  - `is_catholic: bool = Field(default=False)`
- Add two boolean fields to Prayer model:
  - `christians_only: bool = Field(default=False)`
  - `catholics_preferred: bool = Field(default=False)`

### Migration Script
```python
# migrate_simple_faith.py
def add_faith_fields():
    with Session(engine) as db:
        # Migrate existing Christian users
        christian_users = db.exec(
            select(User).where(User.religious_preference == "christian")
        ).all()
        
        for user in christian_users:
            user.is_christian = True
            if user.prayer_style and "catholic" in user.prayer_style.lower():
                user.is_catholic = True
            db.add(user)
        
        db.commit()
```

### Testing
- Unit tests for new fields
- Migration script testing

## Stage 2: Backend Logic (2-3 days)

### Update Preferences Endpoint
```python
@app.post("/preferences")
async def update_preferences(
    # ... existing parameters ...
    is_christian: bool = Form(False),
    is_catholic: bool = Form(False),
    user_session: tuple = Depends(current_user)
):
    user, session = user_session
    
    with Session(engine) as db:
        user.is_christian = is_christian
        user.is_catholic = is_catholic and is_christian  # Catholic only if Christian
        # ... existing logic ...
        db.add(user)
        db.commit()
```

### Update Prayer Creation
```python
@app.post("/prayers")
async def create_prayer(
    # ... existing parameters ...
    christians_only: bool = Form(False),
    catholics_preferred: bool = Form(False),
    user_session: tuple = Depends(current_user)
):
    # ... existing logic ...
    prayer.christians_only = christians_only
    prayer.catholics_preferred = catholics_preferred
```

### Update Filtering Logic
```python
def is_prayer_compatible_with_user(prayer: Prayer, user: User) -> bool:
    if prayer.target_audience == "christians_only" or prayer.christians_only:
        return user.is_christian or user.religious_preference == "christian"
    return True

def find_compatible_prayer_partners(prayer: Prayer, db: Session) -> list[User]:
    # ... existing logic ...
    # Prioritize Catholics if prayer has catholics_preferred
    if prayer.catholics_preferred and user.is_catholic:
        compatible_users.insert(0, user)
```

## Stage 3: Frontend Integration (2-3 days)

### Update Preferences Page
Add to `templates/preferences.html`:
```html
<div class="section faith-preferences">
    <h3>Faith Background <span class="optional">(Optional)</span></h3>
    
    <label class="faith-checkbox">
        <input type="checkbox" name="is_christian" {% if user.is_christian %}checked{% endif %}>
        <span>I am Christian</span>
    </label>
    
    <div class="catholic-option" id="catholic-option" 
         style="{% if not user.is_christian %}display: none;{% endif %}">
        <label class="denomination-checkbox">
            <input type="checkbox" name="is_catholic" {% if user.is_catholic %}checked{% endif %}>
            <span>I am Catholic</span>
        </label>
    </div>
</div>

<script>
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

### Update Prayer Form
Add to `templates/components/prayer_form.html`:
```html
<div class="prayer-targeting-section">
    <h4>Who can pray for this request?</h4>
    
    <label class="targeting-option">
        <input type="radio" name="target_audience" value="everyone" checked>
        <span>Everyone Welcome</span>
    </label>
    
    <label class="targeting-option">
        <input type="radio" name="target_audience" value="christians_only">
        <span>Christians Only</span>
    </label>
    
    <label class="preference-checkbox">
        <input type="checkbox" name="catholics_preferred">
        <span>Catholics preferred (but welcome all Christians)</span>
    </label>
</div>
```

### Testing & Validation
- Integration tests for form submissions
- UI interaction testing
- Cross-browser compatibility
- Accessibility testing

## Success Criteria

### Stage 1 Complete When:
- [ ] Database fields added successfully
- [ ] Migration script runs without errors
- [ ] Existing Christian users migrated correctly

### Stage 2 Complete When:
- [ ] Preferences update correctly saves faith info
- [ ] Prayer creation includes targeting options
- [ ] Prayer filtering respects Christian/Catholic preferences
- [ ] Catholics prioritized for relevant prayers

### Stage 3 Complete When:
- [ ] Faith checkboxes appear in preferences
- [ ] Catholic option shows/hides based on Christian selection
- [ ] Prayer targeting options work correctly
- [ ] All forms submit and validate properly

## Timeline Summary
- **Total Duration**: 6-9 days
- **Stage 1**: Database & Migration (2-3 days)
- **Stage 2**: Backend Logic (2-3 days) 
- **Stage 3**: Frontend Integration (2-3 days)

## Risk Mitigation
- Test migration thoroughly in development
- Maintain backward compatibility with existing `religious_preference` field
- Keep UI changes minimal and intuitive
- Ensure Catholic checkbox is clearly dependent on Christian checkbox