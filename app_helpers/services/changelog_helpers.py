import subprocess
import re
from datetime import datetime
from sqlmodel import Session, select
from models import ChangelogEntry, engine
import anthropic
import os
import fcntl
import time
from typing import List, Dict, Any

def get_git_head_commit() -> str:
    """Get the current HEAD commit hash"""
    try:
        # Try common git paths for production environments
        git_paths = ['/usr/bin/git', '/usr/local/bin/git', 'git']
        
        for git_path in git_paths:
            try:
                result = subprocess.run([git_path, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)
                return result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        return ""
    except Exception:
        return ""

def get_last_cached_commit() -> str:
    """Get the most recent commit ID from the database"""
    with Session(engine) as session:
        stmt = select(ChangelogEntry).order_by(ChangelogEntry.commit_date.desc()).limit(1)
        entry = session.exec(stmt).first()
        return entry.commit_id if entry else ""

def parse_git_commits(since_commit: str = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Parse git commits and return structured data"""
    # Try common git paths for production environments
    git_paths = ['/usr/bin/git', '/usr/local/bin/git', 'git']
    
    for git_path in git_paths:
        try:
            cmd = [git_path, 'log', '--pretty=format:%H|%ad|%s', '--date=iso']
            
            if since_commit:
                cmd.append(f'{since_commit}..HEAD')
            else:
                cmd.extend(['-n', str(limit)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            commits = []
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                # Clean up any extra characters that might appear
                line = line.strip()
                if '< /dev/null |' in line:
                    line = line.replace('< /dev/null | ', '')
                
                parts = line.split('|', 2)
                if len(parts) == 3:
                    commit_hash, date_str, message = parts
                    # Parse ISO date format (e.g., "2025-06-09 01:06:17 -0400")
                    try:
                        # Clean the date string and split on space
                        date_clean = date_str.strip()
                        
                        # Handle format: "2025-06-09 01:06:17 -0400"
                        if ' ' in date_clean:
                            # Split into parts: date, time, timezone
                            date_parts = date_clean.split(' ')
                            if len(date_parts) >= 2:
                                date_part = date_parts[0]  # YYYY-MM-DD
                                time_part = date_parts[1]  # HH:MM:SS
                                # Parse without timezone
                                commit_date = datetime.strptime(f"{date_part} {time_part}", '%Y-%m-%d %H:%M:%S')
                            else:
                                commit_date = datetime.strptime(date_parts[0], '%Y-%m-%d')
                        else:
                            # Just date
                            commit_date = datetime.strptime(date_clean, '%Y-%m-%d')
                            
                    except (ValueError, IndexError) as e:
                        print(f"Date parsing error for '{date_str}': {e}")
                        # If date parsing fails, use current time
                        commit_date = datetime.now()
                    
                    commits.append({
                        'id': commit_hash,
                        'date': commit_date,
                        'message': message.strip()
                    })
            
            return commits
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    # If no git path works, return empty list
    return []

def categorize_commit(message: str) -> str:
    """Categorize commit based on message content"""
    message_lower = message.lower()
    
    # Meta/Development (documentation, plans, guides, etc.)
    if any(keyword in message_lower for keyword in ['plan', 'guide', 'documentation', 'doc', 'readme', 'strategy', 'specification', 'spec']):
        return 'meta'
    
    # New features
    if any(keyword in message_lower for keyword in ['add', 'implement', 'create', 'new', 'introduce']):
        return 'new'
    
    # Bug fixes
    if any(keyword in message_lower for keyword in ['fix', 'bug', 'resolve', 'correct', 'patch']):
        return 'fixed'
    
    # Enhancements/improvements
    if any(keyword in message_lower for keyword in ['improve', 'enhance', 'update', 'optimize', 'refactor', 'upgrade']):
        return 'enhanced'
    
    # Default to enhancement
    return 'enhanced'

def generate_friendly_description(commit_message: str) -> str:
    """Use AI to generate a user-friendly description of the commit"""
    try:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        prompt = f"""Convert this technical git commit message into a friendly, user-facing description that explains what changed for users of a prayer platform web application. Keep it concise (1-2 sentences) and focus on user benefits.

Technical commit: {commit_message}

Guidelines:
- Focus on user-facing changes and benefits
- Avoid technical jargon
- Use friendly, accessible language
- If it's a technical change with no direct user impact, describe it briefly but positively
- Start with an action word when possible (Added, Improved, Fixed, etc.)

Friendly description:"""

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        return response.content[0].text.strip()
    
    except Exception as e:
        print(f"Error generating friendly description: {e}")
        # Fallback: basic cleanup of commit message
        return commit_message.capitalize()

def refresh_changelog_if_needed() -> bool:
    """Check if git has new commits and refresh database if needed (with file locking)"""
    lock_file_path = "/tmp/changelog_refresh.lock"
    
    try:
        # Try to acquire lock
        with open(lock_file_path, 'w') as lock_file:
            # Non-blocking lock - returns immediately if can't acquire
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            current_head = get_git_head_commit()
            last_cached = get_last_cached_commit()
            
            if current_head != last_cached:
                print("Refreshing changelog with AI generation...")
                # Get new commits since last cache
                new_commits = parse_git_commits(since_commit=last_cached if last_cached else None, limit=20)
                
                with Session(engine) as session:
                    for commit in new_commits:
                        # Check if commit already exists
                        existing = session.get(ChangelogEntry, commit['id'])
                        if not existing:
                            # Generate friendly description and categorize
                            friendly_desc = generate_friendly_description(commit['message'])
                            change_type = categorize_commit(commit['message'])
                            
                            entry = ChangelogEntry(
                                commit_id=commit['id'],
                                original_message=commit['message'],
                                friendly_description=friendly_desc,
                                change_type=change_type,
                                commit_date=commit['date']
                            )
                            session.add(entry)
                    
                    session.commit()
                print("Changelog refresh completed.")
                return True
            
            return False
            
    except BlockingIOError:
        # Another process is already refreshing - just skip
        print("Changelog refresh already in progress, skipping...")
        return False
    except Exception as e:
        print(f"Error during changelog refresh: {e}")
        return False

def get_changelog_entries(limit: int = 20) -> List[ChangelogEntry]:
    """Get recent changelog entries from database"""
    with Session(engine) as session:
        stmt = select(ChangelogEntry).order_by(ChangelogEntry.commit_date.desc()).limit(limit)
        return list(session.exec(stmt).all())

def group_entries_by_date(entries: List[ChangelogEntry]) -> Dict[str, List[ChangelogEntry]]:
    """Group changelog entries by relative date"""
    from datetime import date, timedelta
    
    grouped = {}
    today = date.today()
    yesterday = today - timedelta(days=1)
    this_week = today - timedelta(days=7)
    
    for entry in entries:
        entry_date = entry.commit_date.date()
        
        if entry_date == today:
            key = "Today"
        elif entry_date == yesterday:
            key = "Yesterday"
        elif entry_date >= this_week:
            key = "This Week"
        else:
            key = entry_date.strftime("%B %d, %Y")
        
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(entry)
    
    return grouped

def get_change_type_icon(change_type: str) -> str:
    """Get emoji icon for change type"""
    icons = {
        'new': '🚀',
        'enhanced': '✨', 
        'fixed': '🐛',
        'meta': '📋'
    }
    return icons.get(change_type, '📝')