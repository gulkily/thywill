# Changelog Page Implementation Plan

## Overview
Simple changelog page that shows recent features and improvements from git commits, focusing on user-facing changes rather than technical system monitoring.

## 1. Basic Features

- Display recent git commits as changelog entries
- Group by feature type (New, Enhanced, Fixed)
- Show user-friendly descriptions of changes
- Simple timeline format

## 2. Implementation

### Route
- `/changelog` - User-friendly changelog page

### Performance Strategy
```python
# Database model for cached changelog entries
class ChangelogEntry(db.Model):
    commit_id = db.Column(db.String(40), primary_key=True)
    original_message = db.Column(db.Text)
    friendly_description = db.Column(db.Text)
    change_type = db.Column(db.String(20))  # 'new', 'enhanced', 'fixed'
    commit_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def refresh_changelog_if_needed():
    """Check if git has new commits, refresh database if so"""
    current_head = get_git_head_commit()
    last_cached = get_last_cached_commit()
    
    if current_head != last_cached:
        # Get new commits since last cache
        new_commits = get_commits_since(last_cached, limit=20)
        for commit in new_commits:
            if not ChangelogEntry.query.get(commit.id):
                # Use AI to generate friendly description
                friendly_desc = generate_friendly_description(commit.message)
                change_type = categorize_commit(commit.message)
                
                entry = ChangelogEntry(
                    commit_id=commit.id,
                    original_message=commit.message,
                    friendly_description=friendly_desc,
                    change_type=change_type,
                    commit_date=commit.date
                )
                db.session.add(entry)
        db.session.commit()
```

### AI-Generated Friendly Descriptions
- Use Anthropic API to convert technical commits to user-friendly descriptions
- Cache results in database indexed by commit ID
- Only regenerate when new commits appear
- Categorize commits automatically (New Feature, Enhancement, Bug Fix)

## 3. Recent Features (from git log)

- Donation support with PayPal/Venmo
- Dark mode for prayer templates  
- Performance improvements for prayer submission
- Enhanced authentication
- Improved prayer card UI
- Collapsible sections