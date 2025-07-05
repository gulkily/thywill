# Template Field Validation Guide

This guide explains how to identify and prevent template field reference issues in ThyWill.

## The Problem

ThyWill's User model uses `display_name` as the primary key instead of a traditional `id` field. This can cause template errors when developers assume standard field names exist.

**Common Issues:**
- Using `user.id` instead of `user.display_name`
- Using `prayer.author_id` instead of `prayer.author_username`
- Using `mark.user_id` instead of `mark.username`

## Validation Tools

### 1. Comprehensive Validation Script

```bash
./validate_templates.py
```

This Python script:
- Scans all HTML templates
- Identifies field reference issues
- Provides specific fix recommendations
- Shows line numbers for each issue

### 2. Quick Static Analysis

```bash
./check_templates.sh
```

This bash script provides:
- Quick pattern matching for common issues
- Summary of field usage patterns
- Common fix suggestions

## Model Field Reference

### User Model
- ✅ `display_name` (primary key)
- ✅ `created_at`
- ✅ `invited_by_username`
- ❌ `id` (doesn't exist)

### Prayer Model
- ✅ `id`
- ✅ `author_username` (links to User.display_name)
- ✅ `text`
- ✅ `generated_prayer`
- ❌ `author_id` (doesn't exist)

### PrayerMark Model
- ✅ `id`
- ✅ `prayer_id`
- ✅ `username` (links to User.display_name)
- ❌ `user_id` (doesn't exist)

## Common Template Fixes

### User References
```html
<!-- ❌ Wrong -->
{% if user.id == current_user.id %}
<a href="/user/{{ user.id }}">{{ user.display_name }}</a>

<!-- ✅ Correct -->
{% if user.display_name == current_user.display_name %}
<a href="/user/{{ user.display_name }}">{{ user.display_name }}</a>
```

### Prayer Author References
```html
<!-- ❌ Wrong -->
{% if prayer.author_id == me.id %}
<a href="/user/{{ prayer.author_id }}">{{ prayer.author_name }}</a>

<!-- ✅ Correct -->
{% if prayer.author_username == me.display_name %}
<a href="/user/{{ prayer.author_username }}">{{ prayer.author_name }}</a>
```

### PrayerMark References
```html
<!-- ❌ Wrong -->
{% if mark.user_id == current_user.id %}

<!-- ✅ Correct -->
{% if mark.username == current_user.display_name %}
```

## Integration into Development Workflow

### Before Code Changes
```bash
# Check for existing issues
./check_templates.sh

# Run full validation
./validate_templates.py
```

### After Template Changes
```bash
# Always validate after template edits
./validate_templates.py

# Test the specific pages affected
./thywill start
# Navigate to affected pages
```

### Before Committing
```bash
# Final validation check
./validate_templates.py
if [ $? -eq 0 ]; then
    echo "Templates validated successfully"
    git add .
    git commit -m "Template changes validated"
else
    echo "Fix template issues before committing"
fi
```

## Manual Validation Commands

```bash
# Find all user.id references
rg "user.*\.id" --type html

# Find all author_id references  
rg "author_id" --type html

# Find all field comparison patterns
rg "== .*\.id" --type html

# Check user link patterns
rg 'href="/user/\{\{.*\}\}"' --type html
```

## Adding New Models

When adding new models, update `validate_templates.py`:

1. Add model fields to `MODEL_FIELDS` dictionary
2. Add common error patterns to `FIELD_CORRECTIONS`
3. Add validation logic in `validate_field_reference()`

## Best Practices

1. **Always use the primary key field name** - don't assume `id` exists
2. **Check model definitions** before writing templates
3. **Run validation tools** after any template changes
4. **Test rendered pages** to catch runtime issues
5. **Use consistent field names** across related templates

## Troubleshooting

### "Template not found" errors
- Check that template files exist in `templates/` directory
- Verify file permissions allow reading

### "Field not found" errors in browser
- Run `./validate_templates.py` to identify the issue
- Check the model definition for correct field names
- Verify the route handler passes the correct data structure

### False positives in validation
- Update the validation script patterns if needed
- Add exceptions for legitimate usage patterns
- Consider if the model definition needs updating